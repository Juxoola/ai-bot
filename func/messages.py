import asyncio
import base64
import logging
import os
import re
import tempfile
import time
from datetime import timedelta

import aiofiles
import aiofiles.os
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from config import (DEFAULT_SYSTEM_PROMPTS, Form, anthropic_clients, bot,
                    gemini_client, get_anthropic_client, get_client,
                    get_openai_client, openai_clients, should_bypass_timeout)
from database import is_admin, load_context, save_context, trim_context
from func.decorators import rate_limit
from google.genai import types as genai_types
from pydub import AudioSegment

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

async def process_audio_async(ogg_bytes: bytes) -> bytes:
    temp_ogg_path = None
    temp_mp3_path = None
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_ogg:
            await temp_ogg.write(ogg_bytes)
            temp_ogg_path = temp_ogg.name

        temp_mp3_path = temp_ogg_path.replace('.ogg', '.mp3')

        def _convert_sync():
            audio = AudioSegment.from_ogg(temp_ogg_path)
            audio.export(temp_mp3_path, format="mp3")

        await asyncio.to_thread(_convert_sync)

        async with aiofiles.open(temp_mp3_path, 'rb') as mp3_file:
            mp3_bytes = await mp3_file.read()
        
        return mp3_bytes

    except Exception as e:
        print(f"Произошла ошибка при конвертации аудио: {e}")
        return None
    finally:
        if temp_ogg_path and await aiofiles.os.path.exists(temp_ogg_path):
            await aiofiles.os.remove(temp_ogg_path)
        if temp_mp3_path and await aiofiles.os.path.exists(temp_mp3_path):
            await aiofiles.os.remove(temp_mp3_path)

async def _process_g4f_message(message, user_context, user_id, model_id, message_text, is_long_message, start_time):
    if user_context.get("g4f_image") and (not is_long_message or model_id == user_context.get("image_recognition_model")):
        async def g4f_image_request():
            user_g4f_client = await get_client(user_id, "g4f_image_client", model_name=model_id)
            image_data = user_context["g4f_image"]
            image_to_use = image_data
            if hasattr(image_data, 'read') and not isinstance(image_data, str):
                async with aiofiles.open(image_data.name, 'rb') as f:
                    image_bytes = await f.read()
                image_b64 = await asyncio.to_thread(lambda: base64.b64encode(image_bytes).decode('utf-8'))
                image_to_use = f"data:image/jpeg;base64,{image_b64}"
            
            messages = user_context["messages"] if not is_long_message else [{"role": "user", "content": message_text}]
            return await user_g4f_client.chat.completions.create(model=model_id, messages=messages, image=image_to_use)

        logging.info(f"[{time.strftime('%H:%M:%S')}] Начало запроса к G4F image API{' (длинное сообщение)' if is_long_message else ''}")
        timeout = DEFAULT_API_TIMEOUT
        request_func = g4f_image_request
    else:
        async def g4f_request():
            user_g4f_client = await get_client(user_id, "g4f_client", model_name=model_id)
            return await user_g4f_client.chat.completions.create(model=model_id, messages=user_context["messages"])

        logging.info(f"[{time.strftime('%H:%M:%S')}] Начало запроса к G4F API{' (длинное сообщение)' if is_long_message else ''}")
        timeout = EXTENDED_API_TIMEOUT if should_bypass_timeout(model_id, "g4f") else DEFAULT_API_TIMEOUT
        request_func = g4f_request

    try:
        response = await async_run_with_timeout(request_func, timeout)
        if response:
            response_text = response.choices[0].message.content
            logging.info(f"Запрос к G4F API завершен за {time.time() - start_time:.5f} секунд")
            if not is_long_message:
                user_context["messages"].append({"role": "assistant", "content": response_text})
            return response_text
    except TimeoutError:
        logging.error(f"Тайм-аут в g4f запросе{' (длинное сообщение)' if is_long_message else ''}")
        await message.reply(f"🕒 Превышено время ожидания ответа ({timeout} сек). Попробуйте еще раз или выберите другую модель.")
    
    return None

