import asyncio
import base64
import io
import logging
import os
import time

import aiofiles.os
import aiofiles.tempfile
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from config import DEFAULT_SYSTEM_PROMPTS, Form, bot, gemini_client
from database import load_context, save_context
from google.genai import types as genai_types
from PIL import Image

from .files import process_local_file
from .messages import calculate_and_show_processing_time


async def handle_image(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.reply("🔔 Пожалуйста, отправьте изображение.")
        return

    photo = message.photo[-1]
    
    img_byte_io = io.BytesIO()
    await bot.download(file=photo.file_id, destination=img_byte_io)
    
    img_b64_str = await asyncio.to_thread(
        base64.b64encode, img_byte_io.getvalue()
    )

    await state.update_data(image_data=img_b64_str.decode('utf-8'))
    await message.reply("🔔 Изображение получено. Теперь отправьте текстовый промпт.")


async def process_custom_image_prompt(message: types.Message, state: FSMContext):
    start_time = time.time()
    user_id = message.from_user.id
    prompt = message.text
    
    try:
        data, user_context = await asyncio.gather(
            state.get_data(),
            load_context(user_id)
        )

        base64_image = data.get("image_data")
        if not base64_image:
            await message.reply("🔔 Сначала отправьте изображение.")
            return

        model_id, _ = user_context["model"].split('_')

        def _prepare_image(b64_data):
            image_bytes = base64.b64decode(b64_data)
            return Image.open(io.BytesIO(image_bytes))

        pil_image = await asyncio.to_thread(_prepare_image, base64_image)

        system_instruction = next(
            (msg["parts"][0]["text"] for msg in user_context.get("messages", []) if msg.get("role") == "system"),
            DEFAULT_SYSTEM_PROMPTS.get(user_context.get("system_role", "default"))
        )
        
        user_context["messages"] = [{"role": "system", "parts": [{"text": system_instruction}]}]

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction
        ) if system_instruction else None

        response = await gemini_client.aio.models.generate_content(
            model=model_id,
                contents=[pil_image, prompt],
                config=config,
        )
        response_text = response.text

        user_context["messages"].append({
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
            ]
        })
        user_context["messages"].append({"role": "model", "parts": [{"text": response_text}]})

        await save_context(user_id, user_context)
        try:
            await message.reply(response_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
            await message.reply(response_text)
        await calculate_and_show_processing_time(message, user_context, start_time)

    except Exception as e:
        logging.error(f"Ошибка при обработке изображения/промпта: {e}", exc_info=True)
        await message.reply(f"🚨 Произошла ошибка: {e}")
    finally:
        await state.set_state(Form.waiting_for_message)
        await state.update_data(image_data=None)

async def handle_document_with_conversion(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    file_id = message.document.file_id
    mime_type = message.document.mime_type
    file_name = message.document.file_name
    extension = file_name.split('.')[-1].lower() if '.' in file_name else ""

    mime_mapping = {
        "application/pdf": "application/pdf",
        "text/plain": "text/plain",
        "application/x-javascript": "application/x-javascript",
        "text/javascript": "application/x-javascript",
        "application/x-python": "application/x-python",
        "text/x-python": "application/x-python",
        "text/html": "text/html",
        "text/css": "text/css",
        "text/markdown": "text/md",
        "text/md": "text/md",
        "text/csv": "text/csv",
        "text/xml": "text/xml",
        "text/rtf": "text/rtf",
        "application/rtf": "text/rtf"
    }
    
    extension_mapping = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "js": "application/x-javascript",
        "py": "application/x-python",
        "html": "text/html",
        "htm": "text/html",
        "css": "text/css",
        "md": "text/md",
        "csv": "text/csv",
        "xml": "text/xml",
        "rtf": "text/rtf"
    }
    
    directly_supported = False
    if mime_type in mime_mapping:
        directly_supported = True
        mime_type = mime_mapping.get(mime_type, mime_type)
    elif extension in extension_mapping:
        directly_supported = True
        mime_type = extension_mapping[extension]
    
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_data = await bot.download_file(file_path)
    
    if directly_supported:
        base64_file = await asyncio.to_thread(
            lambda: base64.b64encode(file_data.read()).decode('utf-8')
        )

        user_context["messages"].append({
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": base64_file}}
            ]
        })

        await save_context(user_id, user_context)
        
        file_type = extension.upper() if extension else mime_type
        await message.reply(f"🔔Файл {file_type} получен и добавлен в контекст. Теперь вы можете задавать вопросы.")
    else:
        try:
            await message.reply("🔔Файл не поддерживается Gemini напрямую. Начинаю конвертацию...")
            
            async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as tmp_file:
                await tmp_file.write(file_data.read())
                temp_file_path = tmp_file.name
                
            file_content = await process_local_file(temp_file_path)
            
            if file_content == "Unsupported file type" or file_content.startswith("Error processing file"):
                await message.reply(
                    "🚨Не удалось конвертировать файл. Поддерживаемые форматы для конвертации:\n"
                    "- Документы: DOCX, DOC, XLSX, XLS"
                )
            else:
                base64_content = await asyncio.to_thread(
                    lambda: base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
                )
                
                user_context["messages"].append({
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": "text/plain", "data": base64_content}}
                    ]
                })
                                
                await save_context(user_id, user_context)
                await message.reply(f"🔔Файл {extension.upper()} успешно конвертирован в текстовый формат, закодирован в base64 и добавлен в контекст. Теперь вы можете задавать вопросы.")
                
            if os.path.exists(temp_file_path):
                await aiofiles.os.remove(temp_file_path)
        except Exception as e:
            logging.error(f"Ошибка при конвертации файла для Gemini: {e}")
            await message.reply(f"🚨Произошла ошибка при конвертации файла: {e}")
    
    await state.set_state(Form.waiting_for_message)

async def handle_pdf(message: types.Message, state: FSMContext):
    return await handle_document_with_conversion(message, state)

