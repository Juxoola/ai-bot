from aiogram.fsm.context import FSMContext
from config import Form, get_client, get_openai_client, openai_clients, should_bypass_timeout, bot
import tempfile
import os
from datetime import timedelta
from database import load_context,save_context, av_models, trim_context
from aiogram import types
import asyncio
import logging
from aiogram.enums import ParseMode
import time
import aiohttp
import google.generativeai as genai
from keyboards import get_main_keyboard
import re
import multiprocessing
import queue
import base64
import aiofiles
from pydub import AudioSegment

# Список Markdown-символов, которые нужно отслеживать
MARKDOWN_SYMBOLS = ['**', '__', '*', '_', '```', '`']

async def split_markdown(text, max_length):
    if len(text) <= max_length:
        return [text]
        
    parts = []
    current_part = ""
    in_code_block = False
    code_block_lang = None
    
    lines = text.splitlines(keepends=True)
    
    for line in lines:
        is_code_block_marker = line.strip().startswith('```')
        
        if is_code_block_marker:
            if not in_code_block:
                lang_match = re.match(r'```(\w+)', line.strip())
                code_block_lang = lang_match.group(1) if lang_match else None
                in_code_block = True
                
                if len(current_part) + len(line) > max_length:
                    parts.append(current_part)
                    current_part = line
                else:
                    current_part += line
            else:
                in_code_block = False
                
                current_part += line
                
                if current_part:
                    parts.append(current_part)
                    current_part = ""
        elif in_code_block:
            if len(current_part) + len(line) > max_length:
                parts.append(current_part)
                current_part = f"```{code_block_lang or ''}\n{line}"
            else:
                current_part += line
        else:
            if len(current_part) + len(line) > max_length:
                if current_part:
                    parts.append(current_part)
                current_part = line
            else:
                current_part += line
                
    if current_part:
        parts.append(current_part)
        
    for i in range(len(parts)):
        open_count = parts[i].count("```") 
        if open_count % 2 != 0: 
            parts[i] += "\n```"
            
    return parts

async def fix_markdown(text):

    open_formats = []
    in_code_block = False
    result = ""
    lines = text.splitlines(keepends=True)

    for line in lines:
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                result += line
            else:
                in_code_block = False
                result += line
        elif in_code_block:
            result += line 
        else:
            
            result += line

    if in_code_block:
        result += '```\n' 

    return result