async def _process_gemini_message(message, user_context, model_id, message_text, is_long_message, start_time):
    async def gemini_request():
        system_instruction = next((msg["parts"][0].get("text", "") for msg in user_context["messages"] if msg["role"] == "system" and msg.get("parts")), None)
        history_for_model = [msg for msg in user_context["messages"] if msg["role"] != "system"]
        
        if not system_instruction:
            system_instruction = DEFAULT_SYSTEM_PROMPTS.get("default")

        config = genai_types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
        
        response = await gemini_client.aio.models.generate_content(model=model_id, contents=history_for_model, config=config)
        
        return response

    logging.info(f"[{time.strftime('%H:%M:%S')}] Начало запроса к Gemini API{' (длинное сообщение)' if is_long_message else ''}")
    timeout = EXTENDED_API_TIMEOUT if should_bypass_timeout(model_id, "gemini") else DEFAULT_API_TIMEOUT

    try:
        response = await async_run_with_timeout(gemini_request, timeout)
        if response:
            response_text = response.text
            logging.info(f"Запрос к Gemini API завершен за {time.time() - start_time:.5f} секунд")
            if not is_long_message:
                user_context["messages"].append({"role": "model", "parts": [{"text": response_text}]})
            return response_text
    except TimeoutError:
        logging.error(f"Тайм-аут в gemini_request{' (длинное сообщение)' if is_long_message else ''}")
        await message.reply(f"🕒 Превышено время ожидания ответа ({timeout} сек). Попробуйте еще раз или выберите другую модель.")

    return None


