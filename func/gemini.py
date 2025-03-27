from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form,  bot, DEFAULT_SYSTEM_PROMPTS
from database import load_context,save_context
import asyncio
import base64
import logging
from aiogram.enums import ParseMode
import google.generativeai as genai
import tempfile
import os

async def handle_image(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    photo = message.photo[-1]
    file_id = photo.file_id

    file = await bot.get_file(file_id)
    file_path = file.file_path

    image_data = await bot.download_file(file_path)

    base64_image = await asyncio.to_thread(
        lambda: base64.b64encode(image_data.read()).decode('utf-8')
    )

    user_context["messages"].append({
        "role": "user",
        "parts": [
            {"mime_type": "image/jpeg", "data": base64_image}
        ]
    })

    await save_context(user_id, user_context)
    await state.update_data(image_data=base64_image)
    await message.reply("🔔Изображение получено. Теперь отправьте текстовый промпт.")


async def process_custom_image_prompt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    prompt = message.text

    data = await state.get_data()
    base64_image = data.get("image_data")

    if not base64_image:
        await message.reply("🔔Сначала отправьте изображение.")
        return

    user_context = await load_context(user_id)
    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')

    new_message = {
        "role": "user",
        "parts": [
            {"text": prompt},
            {"mime_type": "image/jpeg", "data": base64_image}
        ]
    }

    user_context["messages"].append(new_message)

    await save_context(user_id, user_context)
    
    try:
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
            from google.genai import types as genai_types
            model = genai.GenerativeModel(
                model_id,
                system_instruction=system_instruction
            )
        else:
            model = genai.GenerativeModel(model_id)
        
        chat = model.start_chat(history=messages_for_model[:-1])
        response = await asyncio.to_thread(
            lambda: chat.send_message(messages_for_model[-1])
        )

        await message.reply(response.text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
        await bot.send_message(user_id,
            f"🚨Произошла ошибка при форматировании сообщения: {e}\n\n"
            "Отправляю без форматирования."
        )
        await message.reply(response.text)

        user_context["messages"].append({"role": "assistant", "content": response.text})
        await save_context(user_id, user_context)

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
                {"mime_type": mime_type, "data": base64_file}
            ]
        })

        await save_context(user_id, user_context)
        
        file_type = extension.upper() if extension else mime_type
        await message.reply(f"🔔Файл {file_type} получен и добавлен в контекст. Теперь вы можете задавать вопросы.")
    else:
        try:
            await message.reply("🔔Файл не поддерживается Gemini напрямую. Начинаю конвертацию...")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as tmp_file:
                tmp_file.write(file_data.read())
                temp_file_path = tmp_file.name
                
            from func.g4f import process_local_file
            
            file_content = await asyncio.to_thread(process_local_file, temp_file_path)
            
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
                        {"mime_type": "text/plain", "data": base64_content}
                    ]
                })
                
                await save_context(user_id, user_context)
                await message.reply(f"🔔Файл {extension.upper()} успешно конвертирован в текстовый формат, закодирован в base64 и добавлен в контекст. Теперь вы можете задавать вопросы.")
                
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception as e:
            logging.error(f"Ошибка при конвертации файла для Gemini: {e}")
            await message.reply(f"🚨Произошла ошибка при конвертации файла: {e}")
    
    await state.set_state(Form.waiting_for_message)

async def handle_pdf(message: types.Message, state: FSMContext):
    return await handle_document_with_conversion(message, state)

