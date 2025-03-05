from aiogram.fsm.context import FSMContext
from config import Form, get_client, get_openai_client
import tempfile
import os
from datetime import timedelta
import config
from database import load_context,save_context, av_models
from aiogram import types
import asyncio
import logging
from aiogram.enums import ParseMode
import time
import aiohttp
import google.generativeai as genai

from keyboards import get_g4f_keyboard, get_g4f_keyboard_with_admin_button, get_gemini_keyboard, get_gemini_keyboard_with_admin_button, get_glhf_keyboard, get_glhf_keyboard_with_admin_button
import re

# Список Markdown-символов, которые нужно отслеживать
MARKDOWN_SYMBOLS = ['**', '__', '*', '_', '```', '`']

async def split_markdown(text, max_length):

    parts = []
    current_part = ""
    last_code_block_lang = None  
    in_code_block = False

    lines = text.splitlines(keepends=True)

    for line in lines:
        is_code_block_line = line.strip().startswith('```')

        if is_code_block_line:
            lang_match = re.match(r'```(\w+)', line.strip())
            current_code_block_lang = lang_match.group(1) if lang_match else None

            if not in_code_block:
                # Начало блока кода
                if len(current_part) + len(line) > max_length and current_part:
                    parts.append(current_part)
                    current_part = line
                    if current_code_block_lang:
                        last_code_block_lang = current_code_block_lang 
                    else:
                        last_code_block_lang = None
                else:
                    current_part += line
                    if current_code_block_lang:
                        last_code_block_lang = current_code_block_lang 
                    else:
                        last_code_block_lang = None
                in_code_block = True

            else:
                if len(current_part) + len(line) > max_length and current_part:
                    parts.append(current_part)
                    current_part = line
                else:
                    current_part += line
                parts.append(current_part)
                current_part = ""
                in_code_block = False
                last_code_block_lang = None 


        elif in_code_block:
            if len(current_part) + len(line) > max_length:
                parts.append(current_part)

                if last_code_block_lang:
                    current_part = f'```{last_code_block_lang}\n' + line
                else:
                    current_part = '```\n' + line 

            else:
                current_part += line

        else:
            if len(current_part) + len(line) > max_length and current_part:
                parts.append(current_part)
                current_part = ""
                current_part += line
            else:
                current_part += line

    if current_part:
        parts.append(current_part)

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
async def handle_all_messages(message: types.Message, state: FSMContext, is_admin, is_allowed):
    user_id = message.from_user.id
    

    start_time = time.time()
    current_time = time.strftime("%H:%M:%S", time.localtime())
   

    user_context = await load_context(user_id)  
    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')

    current_state = await state.get_state()
    if (
        current_state != Form.waiting_for_message
        and message.text
        not in [
            "/start",
            "/clear",
            "/model",
            "/add_model",
            "/delete_model",
            "/image",
            "/pdf",
            "/generate_image",
            "/add_image_gen_model",
            "/delete_image_gen_model",
            "/recognize_image",
            "/audio",
            "/search",
            "/long_message",
            "/help",
            "/web_search",
            "/add_user",
            "/remove_user",
            "/files",
            "/web_file",
            "Главное меню",
            "Открыть админ-клавиатуру",
        ]
    ):
        await state.set_state(Form.waiting_for_message)

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
    elif api_type in ["glhf", "ddc", "g4f", "openrouter"]:
        user_context["messages"].append(
            {"role": "user", "content": message.text}
        )


    response_text = ""


    try:
        async def run_with_timeout(coro, timeout, message=None):
            """Выполняет корутину с таймаутом и правильно освобождает ресурсы."""
            task = asyncio.create_task(coro)
            try:
                result = await asyncio.wait_for(task, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                logging.error(f"Превышено время ожидания ответа (таймаут {timeout} сек).")
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass 
                    except Exception as e:
                        logging.error(f"Ошибка при отмене задачи: {e}")
                
                if message:
                    await message.reply(f"🕒 Превышено время ожидания ответа ({timeout} сек). Попробуйте еще раз или выберите другую модель.")
                return None
            except Exception as e:
                logging.error(f"Ошибка в run_with_timeout: {e}")
                if not task.done():
                    task.cancel()
                
                if message:
                    await message.reply(f"🚨 Произошла ошибка при обработке запроса: {str(e)}")
                return None

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

                
                response = await run_with_timeout(
                    asyncio.to_thread(g4f_image_request), timeout=60, message=message
                )
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

                
                response = await run_with_timeout(
                    asyncio.to_thread(g4f_web_search_request), timeout=60, message=message
                )

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

                if model_id in ['deepseek-r1', 'o3-mini-low', 'o3-mini', 'r1-1776', 'sonar-reasoning', 'sonar-reasoning-pro']:
                    response = await asyncio.to_thread(sync_g4f_request)
                else:
                    response = await run_with_timeout(
                            asyncio.to_thread(sync_g4f_request), timeout=60, message=message
                        )

                if response:
                    response_text = response.choices[0].message.content
                    if(model_id in ['o3-mini-low']):
                        response_text = await convert_dashed_code_blocks_to_markdown(response_text)

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
            response = await run_with_timeout(
                    asyncio.to_thread(gemini_request), timeout=60, message=message
                )
            
            if response:
                response_text = response.text
                logging.info(f"Запрос к Gemini API завершен за {time.time() - start_time:.5f} секунд")

                user_context["messages"].append(
                    {"role": "model", "parts": [{"text": response_text}]}
                )

        elif api_type in ["glhf", "ddc", "openrouter"]:
            wrapped_coroutine = await run_with_timeout(
                call_openai_completion(api_type, model_id, user_context["messages"]),
                timeout=60,
                message=message
            )
            if wrapped_coroutine:
                completion = await wrapped_coroutine
                response_text = completion.choices[0].message.content
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
                    if api_type == "g4f":
                        if is_admin(message.from_user.id):
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=await get_g4f_keyboard_with_admin_button())
                        else:
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=await get_g4f_keyboard())
                    elif api_type == "gemini":
                        if is_admin(message.from_user.id):
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=await get_gemini_keyboard_with_admin_button())
                        else:
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=await get_gemini_keyboard())
                    else:
                        if is_admin(message.from_user.id):
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=await get_glhf_keyboard_with_admin_button())
                        else:
                            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=await get_glhf_keyboard())
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