async def _process_openai_audio_message(message, user_id, model_id, api_type, encoded_audio, audio_format, start_time):
    try:
        client = await get_openai_client(api_type)
        logging.info("Начало прямого запроса к OpenAI Audio API")
        
        current_message = [{"role": "user", "content": message.text}] if message.text else [{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": encoded_audio, "format": audio_format}}]}]
        
        user_context = await load_context(user_id)
        voice = user_context.get("voice")
        
        async def audio_api_request():
            return await client.chat.completions.create(model=model_id, modalities=["text", "audio"], audio={"voice": voice, "format": "wav"}, messages=current_message, timeout=90)
        
        result = await async_run_with_timeout(audio_api_request, AUDIO_API_TIMEOUT)
        
        if result and result.choices and hasattr(result.choices[0].message, 'audio') and result.choices[0].message.audio:
            choice = result.choices[0].message
            response_text = choice.audio.transcript
            response_audio = await asyncio.to_thread(lambda: base64.b64decode(choice.audio.data))
            
            temp_wav_path = f"temp_audio_{user_id}.wav"
            async with aiofiles.open(temp_wav_path, "wb") as f:
                await f.write(response_audio)
            
            temp_ogg_path = f"temp_audio_{user_id}.ogg"
            await asyncio.to_thread(lambda: AudioSegment.from_wav(temp_wav_path).export(temp_ogg_path, format="ogg"))
            
            try:
                 async with aiofiles.open(temp_ogg_path, "rb") as audio_file:
                    audio_data = await audio_file.read()
                    await message.reply_audio(audio=types.BufferedInputFile(audio_data, filename="response.ogg"), caption="🔊 Аудио-ответ")
            finally:
                if os.path.exists(temp_wav_path): await aiofiles.os.remove(temp_wav_path)
                if os.path.exists(temp_ogg_path): await aiofiles.os.remove(temp_ogg_path)
            
            if user_context.get("show_processing_time", True):
                processing_time = str(timedelta(seconds=int(time.time() - start_time)))
                await message.answer(f"⏳ Время обработки запроса: {processing_time}")
            
            return response_text
        else:
            logging.error("Модель не вернула аудио в ответе или ответ некорректен")
            await message.reply("🚨 Модель не вернула аудио-ответ или ответ некорректен")

    except TimeoutError:
        logging.error("Тайм-аут в audio_api_request")
        await message.reply(f"🕒 Превышено время ожидания ответа ({AUDIO_API_TIMEOUT} сек) от аудио-модели.")
    except Exception as e:
        logging.error(f"Ошибка при обработке аудио запроса: {e}")
        await message.reply("🚨 Ошибка при обработке аудио.")
        
    return None

async def _process_openai_text_message(message, user_context, model_id, api_type, is_long_message):
    timeout = EXTENDED_API_TIMEOUT if should_bypass_timeout(model_id, api_type) else DEFAULT_API_TIMEOUT
    try:
        result = await async_run_with_timeout(call_openai_completion_async, timeout, api_type, model_id, user_context["messages"])
        if result and hasattr(result, "choices") and result.choices:
            response_text = result.choices[0].message.content
            if not is_long_message:
                user_context["messages"].append({"role": "assistant", "content": response_text})
            return response_text
        else:
            logging.error(f"Ответ от {api_type} API не содержит ожидаемых данных: {result}")
            await message.reply(f"🚨 Ошибка: получен некорректный ответ от {api_type} API.")
    except TimeoutError:
        logging.error(f"Тайм-аут в openai_client запросе{' (длинное сообщение)' if is_long_message else ''}")
        await message.reply(f"🕒 Превышено время ожидания ответа ({timeout} сек). Попробуйте еще раз или выберите другую модель.")
    
    return None

async def _process_anthropic_message(message, user_context, user_id, model_id, api_type, message_text, is_long_message):
    try:
        system_content = None
        if user_context["messages"] and user_context["messages"][0]["role"] == "system":
            system_content = user_context["messages"][0]["content"]
        
        anthropic_messages = [msg for msg in user_context["messages"] if msg["role"] in ["user", "assistant"]]
        
        if not anthropic_messages or (anthropic_messages[-1]["role"] != "user" and message_text):
            anthropic_messages.append({"role": "user", "content": message_text})

        result = await async_run_with_timeout(
            lambda: call_anthropic_completion_sync(api_type, model_id, anthropic_messages, system=system_content),
            DEFAULT_API_TIMEOUT
        )
        
        if result:
            response_text = result.content[0].text
            if not is_long_message:
                user_context["messages"].append({"role": "assistant", "content": response_text})
            return response_text
            
    except TimeoutError:
        logging.error("Тайм-аут в Anthropic API запросе")
        await message.reply(f"🕒 Превышено время ожидания ответа ({DEFAULT_API_TIMEOUT} сек). Попробуйте еще раз или выберите другую модель.")
    except Exception as e:
        logging.exception(f"Ошибка при вызове Anthropic API: {e}")
        await message.reply("❌ Ошибка при обработке запроса.")
        
    return None

async def process_message(message: types.Message, user_context, user_id, api_type, model_id, message_text, start_time=None, audio_data=None, audio_format=None, encoded_audio=None, is_long_message=False):
    if start_time is None:
        start_time = time.time()
    
    response_text = None
    
    # Добавление текущего сообщения в контекст
    if api_type == "gemini":
        last_message = user_context["messages"][-1] if user_context["messages"] else None
        if last_message and last_message["role"] == "user" and any("data" in part for part in last_message.get("parts", [])):
            last_message["parts"].append({"text": message_text})
        else:
            user_context["messages"].append({"role": "user", "parts": [{"text": message_text}]})
    elif api_type in list(openai_clients.keys()) + ["g4f"]:
        user_context["messages"].append({"role": "user", "content": message_text})

    try:
        if api_type == "g4f":
            response_text = await _process_g4f_message(message, user_context, user_id, model_id, message_text, is_long_message, start_time)
        elif api_type == "gemini":
            response_text = await _process_gemini_message(message, user_context, model_id, message_text, is_long_message, start_time)
        elif api_type in openai_clients:
            if not is_long_message and model_id == "openai-audio":
                response_text = await _process_openai_audio_message(message, user_id, model_id, api_type, encoded_audio, audio_format, start_time)
            else:
                response_text = await _process_openai_text_message(message, user_context, model_id, api_type, is_long_message)
        elif api_type in anthropic_clients:
            response_text = await _process_anthropic_message(message, user_context, user_id, model_id, api_type, message_text, is_long_message)

        if response_text:
            response_text = response_text.replace("<think>", "").replace("</think>", "")
            
        return response_text
    
    except Exception as e:
        logging.error(f"Ошибка во время запроса к API: {e}")
        await message.reply("🚨Произошла ошибка.")
        return None

async def send_response(message: types.Message, response_text: str):
    try:
        if len(response_text) > MAX_MESSAGE_LENGTH:
            await send_message_in_parts(message, response_text, MAX_MESSAGE_LENGTH)
            # Дополнительно отправляем ответ в виде текстового файла для длинных сообщений
            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding='utf-8') as temp_file:
                await aiofiles.os.remove(temp_file.name) # aiofiles requires this
                async with aiofiles.open(temp_file.name, "w+", encoding='utf-8') as f:
                    await f.write(response_text)
                temp_file_path = temp_file.name

            async with aiofiles.open(temp_file_path, "rb") as file_to_send:
                await message.reply_document(types.BufferedInputFile(await file_to_send.read(), filename="response.txt"))
            await aiofiles.os.remove(temp_file_path)
        else:
            await message.reply(response_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        await message.answer(f"🚨 Произошла ошибка при форматировании сообщения. Отправляю без форматирования.")
        await message.reply(response_text)
        # Попытка отправить как файл в случае любой ошибки
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding='utf-8') as temp_file:
            await aiofiles.os.remove(temp_file.name)
            async with aiofiles.open(temp_file.name, "w+", encoding='utf-8') as f:
                await f.write(response_text)
            temp_file_path = temp_file.name
        try:
            async with aiofiles.open(temp_file_path, "rb") as file_to_send:
                await message.reply_document(types.BufferedInputFile(await file_to_send.read(), filename="response.txt"))
        except Exception as file_e:
            logging.error(f"Ошибка при отправке файла: {file_e}")
            await message.answer("🚨 Не удалось отправить ответ в виде файла.")
        finally:
            if await aiofiles.os.path.exists(temp_file_path):
                await aiofiles.os.remove(temp_file_path)

@rate_limit
async def handle_all_messages(message: types.Message, state: FSMContext, audio_response=False):
    user_id = message.from_user.id
    start_time = time.time()
   
    user_context = await load_context(user_id)
    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')

    user_context["messages"] = await trim_context(user_context["messages"], is_admin=is_admin(user_id))

    audio_data, encoded_audio, audio_format = None, None, None
    
    if audio_response and (message.voice or message.audio):
        try:
            audio_file = message.voice or message.audio
            file_info = await bot.get_file(audio_file.file_id)
            audio_data = await bot.download_file(file_info.file_path)
            audio_bytes = audio_data.read() if hasattr(audio_data, 'read') else audio_data
            
            if message.voice:
                audio_bytes = await process_audio_async(audio_bytes)
                audio_format = "mp3"
            elif message.audio and message.audio.mime_type:
                mime_type = message.audio.mime_type
                if "wav" in mime_type: audio_format = "wav"
                elif "mp3" in mime_type: audio_format = "mp3"

            if not audio_format:
                await message.reply("🚨 Неподдерживаемый формат аудио.")
                return

            encoded_audio = await asyncio.to_thread(lambda: base64.b64encode(audio_bytes).decode('utf-8'))
            if api_type not in openai_clients:
                await message.reply("🚨 Выбранная модель не поддерживает аудио-ответы.")
                return
            user_context["messages"].append({"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": encoded_audio, "format": audio_format}}]})

        except Exception as e:
            logging.error(f"Ошибка при обработке аудио: {e}")
            await message.reply("🚨 Произошла ошибка при обработке аудио.")
            return

    message_text = message.text or ""
    
    response_text = await process_message(message=message, user_context=user_context, user_id=user_id, api_type=api_type, model_id=model_id, message_text=message_text, start_time=start_time, audio_data=audio_data, audio_format=audio_format, encoded_audio=encoded_audio)
    
    if response_text:
        await send_response(message, response_text)
        await save_context(user_id, user_context)
        await calculate_and_show_processing_time(message, user_context, start_time)