async def send_message_in_parts(message, response_text, max_length=4050):
    parts = await split_markdown(response_text, max_length)
    for part_index, part in enumerate(parts):
        try:
            fixed_part = await fix_markdown(part) 
            if len(fixed_part) > 4096:

                subparts = []
                current_subpart = ""
                lines = fixed_part.split('\n')
                in_sub_code_block = False

                for line in lines:
                    if line.strip().startswith('```'):
                        if not in_sub_code_block:
                            in_sub_code_block = True
                            if len(current_subpart) + len(line) > 4096 and current_subpart:
                                subparts.append(current_subpart)
                                current_subpart = line + '\n'
                            else:
                                current_subpart += line + '\n'
                        else:
                            in_sub_code_block = False
                            if len(current_subpart) + len(line) > 4096 and current_subpart:
                                subparts.append(current_subpart)
                                subparts.append(line + '\n') 
                                current_subpart = ""
                            else:
                                current_subpart += line + '\n'
                                subparts.append(current_subpart) 
                                current_subpart = ""

                    elif in_sub_code_block:
                        if len(current_subpart) + len(line) > 4096 and current_subpart:
                            subparts.append(current_subpart)
                            current_subpart = line + '\n'
                        else:
                            current_subpart += line + '\n'
                    else:
                        if len(current_subpart) + len(line) > 4096 and current_subpart:
                            subparts.append(current_subpart)
                            current_subpart = line + '\n'
                        else:
                            current_subpart += line + '\n'

                if current_subpart:
                    subparts.append(current_subpart)


                for subpart_index, subpart in enumerate(subparts):
                    if subpart.strip(): 
                        try:
                            await message.answer(subpart, parse_mode=ParseMode.MARKDOWN)
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            logging.error(f"Ошибка при отправке подчасти {subpart_index} части {part_index}: {e}")
                            await message.answer(subpart) 

            else:
                if fixed_part.strip(): 
                    try:
                        await message.answer(fixed_part, parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logging.error(f"Ошибка при отправке части {part_index} с Markdown: {e}")
                        await message.answer(part)

        except Exception as e:
            logging.error(f"Ошибка при обработке и отправке части сообщения {part_index}: {e}")
            await message.answer(part) 
            await asyncio.sleep(0.1)


async def convert_dashed_code_blocks_to_markdown(text):
    lines = text.splitlines(keepends=True)
    in_code_block = False
    result = ""
    for line in lines:
        if re.fullmatch(r'---+', line.strip()):
            if not in_code_block:
                result += "```python\n"
                in_code_block = True
            else:
                result += "```\n"
                in_code_block = False
        else:
            result += line
    return result

            
MAX_MESSAGE_LENGTH = 4050

class RateLimiter:
    def __init__(self, rate_limit=5, per_seconds=60):
        self.rate_limit = rate_limit
        self.per_seconds = per_seconds
        self.user_requests = {}
        self.lock = asyncio.Lock()
    
    async def can_process(self, user_id):
        async with self.lock:
            current_time = time.time()
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
            
            self.user_requests[user_id] = [
                ts for ts in self.user_requests[user_id] 
                if current_time - ts < self.per_seconds
            ]
            
            if len(self.user_requests[user_id]) >= self.rate_limit:
                return False
                
            self.user_requests[user_id].append(current_time)
            return True

async def handle_all_messages(message: types.Message, state: FSMContext, is_admin, is_allowed, audio_response=False):
    user_id = message.from_user.id
    
    current_state = await state.get_state() or Form.waiting_for_message
    
    if not is_admin:
        rate_limiter = RateLimiter(rate_limit=5, per_seconds=60)
        can_process = await rate_limiter.can_process(user_id)
        if not can_process:
            await message.reply("⚠️ Слишком много запросов. Пожалуйста, подождите")
            return
    
    start_time = time.time()
    current_time = time.strftime("%H:%M:%S", time.localtime())
   
    user_context = await load_context(user_id)  
    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')

    user_is_admin = is_admin(user_id)
    user_context["messages"] = await trim_context(user_context["messages"], is_admin=user_is_admin)

    audio_data = None
    audio_file_id = None
    
    if audio_response and (message.voice or message.audio):
        try:
            if message.voice:
                audio_file_id = message.voice.file_id
            else:
                audio_file_id = message.audio.file_id
                
            file = await bot.get_file(audio_file_id)
            file_path = file.file_path
            audio_data = await bot.download_file(file_path)
            
            if hasattr(audio_data, 'read'):
                audio_bytes = audio_data.read()
            else:
                audio_bytes = audio_data
            
            audio_format = "mp3" 
            if message.audio and message.audio.mime_type:
                if "wav" in message.audio.mime_type:
                    audio_format = "wav"
                elif "mp3" in message.audio.mime_type:
                    audio_format = "mp3"
            
            if message.voice:
                audio_format = "ogg"
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_ogg:
                    temp_ogg.write(audio_bytes)
                    temp_ogg_path = temp_ogg.name
                
                temp_mp3_path = temp_ogg_path.replace('.ogg', '.mp3')
                audio = AudioSegment.from_ogg(temp_ogg_path)
                audio.export(temp_mp3_path, format="mp3")
                
                with open(temp_mp3_path, 'rb') as mp3_file:
                    audio_bytes = mp3_file.read()
                
                os.remove(temp_ogg_path)
                os.remove(temp_mp3_path)
                
                audio_format = "mp3"
            
            encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')
                    
            # Создаем сообщение для OpenAI с аудио
            if api_type in list(openai_clients.keys()):
                user_context["messages"].append({
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": encoded_audio,
                                "format": audio_format
                            }
                        }
                    ]
                })
            else:
                await message.reply("🚨 Выбранная модель не поддерживает аудио-ответы.")
                return
        except Exception as e:
            logging.error(f"Ошибка при обработке аудио: {e}")
            await message.reply(f"🚨 Произошла ошибка при обработке аудио: {str(e)}")
            return
    elif message.text:
        if current_state == Form.waiting_for_message:
            if api_type == "gemini":
                last_message = (
                    user_context["messages"][-1]
                    if user_context["messages"]
                    else None
                )
                if last_message and last_message["role"] == "user" and any(
                    "data" in part for part in last_message["parts"]
                ):
                    user_context["messages"][-1]["parts"].append(
                        {"text": message.text}
                    )
                else:
                    user_context["messages"].append(
                        {"role": "user", "parts": [{"text": message.text}]}
                    )
            elif api_type in list(openai_clients.keys()) + ["g4f"]:
                user_context["messages"].append(
                    {"role": "user", "content": message.text}
                )

    allowed_apis = list(openai_clients.keys()) + ["g4f"]

    if (
        current_state == Form.waiting_for_message
        and api_type == "gemini"
    ):
        last_message = (
            user_context["messages"][-1]
            if user_context["messages"]
            else None
        )
        if last_message and last_message["role"] == "user" and any(
            "data" in part for part in last_message["parts"]
        ):
            user_context["messages"][-1]["parts"].append(
                {"text": message.text}
            )
        else:
            user_context["messages"].append(
                {"role": "user", "parts": [{"text": message.text}]}
            )
    elif api_type in allowed_apis:
        
        user_context["messages"].append(
            {"role": "user", "content": message.text}
        )


    response_text = ""
    response_audio = None

    try:
        
        if api_type == "g4f":
            
            if user_context["g4f_image"]:
                def g4f_image_request():
                    user_g4f_client = get_client(user_id, "g4f_image_client", model_name=model_id)
                    return user_g4f_client.chat.completions.create(
                        model=model_id,
                        messages=user_context["messages"],
                        image=user_context["g4f_image"],
                    )

                current_time = time.strftime("%H:%M:%S", time.localtime())
                logging.info(f"[{current_time}] Начало запроса к G4F image API")

                
                try:
                    response = await async_run_with_timeout(g4f_image_request, 60)
                except TimeoutError as e:
                    logging.error(f"Timeout in g4f_image_request: {e}")
                    await message.reply(f"🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                    response = None

                if response:
                    response_text = response.choices[0].message.content
                    logging.info(f"Запрос к G4F image API завершен за {time.time() - start_time:.5f} секунд")
                    user_context["messages"].append(
                        {"role": "assistant", "content": response_text}
                    )
            
            elif user_context["web_search_enabled"]:
                tool_calls = [
                    {
                        "function": {
                            "arguments": {
                                "query": user_context["messages"][-1]["content"],
                                "max_results": 5,
                                "max_words": 2500,
                                "backend": "auto",
                                "add_text": True,
                                "timeout": 5
                            },
                            "name": "search_tool"
                        },
                        "type": "function"
                    }
                ]

                def g4f_web_search_request():
                    user_g4f_client = get_client(user_id, "g4f_client", model_name=model_id)
                    return  user_g4f_client.chat.completions.create(
                        model=model_id,
                        messages=user_context["messages"],
                        tool_calls=tool_calls
                    )

                current_time = time.strftime("%H:%M:%S", time.localtime())
                logging.info(f"[{current_time}] Начало запроса к G4F с веб-поиском")

                
                try:
                    response = await async_run_with_timeout(g4f_web_search_request, 60)
                except TimeoutError as e:
                    logging.error(f"Timeout in g4f_web_search_request: {e}")
                    await message.reply(f"🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                    response = None

                if response:
                    response_text = response.choices[0].message.content
                    logging.info(f"Запрос к G4F с веб-поиском завершен за {time.time() - start_time:.5f} секунд")

                    user_context["messages"].append(
                        {"role": "assistant", "content": response_text}
                    )

            else:
                current_time = time.strftime("%H:%M:%S", time.localtime())
                logging.info(f"[{current_time}] Начало запроса к G4F API")

                def sync_g4f_request():
                    
                    user_g4f_client = get_client(user_id, "g4f_client", model_name=model_id)
                    return user_g4f_client.chat.completions.create(
                        model=model_id,
                        messages=user_context["messages"],
                    )

                if should_bypass_timeout(model_id, api_type):
                    response = await asyncio.to_thread(sync_g4f_request)
                    logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен без таймаута")
                else:
                    try:
                        response = await async_run_with_timeout(sync_g4f_request, 60)
                    except TimeoutError as e:
                        logging.error(f"Timeout in sync_g4f_request: {e}")
                        await message.reply(f"🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                        response = None

                if response:
                    response_text = response.choices[0].message.content
                    logging.info(f"Запрос к G4F API завершен за {time.time() - start_time:.5f} секунд")

                    user_context["messages"].append(
                        {"role": "assistant", "content": response_text}
                    )

        elif api_type == "gemini":
            def gemini_request():
                gemini_model = genai.GenerativeModel(
                    model_id
                )
                
                if not user_context["messages"]:
                    user_context["messages"] = [
                        {"role": "user", "parts": [{"text": message.text}]}
                    ]
                return gemini_model.generate_content(
                    user_context["messages"]
                )       

            current_time = time.strftime("%H:%M:%S", time.localtime())
            logging.info(f"[{current_time}] Начало запроса к Gemini API")
            
            if should_bypass_timeout(model_id, api_type):
                response = await asyncio.to_thread(gemini_request)
                logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен без таймаута")
            else:
                try:
                    response = await async_run_with_timeout(gemini_request, 60)
                except TimeoutError as e:
                    logging.error(f"Timeout in gemini_request: {e}")
                    await message.reply(f"🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                    response = None

            if response:
                response_text = response.text
                logging.info(f"Запрос к Gemini API завершен за {time.time() - start_time:.5f} секунд")

                user_context["messages"].append(
                    {"role": "model", "parts": [{"text": response_text}]}
                )

        elif api_type in openai_clients:
            if audio_response and model_id == "openai-audio":
                try:
                    client = get_openai_client(api_type)
                    logging.info(f"Начало прямого запроса к OpenAI Audio API")
                    
                    current_message = []
                    
                    if message.text:
                        current_message = [{"role": "user", "content": message.text}]
                    else:
                        current_message = [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_audio",
                                        "input_audio": {
                                            "data": encoded_audio,
                                            "format": audio_format
                                        }
                                    }
                                ]
                            }
                        ]
                    
                    logging.info("Отправка запроса к аудиомодели без учета предыдущего контекста")
                    
                    result = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=model_id,
                        modalities=["text", "audio"],
                        audio={"voice": "alloy", "format": "wav"},
                        messages=current_message,
                        timeout=90
                    )
                    
                    logging.info(f"Прямой запрос к OpenAI Audio API завершен успешно")
                    
                    if result and result.choices:
                        choice = result.choices[0].message
                        if hasattr(choice, 'audio') and choice.audio:
                            response_text = choice.audio.transcript
                            response_audio = base64.b64decode(choice.audio.data)
                            
                            temp_wav_path = f"temp_audio_{user_id}.wav"
                            async with aiofiles.open(temp_wav_path, "wb") as f:
                                await f.write(response_audio)
                            
                            temp_ogg_path = f"temp_audio_{user_id}.ogg"
                            audio = AudioSegment.from_wav(temp_wav_path)
                            audio.export(temp_ogg_path, format="ogg")
                            
                            try:
                                with open(temp_ogg_path, "rb") as audio_file:
                                    await message.answer_audio(
                                        audio=types.BufferedInputFile(audio_file.read(), filename="response.ogg"),
                                        caption=f"🔊 Аудио-ответ:\n\n{response_text[:1000]}" if response_text else "🔊 Аудио-ответ"
                                    )
                            except Exception as e:
                                logging.error(f"Ошибка при отправке аудио: {e}")
                                await message.reply("🚨 Ошибка при отправке аудио-ответа")
                            finally:
                                if os.path.exists(temp_wav_path):
                                    os.remove(temp_wav_path)
                                if os.path.exists(temp_ogg_path):
                                    os.remove(temp_ogg_path)
                            
                            end_time = time.time()
                            processing_time = end_time - start_time
                            formatted_processing_time = str(timedelta(seconds=int(processing_time)))
                            if user_context.get("show_processing_time", True):
                                await message.answer(f"⏳ Время обработки запроса: {formatted_processing_time}")
                            
                            return
                        else:
                            logging.error("Модель не вернула аудио в ответе")
                            await message.reply("🚨 Модель не вернула аудио-ответ")
                    else:
                        logging.error("Не получен ответ от API или ответ некорректен")
                        await message.reply("🚨 Не получен корректный ответ от API")
                        return
                except Exception as e:
                    logging.error(f"Ошибка при обработке аудио запроса: {e}")
                    await message.reply(f"🚨 Ошибка при обработке аудио: {str(e)}")
                    return
            elif should_bypass_timeout(model_id, api_type):
                try:
                    result = await asyncio.to_thread(call_openai_completion_sync, api_type, model_id, user_context["messages"])
                    logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен без таймаута")
                except Exception as e:
                    logging.error(f"Ошибка при выполнении запроса к {api_type} API: {e}")
                    await message.reply(f"🚨 Ошибка при выполнении запроса: {e}")
                    result = None
            else:
                try:
                    result = await async_run_with_timeout(call_openai_completion_sync, 60, api_type, model_id, user_context["messages"])
                except TimeoutError as e:
                    logging.error(f"Timeout in openai_client request (long message): {e}")
                    await message.reply("🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                    result = None

            if result:
                if not hasattr(result, "choices") or not result.choices:
                    logging.error(f"Ответ от {api_type} API не содержит ожидаемых данных: {result}")
                    await message.reply(f"🚨 Ошибка: получен некорректный ответ от {api_type} API.")
                else:
                    response_text = result.choices[0].message.content
                    user_context["messages"].append({"role": "assistant", "content": response_text})

        if response_text:
            # Удаляем теги <think> и </think> из ответа модели
            response_text = response_text.replace("<think>", "").replace("</think>", "")
            
            end_time = time.time()
            processing_time = end_time - start_time
            formatted_processing_time = str(timedelta(seconds=int(processing_time)))

            service_info = f"⏳ Время обработки запроса: {formatted_processing_time}"
            if len(response_text) > MAX_MESSAGE_LENGTH:
                await send_message_in_parts(message, response_text, MAX_MESSAGE_LENGTH)
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                    temp_file.write(response_text)
                    temp_file_path = temp_file.name

                try:
                    with open(temp_file_path, "rb") as file_to_send:
                        await message.answer_document(types.BufferedInputFile(file_to_send.read(), filename="response.txt"))
                except Exception as e:
                    logging.error(f"Ошибка при отправке файла: {e}")
                    await message.answer("🚨 Не удалось отправить ответ в виде файла.")
                finally:
                    os.remove(temp_file_path)
            else:
                
                try:
                    await message.answer(response_text, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
                    try:
                        await message.answer(
                            f"🔔Попытка фиксить форматирование сообщения"
                        )
                        fixed_response = await fix_markdown(response_text)
                        await message.answer(fixed_response,parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        await message.answer(
                            f"🚨Произошла ошибка при форматировании сообщения: {e}\n\n"
                            "Отправляю без форматирования."
                        )
                        await message.answer(response_text)
                        

            await save_context(user_id, user_context)

            if user_context.get("show_processing_time", True):
                await message.answer(service_info)

    except Exception as e:
        logging.error(f"Ошибка во время запроса к API: {e}")
        await message.reply(f"🚨Произошла ошибка: {e}")
    logging.info(f"Общее время обработки сообщения: {time.time() - start_time:.5f} секунд")



async def cmd_long_message(message: types.Message, state: FSMContext, is_allowed, is_admin):
    user_id = message.from_user.id

    if not is_admin(user_id):
        rate_limiter = RateLimiter(rate_limit=5, per_seconds=60)
        can_process = await rate_limiter.can_process(user_id)
        if not can_process:
            await message.reply("⚠️ Слишком много запросов. Пожалуйста, подождите")
            return
        
    start_time = time.time()
    current_time = time.strftime("%H:%M:%S", time.localtime())

    user_context = await load_context(user_id)
    current_state = await state.get_state()

    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')
    
    user_is_admin = is_admin(user_id)
    user_context["messages"] = await trim_context(user_context["messages"], is_admin=user_is_admin)

    if current_state == Form.waiting_for_long_message:

        if user_context["long_message"]:

            long_message = user_context["long_message"]
            user_context["long_message"] = ""  
            allowed_apis = list(openai_clients.keys()) + ["g4f"]

            if api_type == "gemini":
                last_message = (
                    user_context["messages"][-1]
                    if user_context["messages"]
                    else None
                )
                if last_message and last_message["role"] == "user" and any(
                    "data" in part for part in last_message["parts"]
                ):
                    user_context["messages"][-1]["parts"].append(
                        {"text": long_message}
                    )
                else:
                    user_context["messages"].append(
                        {"role": "user", "parts": [{"text": long_message}]}
                    )
            elif api_type in allowed_apis:
                user_context["messages"].append({"role": "user", "content": long_message})

            response_text = ""

            try:
                if api_type in openai_clients:                    
                    if should_bypass_timeout(model_id, api_type):
                        try:
                            result = await asyncio.to_thread(call_openai_completion_sync, api_type, model_id, user_context["messages"])
                            logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен без таймаута в режиме длинного сообщения")
                        except Exception as e:
                            logging.error(f"Ошибка при выполнении запроса к {api_type} API в режиме длинного сообщения: {e}")
                            await message.reply(f"🚨 Ошибка при выполнении запроса: {e}")
                            result = None
                    else:
                        try:
                            result = await async_run_with_timeout(call_openai_completion_sync, 60, api_type, model_id, user_context["messages"])
                        except TimeoutError as e:
                            logging.error(f"Timeout in openai_client request (long message): {e}")
                            await message.reply("🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                            result = None

                    if result:
                        response_text = result.choices[0].message.content

                elif api_type == "g4f":
                    if user_context["g4f_image"] and model_id == user_context["image_recognition_model"]:
                        def g4f_image_request():
                            user_g4f_client = get_client(user_id, "g4f_image_client", model_name=model_id)
                            return user_g4f_client.chat.completions.create(
                                model=model_id,
                                messages=[{"role": "user", "content": long_message}],
                                image=user_context["g4f_image"],
                            )
                        try:
                            response = await async_run_with_timeout(g4f_image_request, 60)
                        except TimeoutError as e:
                            logging.error(f"Timeout in g4f_image_request (long message): {e}")
                            await message.reply(f"🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                            response = None

                        if response:
                            response_text = response.choices[0].message.content
                    else:
                        def g4f_request():
                            user_g4f_client = get_client(user_id, "g4f_client", model_name=model_id)
                            return user_g4f_client.chat.completions.create(
                                model=model_id,
                                messages=user_context["messages"],
                            )

                        if should_bypass_timeout(model_id, api_type):
                            response = await asyncio.to_thread(g4f_request)
                            logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен без таймаута в режиме длинного сообщения")
                        else:
                            try:
                                response = await async_run_with_timeout(g4f_request, 60)
                            except TimeoutError as e:
                                logging.error(f"Timeout in g4f_request (long message): {e}")
                                await message.reply(f"🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                                response = None

                        if response:
                            response_text = response.choices[0].message.content

                elif api_type == "gemini":
                    def gemini_request():
                        gemini_model = genai.GenerativeModel(model_id)
                        return gemini_model.generate_content(user_context["messages"])

                    if should_bypass_timeout(model_id, api_type):
                        response = await asyncio.to_thread(gemini_request)
                        logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен без таймаута в режиме длинного сообщения")
                    else:
                        try:
                            response = await async_run_with_timeout(gemini_request, 60)
                        except TimeoutError as e:
                            logging.error(f"Timeout in gemini_request (long message): {e}")
                            await message.reply("🕒 Превышено время ожидания ответа (60 сек). Попробуйте еще раз или выберите другую модель.")
                            response = None

                    if response:
                        response_text = response.text

                if response_text:
                    # Удаляем теги <think> и </think> из ответа модели
                    response_text = response_text.replace("<think>", "").replace("</think>", "")
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    formatted_processing_time = str(timedelta(seconds=int(processing_time)))

                    service_info = f"⏳ Время обработки запроса: {formatted_processing_time}"
                    
                    if len(response_text) > MAX_MESSAGE_LENGTH:
                        await send_message_in_parts(message, response_text, MAX_MESSAGE_LENGTH)
                        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                            temp_file.write(response_text)
                            temp_file_path = temp_file.name

                        try:
                            with open(temp_file_path, "rb") as file_to_send:
                                await message.answer_document(types.BufferedInputFile(file_to_send.read(), filename="response.txt"))
                        except Exception as e:
                            logging.error(f"Ошибка при отправке файла: {e}")
                            await message.answer("🚨 Не удалось отправить ответ в виде файла.")
                        finally:
                            os.remove(temp_file_path)
                    else:
                        try:
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN)
                        except Exception as e:
                            logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
                            try:
                                await message.answer(
                                    f"🔔Попытка фиксить форматирование сообщения"
                                )
                                fixed_response = await fix_markdown(
                                    response_text
                                )
                                await message.answer(
                                    fixed_response,
                                    parse_mode=ParseMode.MARKDOWN,
                                )
                            except Exception as e:
                                await message.answer(
                                    f"🚨Произошла ошибка при форматировании сообщения: {e}\n\n"
                                    "Отправляю без форматирования."
                                )
                                await message.answer(response_text)
                if api_type != "gemini":
                    user_context["messages"].append(
                        {"role": "assistant", "content": response_text}
                    )
                else:
                    user_context["messages"].append(
                        {"role": "model", "parts": [{"text": response_text}]}
                    )
                await save_context(user_id, user_context)

                if user_context.get("show_processing_time", True):
                    await message.answer(service_info)

            except Exception as e:
                logging.error(f"Ошибка во время запроса к API: {e}")
                await message.reply(f"🚨Произошла ошибка: {e}")

            await message.reply("🔔Длинное сообщение обработано.")
            await state.set_state(Form.waiting_for_message)
        else:
            await state.set_state(Form.waiting_for_message)
            await message.reply("🔔Режим накопления сообщений отключен.")
        return

    else:
        await message.reply(
            "🔔Режим накопления сообщений активирован. Отправьте /long_message еще раз, чтобы завершить накопление и отправить сообщение модели."
        )
        await state.set_state(Form.waiting_for_long_message)
        
async def handle_long_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    user_context["long_message"] += message.text + "\n"
    await save_context(user_id, user_context)
    await message.reply("🔔Сообщение добавлено к накоплению.")



def call_openai_completion_sync(api_type, model, messages, **kwargs):
    """Синхронная версия для вызова OpenAI API, которая используется в async_run_with_timeout."""
    client = get_openai_client(api_type)
    start_time = time.time()
    start_timestamp = time.strftime("%H:%M:%S", time.localtime(start_time))
    logging.info(f"[{start_timestamp}] Начало запроса к OpenAI API ({api_type}) с моделью {model}.")
    try:
        result =  client.chat.completions.create(model=model, messages=messages, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        end_timestamp = time.strftime("%H:%M:%S", time.localtime(end_time))
        logging.info(f"[{end_timestamp}] Запрос к OpenAI API ({api_type}) завершён за {duration:.2f} секунд.")
        return result
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        end_timestamp = time.strftime("%H:%M:%S", time.localtime(end_time))
        logging.error(f"[{end_timestamp}] Ошибка при выполнении запроса к OpenAI API ({api_type}) с моделью {model} после {duration:.2f} секунд: {e}")
        raise



def run_in_process(func, timeout, *args, **kwargs):
    """Запускает блокирующую функцию func в отдельном процессе с таймаутом.
    Если функция не завершилась за timeout секунд, процесс принудительно завершается.
    Результат (или исключение) передается через очередь."""
    result_queue = multiprocessing.Queue()

    def wrapper():
        try:
            result = func(*args, **kwargs)
            result_queue.put((True, result))
        except Exception as ex:
            result_queue.put((False, ex))

    process = multiprocessing.Process(target=wrapper)
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join(1)
        raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
    try:
        success, result = result_queue.get_nowait()
        if success:
            return result
        else:
            raise result
    except queue.Empty:
        raise Exception("Ошибка: функция не вернула результат.")

async def async_run_with_timeout(func, timeout, *args, **kwargs):
    """Асинхронная обёртка для запуска блокирующих функций с таймаутом через отдельный процесс."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_in_process, func, timeout, *args, **kwargs)