async def cmd_long_message(message: types.Message, state: FSMContext, is_allowed):
    start_time = time.time()
    current_time = time.strftime("%H:%M:%S", time.localtime())

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    current_state = await state.get_state()

    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')
    
    if current_state == Form.waiting_for_long_message:

        if user_context["long_message"]:

            long_message = user_context["long_message"]
            user_context["long_message"] = ""  

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
            elif api_type in ["glhf", "g4f", "ddc", "openrouter"]:
                user_context["messages"].append(
                    {"role": "user", "content": long_message}
                )

            response_text = ""

            try:
                async def run_with_timeout(coro, timeout, message=None):
                    """Выполняет корутину с таймаутом и правильно освобождает ресурсы."""
                    task = asyncio.create_task(coro)
                    try:
                        result = await asyncio.wait_for(task, timeout=timeout)
                        return result
                    except asyncio.TimeoutError:
                        logging.error(f"Превышено время ожидания ответа (таймаут {timeout} сек).")
                        if not task.done():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass  # Ожидаемое поведение при отмене
                            except Exception as e:
                                logging.error(f"Ошибка при отмене задачи: {e}")
                        
                        if message:
                            await message.reply(f"🕒 Превышено время ожидания ответа ({timeout} сек). Попробуйте еще раз или выберите другую модель.")
                        return None
                    except Exception as e:
                        logging.error(f"Ошибка в run_with_timeout: {e}")
                        if not task.done():
                            task.cancel()
                        
                        if message:
                            await message.reply(f"🚨 Произошла ошибка при обработке запроса: {str(e)}")
                        return None

                if api_type in ["glhf", "ddc", "openrouter"]:
                    wrapped_coroutine = await run_with_timeout(
                        call_openai_completion(api_type, model_id, user_context["messages"]),
                        timeout=60,
                        message=message
                    )
                    if wrapped_coroutine:
                        completion = await wrapped_coroutine
                        response_text = completion.choices[0].message.content

                elif api_type == "g4f":
                    if (
                        user_context["g4f_image"]
                        and model_id
                        == user_context["image_recognition_model"]
                    ):

                        def g4f_image_request():
                            user_g4f_client = get_client(user_id, "g4f_image_client", model_name=model_id)
                            return  user_g4f_client.chat.completions.create(
                                model=model_id,
                                messages=[
                                    {"role": "user", "content": long_message}
                                ],
                                image=user_context["g4f_image"],
                            )
                        response = await run_with_timeout(
                            asyncio.to_thread(g4f_image_request), timeout=60, message=message
                        )
                        if response:
                            response_text = response.choices[0].message.content

                    else:
                        def g4f_request():
                            user_g4f_client = get_client(user_id, "g4f_client", model_name=model_id)
                            return user_g4f_client.chat.completions.create(
                                model=model_id,
                                messages=user_context["messages"],
                            )

                        if model_id in ['deepseek-r1', 'o3-mini-low', 'o3-mini', 'r1-1776', 'sonar-reasoning', 'sonar-reasoning-pro']: 
                            response = await asyncio.to_thread(g4f_request)
                        else:
                            response = await run_with_timeout(
                                asyncio.to_thread(g4f_request), timeout=60, message=message
                            )

                        if response:
                            response_text = response.choices[0].message.content
                            if(model_id in ['o3-mini-low']):
                                response_text = await convert_dashed_code_blocks_to_markdown(response_text)

                elif api_type== "gemini":
                    def gemini_request():
                        gemini_model = genai.GenerativeModel(
                            model_id
                        )
                        return gemini_model.generate_content(
                            user_context["messages"]
                        )

                    response = await run_with_timeout(
                                asyncio.to_thread(gemini_request), timeout=60, message=message
                            )
                    
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
                        await send_message_in_parts(
                            message, response_text, MAX_MESSAGE_LENGTH
                        )
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
                            await message.answer(
                                response_text, parse_mode=ParseMode.MARKDOWN
                            )
                        except Exception as e:
                            logging.error(
                                f"Ошибка Markdown при отправке сообщения: {e}"
                            )
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

async def call_openai_completion(api_type, model, messages, **kwargs):

    client = get_openai_client(api_type)
    start_time = time.time()
    start_timestamp = time.strftime("%H:%M:%S", time.localtime(start_time))
    logging.info(f"[{start_timestamp}] Начало запроса к OpenAI API ({api_type}) с моделью {model}.")
    try:
        result = await asyncio.to_thread(client.chat.completions.create, model=model, messages=messages, **kwargs)
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