@rate_limit
async def cmd_long_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    start_time = time.time()

    user_context = await load_context(user_id)
    current_state = await state.get_state()

    if current_state != Form.waiting_for_long_message:
        await message.reply("🔔Режим накопления сообщений активирован. Отправьте /long_message еще раз, чтобы завершить накопление и отправить сообщение модели.")
        await state.set_state(Form.waiting_for_long_message)
        return

    long_message_text = user_context.get("long_message")
    if not long_message_text:
        await state.set_state(Form.waiting_for_message)
        await message.reply("🔔Режим накопления сообщений отключен, так как не было накопленных сообщений.")
        return

    user_context["long_message"] = ""  # Очищаем сразу
    
    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')
    
    user_context["messages"] = await trim_context(user_context["messages"], is_admin=is_admin(user_id))
    
    response_text = await process_message(
        message=message,
        user_context=user_context,
        user_id=user_id,
        api_type=api_type,
        model_id=model_id,
        message_text=long_message_text,
        start_time=start_time,
        is_long_message=True
    )

    if response_text:
        await send_response(message, response_text)
        
        # Обновляем контекст после успешного ответа
        if api_type == "gemini":
            user_context["messages"].append({"role": "model", "parts": [{"text": response_text}]})
        else:
            user_context["messages"].append({"role": "assistant", "content": response_text})
        
        await save_context(user_id, user_context)
        await calculate_and_show_processing_time(message, user_context, start_time)

    await message.reply("🔔Длинное сообщение обработано.")
    await state.set_state(Form.waiting_for_message)
        
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
            try:
                return await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
        else:
            loop = asyncio.get_running_loop()
            
            future = loop.run_in_executor(None, lambda: func(*args, **kwargs))
            try:
                return await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                future.cancel()
                try:
                    await future
                except asyncio.CancelledError:
                    pass
                raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
            
    except asyncio.TimeoutError:
        raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
