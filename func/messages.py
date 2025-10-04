from aiogram.fsm.context import FSMContext
from config import Form, get_client, get_openai_client, openai_clients, should_bypass_timeout, bot, DEFAULT_SYSTEM_PROMPTS, anthropic_clients, get_anthropic_client, gemini_client
import tempfile
import os
from datetime import timedelta
from database import load_context,save_context, trim_context, is_admin
from aiogram import types
import asyncio
import logging
from aiogram.enums import ParseMode
import time
from google.genai import types as genai_types
import re
import base64
import aiofiles
import aiofiles.os
from pydub import AudioSegment
from func.decorators import rate_limit

DEFAULT_API_TIMEOUT = 60
AUDIO_API_TIMEOUT = 120
EXTENDED_API_TIMEOUT = 240

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
                            await message.reply(subpart, parse_mode=ParseMode.MARKDOWN)
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            logging.error(f"Ошибка при отправке подчасти {subpart_index} части {part_index}: {e}")
                            await message.reply(subpart) 

            else:
                if fixed_part.strip(): 
                    try:
                        await message.reply(fixed_part, parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logging.error(f"Ошибка при отправке части {part_index} с Markdown: {e}")
                        await message.reply(part)

        except Exception as e:
            logging.error(f"Ошибка при обработке и отправке части сообщения {part_index}: {e}")
            await message.reply(part) 
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

async def calculate_and_show_processing_time(message, user_context, start_time):
    end_time = time.time()
    processing_time = end_time - start_time
    formatted_processing_time = str(timedelta(seconds=int(processing_time)))
    
    service_info = f"⏳ Время обработки запроса: {formatted_processing_time}"
    
    if user_context.get("show_processing_time", True):
        await message.answer(service_info)
    
    logging.info(f"Общее время обработки сообщения: {processing_time:.5f} секунд")
    
    return formatted_processing_time

def process_audio_sync(ogg_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_ogg:
        temp_ogg.write(ogg_bytes)
        temp_ogg_path = temp_ogg.name

    temp_mp3_path = temp_ogg_path.replace('.ogg', '.mp3')
    
    try:
        audio = AudioSegment.from_ogg(temp_ogg_path)
        audio.export(temp_mp3_path, format="mp3")
        
        with open(temp_mp3_path, 'rb') as mp3_file:
            mp3_bytes = mp3_file.read()
        return mp3_bytes
    finally:
        # Очищаем временные файлы
        if os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)
        if os.path.exists(temp_mp3_path):
            os.remove(temp_mp3_path)

async def process_message(message: types.Message, user_context, user_id, api_type, model_id, message_text, start_time=None, audio_data=None, audio_format=None, encoded_audio=None, is_long_message=False):

    if start_time is None:
        start_time = time.time()
    
    response_text = ""
    response_audio = None
    
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
{"text": message_text}
            )
        else:
            user_context["messages"].append(
{"role": "user", "parts": [{"text": message_text}]}
    )
    elif api_type in allowed_apis:
        user_context["messages"].append(
            {"role": "user", "content": message_text}
        )

    try:
        # Обработка через G4F API
        if api_type == "g4f":
            if user_context["g4f_image"] and (not is_long_message or model_id == user_context["image_recognition_model"]):
                async def g4f_image_request():
                    user_g4f_client = await get_client(user_id, "g4f_image_client", model_name=model_id)
                    
                    image_data = user_context["g4f_image"]
                    if hasattr(image_data, 'read') and not isinstance(image_data, str):
                        if hasattr(image_data, 'seek'):
                            image_data.seek(0)
                        image_bytes = image_data.read()
                        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                        image_data_uri = f"data:image/jpeg;base64,{image_b64}"
                        image_to_use = image_data_uri
                    else:
                        image_to_use = image_data
                    
                    return await user_g4f_client.chat.completions.create(
                        model=model_id,
                        messages=user_context["messages"] if not is_long_message else [{"role": "user", "content": message_text}],
                        image=image_to_use,
                    )

                current_time = time.strftime("%H:%M:%S", time.localtime())
                logging.info(f"[{current_time}] Начало запроса к G4F image API{' (длинное сообщение)' if is_long_message else ''}")
                
                try:
                    response = await async_run_with_timeout(g4f_image_request, DEFAULT_API_TIMEOUT)
                except TimeoutError as e:
                    logging.error(f"Timeout in g4f_image_request{' (long message)' if is_long_message else ''}: {e}")
                    await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                    response = None

                if response:
                    response_text = response.choices[0].message.content
                    logging.info(f"Запрос к G4F image API завершен за {time.time() - start_time:.5f} секунд")
                    if not is_long_message:
                        user_context["messages"].append(
                            {"role": "assistant", "content": response_text}
                        )
            else:
                current_time = time.strftime("%H:%M:%S", time.localtime())
                logging.info(f"[{current_time}] Начало запроса к G4F API{' (длинное сообщение)' if is_long_message else ''}")

                async def g4f_request():
                    user_g4f_client = await get_client(user_id, "g4f_client", model_name=model_id)
                    return await user_g4f_client.chat.completions.create(
                        model=model_id,
                        messages=user_context["messages"],
                    )

                if should_bypass_timeout(model_id, api_type):
                    try:
                        response = await async_run_with_timeout(g4f_request, EXTENDED_API_TIMEOUT)
                        logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен с расширенным таймаутом {EXTENDED_API_TIMEOUT} сек{' в режиме длинного сообщения' if is_long_message else ''}")
                    except TimeoutError as e:
                        logging.error(f"Timeout in g4f_request{' (long message)' if is_long_message else ''}: {e}")
                        await message.reply(f"🕒 Превышено время ожидания ответа ({EXTENDED_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                        response = None
                else:
                    try:
                        response = await async_run_with_timeout(g4f_request, DEFAULT_API_TIMEOUT)
                    except TimeoutError as e:
                        logging.error(f"Timeout in {'g4f_request' if is_long_message else 'sync_g4f_request'}{' (long message)' if is_long_message else ''}: {e}")
                        await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                        response = None

                if response:
                    response_text = response.choices[0].message.content
                    logging.info(f"Запрос к G4F API завершен за {time.time() - start_time:.5f} секунд")
                    if not is_long_message:
                        user_context["messages"].append(
                            {"role": "assistant", "content": response_text}
                        )

        # Обработка через Gemini API
        elif api_type == "gemini":
            async def gemini_request():
                system_instruction = None
                history_for_model = []
                
                for msg in user_context["messages"]:
                    if msg["role"] == "system" and "parts" in msg and msg["parts"]:
                        system_instruction = msg["parts"][0].get("text", "")
                    else:

                        new_parts = []
                        for part in msg.get('parts', []):
                            if 'inline_data' in part and 'data' in part['inline_data']:
                                try:
                                    img_bytes = base64.b64decode(part['inline_data']['data'])
                                    new_parts.append(Image.open(io.BytesIO(img_bytes)))
                                except Exception:
                                    new_parts.append(part)
                            else:
                                new_parts.append(part)
                        msg['parts'] = new_parts
                        history_for_model.append(msg)
                
                if not system_instruction:
                    system_instruction = DEFAULT_SYSTEM_PROMPTS["default"]

                current_prompt = message_text if is_long_message else message.text
                history_for_model.append({'role': 'user', 'parts': [{'text': current_prompt}]})

                config = genai_types.GenerateContentConfig(
                    system_instruction=system_instruction
                ) if system_instruction else None
                
                response = await gemini_client.aio.models.generate_content(
                    model=model_id,
                    contents=history_for_model,
                    config=config
                )
                
                user_context["messages"].append({'role': 'user', 'parts': [{'text': current_prompt}]})

                return response

            current_time = time.strftime("%H:%M:%S", time.localtime())
            logging.info(f"[{current_time}] Начало запроса к Gemini API{' (длинное сообщение)' if is_long_message else ''}")
            
            if should_bypass_timeout(model_id, api_type):
                try:
                    response = await async_run_with_timeout(gemini_request, EXTENDED_API_TIMEOUT)
                    logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен с расширенным таймаутом {EXTENDED_API_TIMEOUT} сек{' в режиме длинного сообщения' if is_long_message else ''}")
                except TimeoutError as e:
                    logging.error(f"Timeout in gemini_request{' (long message)' if is_long_message else ''}: {e}")
                    await message.reply(f"🕒 Превышено время ожидания ответа ({EXTENDED_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                    response = None
            else:
                try:
                    response = await async_run_with_timeout(gemini_request, DEFAULT_API_TIMEOUT)
                except TimeoutError as e:
                    logging.error(f"Timeout in gemini_request{' (long message)' if is_long_message else ''}: {e}")
                    await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                    response = None

            if response:
                response_text = response.text
                logging.info(f"Запрос к Gemini API завершен за {time.time() - start_time:.5f} секунд")
                if not is_long_message:
                    user_context["messages"].append(
                        {"role": "model", "parts": [{"text": response_text}]}
                    )

        # Обработка через OpenAI API
        elif api_type in openai_clients:
            if not is_long_message and model_id == "openai-audio":
                try:
                    client = await get_openai_client(api_type)
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
                    
                    user_context = await load_context(user_id)
                    voice = user_context.get("voice")
                    
                    async def audio_api_request():
                        return await client.chat.completions.create(
                            model=model_id,
                            modalities=["text", "audio"],
                            audio={"voice": voice, "format": "wav"},
                            messages=current_message,
                            timeout=90
                        )
                    
                    try:
                        result = await async_run_with_timeout(audio_api_request, AUDIO_API_TIMEOUT)
                        logging.info(f"Прямой запрос к OpenAI Audio API завершен успешно")
                    except TimeoutError as e:
                        logging.error(f"Timeout in audio_api_request: {e}")
                        await message.reply(f"🕒 Превышено время ожидания ответа ({AUDIO_API_TIMEOUT} сек) от аудио-модели. Попробуйте еще раз или используйте другую модель.")
                        return None
                    
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
                                    await message.reply_audio(
                                        audio=types.BufferedInputFile(audio_file.read(), filename="response.ogg"),
                                        caption="🔊 Аудио-ответ"
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
                            
                            return response_text
                        else:
                            logging.error("Модель не вернула аудио в ответе")
                            await message.reply("🚨 Модель не вернула аудио-ответ")
                    else:
                        logging.error("Не получен ответ от API или ответ некорректен")
                        await message.reply("🚨 Не получен корректный ответ от API")
                        return None
                except Exception as e:
                    logging.error(f"Ошибка при обработке аудио запроса: {e}")
                    await message.reply(f"🚨 Ошибка при обработке аудио: {str(e)}")
                    return None
            else:
                if should_bypass_timeout(model_id, api_type):
                    try:
                        result = await async_run_with_timeout(call_openai_completion_async, EXTENDED_API_TIMEOUT, api_type, model_id, user_context["messages"])
                        logging.info(f"Запрос к {api_type} API с моделью {model_id} выполнен с расширенным таймаутом {EXTENDED_API_TIMEOUT} сек{' в режиме длинного сообщения' if is_long_message else ''}")
                    except TimeoutError as e:
                        logging.error(f"Timeout in openai_client request{' (long message)' if is_long_message else ''}: {e}")
                        await message.reply(f"🕒 Превышено время ожидания ответа ({EXTENDED_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                        result = None
                else:
                    try:
                        result = await async_run_with_timeout(call_openai_completion_async, DEFAULT_API_TIMEOUT, api_type, model_id, user_context["messages"])
                    except TimeoutError as e:
                        logging.error(f"Timeout in openai_client request{' (long message)' if is_long_message else ''}: {e}")
                        await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
                        result = None

            if result:
                if not hasattr(result, "choices") or not result.choices:
                    logging.error(f"Ответ от {api_type} API не содержит ожидаемых данных: {result}")
                    await message.reply(f"🚨 Ошибка: получен некорректный ответ от {api_type} API.")
                else:
                    response_text = result.choices[0].message.content
                    if not is_long_message:
                        user_context["messages"].append({"role": "assistant", "content": response_text})

        elif api_type in anthropic_clients:
            try:
                client = get_anthropic_client(api_type)
                logging.info(f"Начало запроса к Anthropic API с моделью {model_id}")
                
                user_context = await load_context(user_id)
                
                anthropic_messages = []
                system_content = None
                
                if user_context["messages"] and user_context["messages"][0]["role"] == "system":
                    system_content = user_context["messages"][0]["content"]
                
                for msg in user_context["messages"]:
                    if msg["role"] == "system":
                        continue
                    
                    if msg["role"] in ["user", "assistant"]:
                        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
                
                if not anthropic_messages:
                    if message_text:
                        anthropic_messages.append({"role": "user", "content": message_text})
                    else:
                        logging.error("Отсутствуют сообщения для отправки в Anthropic API")
                        await message.reply("🚨 Ошибка: нет сообщений для отправки в API.")
                        return None
                elif anthropic_messages[-1]["role"] != "user" and message_text:
                    anthropic_messages.append({"role": "user", "content": message_text})
                
                result = await async_run_with_timeout(
                    lambda: call_anthropic_completion_sync(api_type, model_id, anthropic_messages, system=system_content),
                    DEFAULT_API_TIMEOUT
                )
                
                if result:
                    response_text = result.content[0].text
                    if not is_long_message:
                        user_context["messages"].append({"role": "assistant", "content": response_text})
                    
            except TimeoutError as e:
                logging.error(f"Timeout in Anthropic API request: {e}")
                await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
            except Exception as e:
                logging.exception(f"Ошибка при вызове Anthropic API: {e}")
                await message.reply(f"❌ Ошибка при обработке запроса: {e}")
                
        if response_text:
            # Удаляем теги <think> и </think> из ответа модели
            response_text = response_text.replace("<think>", "").replace("</think>", "")
            
        return response_text
    
    except Exception as e:
        logging.error(f"Ошибка во время запроса к API: {e}")
        await message.reply(f"🚨Произошла ошибка: {e}")
        return None

@rate_limit
async def handle_all_messages(message: types.Message, state: FSMContext, audio_response=False):
    user_id = message.from_user.id
    start_time = time.time()
   
    user_context = await load_context(user_id)  
    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')

    user_is_admin = is_admin(user_id)
    user_context["messages"] = await trim_context(user_context["messages"], is_admin=user_is_admin)

    audio_data = None
    audio_file_id = None
    encoded_audio = None
    audio_format = None
    
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
                
                audio_bytes = await asyncio.to_thread(process_audio_sync, audio_bytes)
                audio_format = "mp3"
            
            encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')
                    
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

    message_text = message.text if message.text else ""
    
    response_text = await process_message(
        message=message,
        user_context=user_context,
        user_id=user_id,
        api_type=api_type,
        model_id=model_id,
        message_text=message_text,
        start_time=start_time,
        audio_data=audio_data,
        audio_format=audio_format,
        encoded_audio=encoded_audio,
        is_long_message=False
    )
    
    if response_text:
            if len(response_text) > MAX_MESSAGE_LENGTH:
                await send_message_in_parts(message, response_text, MAX_MESSAGE_LENGTH)
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                    temp_file.write(response_text)
                    temp_file_path = temp_file.name

                try:
                    async with aiofiles.open(temp_file_path, "rb") as file_to_send:
                        file_bytes = await file_to_send.read()
                        await message.reply_document(types.BufferedInputFile(file_bytes, filename="response.txt"))
                except Exception as e:
                    logging.error(f"Ошибка при отправке файла: {e}")
                    await message.answer("🚨 Не удалось отправить ответ в виде файла.")
                finally:
                    await aiofiles.os.remove(temp_file_path)
            else:
                try:
                    await message.reply(response_text, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
                    await message.answer(
                        f"🚨Произошла ошибка при форматировании сообщения: {e}\n\n"
                        "Отправляю без форматирования."
                    )
                    await message.reply(response_text)
                    
                    # Дополнительно отправляем ответ в виде текстового файла
                    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                        temp_file.write(response_text)
                        temp_file_path = temp_file.name

                    try:
                        async with aiofiles.open(temp_file_path, "rb") as file_to_send:
                            file_bytes = await file_to_send.read()
                            await message.reply_document(types.BufferedInputFile(file_bytes, filename="response.txt"))
                    except Exception as e:
                        logging.error(f"Ошибка при отправке файла: {e}")
                        await message.answer("🚨 Не удалось отправить ответ в виде файла.")
                    finally:
                        await aiofiles.os.remove(temp_file_path)

            await save_context(user_id, user_context)
            
            await calculate_and_show_processing_time(message, user_context, start_time)

@rate_limit
async def cmd_long_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    start_time = time.time()

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
            
            response_text = await process_message(
                message=message,
                user_context=user_context,
                user_id=user_id,
                api_type=api_type,
                model_id=model_id,
                message_text=long_message,
                start_time=start_time,
                is_long_message=True
            )

            if response_text:
                
                if len(response_text) > MAX_MESSAGE_LENGTH:
                    await send_message_in_parts(message, response_text, MAX_MESSAGE_LENGTH)
                    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                        temp_file.write(response_text)
                        temp_file_path = temp_file.name

                    try:
                        async with aiofiles.open(temp_file_path, "rb") as file_to_send:
                            file_bytes = await file_to_send.read()
                            await message.reply_document(types.BufferedInputFile(file_bytes, filename="response.txt"))
                    except Exception as e:
                        logging.error(f"Ошибка при отправке файла: {e}")
                        await message.answer("🚨 Не удалось отправить ответ в виде файла.")
                    finally:
                        await aiofiles.os.remove(temp_file_path)
                else:
                    try:
                        await message.reply(response_text, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
                        await message.answer(
                            f"🚨Произошла ошибка при форматировании сообщения: {e}\n\n"
                            "Отправляю без форматирования."
                        )
                        await message.reply(response_text)
                            
                        # Дополнительно отправляем ответ в виде текстового файла
                        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                            temp_file.write(response_text)
                            temp_file_path = temp_file.name

                        try:
                            async with aiofiles.open(temp_file_path, "rb") as file_to_send:
                                file_bytes = await file_to_send.read()
                                await message.reply_document(types.BufferedInputFile(file_bytes, filename="response.txt"))
                        except Exception as e:
                            logging.error(f"Ошибка при отправке файла: {e}")
                            await message.answer("🚨 Не удалось отправить ответ в виде файла.")
                        finally:
                            await aiofiles.os.remove(temp_file_path)

                if api_type != "gemini":
                    user_context["messages"].append(
                        {"role": "assistant", "content": response_text}
                    )
                else:
                    user_context["messages"].append(
                        {"role": "model", "parts": [{"text": response_text}]}
                    )
                await save_context(user_id, user_context)
                
                await calculate_and_show_processing_time(message, user_context, start_time)

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
    await state.set_state(Form.waiting_for_long_message)

async def call_openai_completion_async(api_type, model, messages, **kwargs):
    client = await get_openai_client(api_type)
    start_time = time.time()
    start_timestamp = time.strftime("%H:%M:%S", time.localtime(start_time))
    logging.info(f"[{start_timestamp}] Начало запроса к OpenAI API ({api_type}) с моделью {model}.")
    try:
        result = await client.chat.completions.create(model=model, messages=messages, **kwargs)
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

def call_anthropic_completion_sync(api_type, model, messages, system=None, **kwargs):
    client = get_anthropic_client(api_type)
    start_time = time.time()
    start_timestamp = time.strftime("%H:%M:%S", time.localtime(start_time))
    logging.info(f"[{start_timestamp}] Начало запроса к Anthropic API ({api_type}) с моделью {model}.")
    try:
        result = client.messages.create(
            model=model,
            messages=messages,
            system=system,
            max_tokens=4096,
            **kwargs
        )
        end_time = time.time()
        duration = end_time - start_time
        end_timestamp = time.strftime("%H:%M:%S", time.localtime(end_time))
        logging.info(f"[{end_timestamp}] Запрос к Anthropic API ({api_type}) завершён за {duration:.2f} секунд.")
        return result
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        end_timestamp = time.strftime("%H:%M:%S", time.localtime(end_time))
        logging.error(f"[{end_timestamp}] Ошибка при выполнении запроса к Anthropic API ({api_type}) с моделью {model} после {duration:.2f} секунд: {e}")
        raise

async def async_run_with_timeout(func, timeout, *args, **kwargs):
    try:
        if asyncio.iscoroutinefunction(func):
            task = asyncio.create_task(func(*args, **kwargs))
            return await asyncio.wait_for(task, timeout=timeout)
        else:
            loop = asyncio.get_running_loop()
            
            future = loop.run_in_executor(None, lambda: func(*args, **kwargs))
            return await asyncio.wait_for(future, timeout=timeout)
            
    except asyncio.TimeoutError:
        raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
