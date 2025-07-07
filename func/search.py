from aiogram.fsm.context import FSMContext
from config import get_client, Form, openai_clients, anthropic_clients, DEFAULT_SYSTEM_PROMPTS
from func.messages import send_message_in_parts, call_anthropic_completion_sync
from database import load_context, save_context
from aiogram import types
import asyncio
import logging
from aiogram.enums import ParseMode
from bs4 import BeautifulSoup
from aiohttp import ClientSession, ClientTimeout, ClientError
from urllib.parse import urlparse
from typing import Iterator
import os
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
import google.generativeai as genai
from .messages import call_openai_completion_sync, async_run_with_timeout, DEFAULT_API_TIMEOUT

class SearchResults():
    def __init__(self, results: list, used_words: int):
        self.results = results
        self.used_words = used_words

    def __iter__(self):
        yield from self.results

    def __str__(self):
        search = ""
        for idx, result in enumerate(self.results):
            if search:
                search += "\n\n\n"
            search += f"Title: {result.title}\n\n"
            if result.text:
                search += result.text
            else:
                search += result.snippet
            search += f"\n\nSource: [[{idx}]]({result.url})"
        return search

    def __len__(self) -> int:
        return len(self.results)

class SearchResultEntry():
    def __init__(self, title: str, url: str, snippet: str, text: str=None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.text = text

def scrape_text(html: str, max_words: int = None, add_source=True, count_images: int = 2) -> Iterator[str]:
    source = BeautifulSoup(html, "html.parser")
    soup = source
    for selector in [
            "main",
            ".main-content-wrapper",
            ".main-content",
            ".emt-container-inner",
            ".content-wrapper",
            "#content",
            "#mainContent",
        ]:
        select = soup.select_one(selector)
        if select:
            soup = select
            break
    for remove in [".c-globalDisclosure"]:
        select = soup.select_one(remove)
        if select:
            select.extract()

    image_select = "img[alt][src^=http]:not([alt=''])"
    image_link_select = f"a:has({image_select})"
    yield_words = []
    for paragraph in soup.select(f"h1, h2, h3, h4, h5, h6, p, table:not(:has(p)), ul:not(:has(p)), {image_link_select}"):
        if count_images > 0:
            image = paragraph.select_one(image_select)
            if image:
                title = paragraph.get("title") or paragraph.text
                if title:
                    yield f"!{title}({image['src']})\n" 
                    if max_words is not None:
                        max_words -= 10
                    count_images -= 1
                continue

        for line in paragraph.text.splitlines():
            words = [word for word in line.split() if word]
            count = len(words)
            if not count:
                continue
            words = " ".join(words)
            if words in yield_words:
                continue
            if max_words:
                max_words -= count
                if max_words <= 0:
                    break
            yield words + "\n"
            yield_words.append(words)

    if add_source:
        canonical_link = source.find("link", rel="canonical")
        if canonical_link and "href" in canonical_link.attrs:
            link = canonical_link["href"]
            domain = urlparse(link).netloc
            yield f"\nSource: [{domain}]({link})"

async def fetch_and_scrape(session: ClientSession, url: str, max_words: int = None, add_source: bool = False) -> str:
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                text = "".join(scrape_text(html, max_words, add_source))
                return text
    except (ClientError, asyncio.TimeoutError):
        return

async def search(query: str, max_results: int = 5, max_words: int = 2500, backend: str = "auto", add_text: bool = True, timeout: int = 5, region: str = "wt-wt") -> SearchResults:
    try:
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(
                    query,
                    region=region,
                    safesearch="moderate",
                    timelimit="y",
                    max_results=max_results,
                    backend=backend,
                ):
                if ".google." in result["href"]:
                    continue
                results.append(SearchResultEntry(
                    result["title"],
                    result["href"],
                    result["body"]
                ))

            if add_text:
                requests = []
                async with ClientSession(timeout=ClientTimeout(timeout)) as session:
                    for entry in results:
                        requests.append(fetch_and_scrape(session, entry.url, int(max_words / (max_results - 1)), False))
                    texts = await asyncio.gather(*requests)

            formatted_results = []
            used_words = 0
            left_words = max_words
            for i, entry in enumerate(results):
                if add_text:
                    entry.text = texts[i]
                if max_words:
                    left_words -= entry.title.count(" ") + 5
                    if entry.text:
                        left_words -= entry.text.count(" ")
                    else:
                        left_words -= entry.snippet.count(" ")
                    if 0 > left_words:
                        break
                used_words = max_words - left_words
                formatted_results.append(entry)

            return SearchResults(formatted_results, used_words)
    except:
        return SearchResults([], 0)

async def process_search_query(message: types.Message, state: FSMContext):
    query = message.text
    user_id = message.from_user.id
    user_context = await load_context(user_id)
    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')
    MAX_MESSAGE_LENGTH = 4096

    try:
        search_results = await asyncio.to_thread(
            lambda: asyncio.run(search(query))
        )

        search_message = f"""
{str(search_results)}

Инструкция: Используя предоставленные результаты веб-поиска, напишите развернутый ответ на запрос пользователя.
Обязательно добавьте источники цитирования, используя обозначение [Number](Url) после ссылки. Пример: [0](http://google.com)

Запрос пользователя:
{query}
"""     
        allowed_apis = list(openai_clients.keys()) + ["g4f"]
        if api_type in allowed_apis:
            user_context["messages"].append({"role": "user", "content": search_message})
        elif api_type == "gemini":
            user_context["messages"].append({"role": "user", "parts": [{"text": search_message}]})

        response_text = None

        if api_type in openai_clients:

            try:
                result = await async_run_with_timeout(
                    lambda: call_openai_completion_sync(api_type, model_id, user_context["messages"]),
                    DEFAULT_API_TIMEOUT
                )
            except TimeoutError as e:
                logging.error(f"Timeout in openai_client request (long message): {e}")
                await message.reply("🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT}. Попробуйте еще раз или выберите другую модель.")
                result = None

            if result:
                response_text = result.choices[0].message.content
                
        elif api_type in anthropic_clients:
            # Конвертируем формат сообщений OpenAI в формат Anthropic
            anthropic_messages = []
            system_content = None
            
            # Извлекаем системное сообщение, если оно есть
            if user_context["messages"] and user_context["messages"][0]["role"] == "system":
                system_content = user_context["messages"][0]["content"]
            
            # Добавляем все сообщения кроме системного
            for msg in user_context["messages"]:
                role = msg["role"]
                if role == "system":
                    continue
                anthropic_messages.append({"role": role, "content": msg["content"]})
                        
            try:
                result = await async_run_with_timeout(
                    lambda: call_anthropic_completion_sync(api_type, model_id, anthropic_messages, system=system_content),
                    DEFAULT_API_TIMEOUT
                )
            except TimeoutError as e:
                logging.error(f"Timeout in anthropic_client request (long message): {e}")
                await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                result = None

            if result:
                response_text = result.content[0].text

        elif api_type == "g4f":
            def g4f_request():
                user_g4f_client = get_client(user_id, "g4f_client", model_name=model_id)
                return user_g4f_client.chat.completions.create(
                    model=model_id,
                    messages=user_context["messages"],
                )

            try:
                response = await async_run_with_timeout(g4f_request, DEFAULT_API_TIMEOUT)
            except TimeoutError as e:
                logging.error(f"Timeout in g4f_image_request (long message): {e}")
                await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                response = None

            if response:
                response_text = response.choices[0].message.content

        elif api_type == "gemini":
            async def gemini_request():
                system_instruction = None
                messages_for_model = []
                
                for msg in user_context["messages"]:
                    if msg["role"] == "system" and "parts" in msg and msg["parts"]:
                        system_text = msg["parts"][0].get("text", "")
                        if system_text:
                            system_instruction = system_text
                    else:
                        messages_for_model.append(msg)
                
                if not system_instruction:
                    system_instruction = DEFAULT_SYSTEM_PROMPTS["default"]
                
                if system_instruction:
                    gemini_model = genai.GenerativeModel(
                        model_id,
                        system_instruction=system_instruction
                    )
                else:
                    gemini_model = genai.GenerativeModel(model_id)
                
                return gemini_model.generate_content(messages_for_model)

            try:
                response = await async_run_with_timeout(gemini_request, DEFAULT_API_TIMEOUT)
            except TimeoutError as e:
                logging.error(f"Timeout in gemini_request (long message): {e}")
                await message.reply("🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT}). Попробуйте еще раз или выберите другую модель.")
                response = None
            
            if response:
                response_text = response.text

        if response_text:
            if len(response_text) > MAX_MESSAGE_LENGTH:
                await send_message_in_parts(message, response_text, MAX_MESSAGE_LENGTH)
            else:
                try:
                    await message.reply(response_text, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
                    await message.answer(
                        f"🚨Произошла ошибка при форматировании сообщения: {e}\n\nОтправляю без форматирования."
                    )
                    await message.reply(response_text)

        if api_type in allowed_apis:
            user_context["messages"].append({"role": "assistant", "content": response_text})
        elif api_type == "gemini":
            user_context["messages"].append({"role": "model", "parts": [{"text": response_text}]})
        await save_context(user_id, user_context)
    except Exception as e:
        logging.error(f"Ошибка во время веб-поиска или отправки в модель: {e}")
        await message.reply(f"🚨Произошла ошибка во время веб-поиска или отправки в модель: {e}")
    await state.set_state(Form.waiting_for_message)