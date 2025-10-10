import asyncio
import base64
import logging
import time
from io import BytesIO

from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form, bot
from database import load_context, save_context

from .messages import (call_openai_completion_async)

from .utils import (async_run_with_timeout,
                    calculate_and_show_processing_time, DEFAULT_API_TIMEOUT)

async def process_image_with_openai(message: types.Message, state: FSMContext, prompt: str):
    start_time = time.time()

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    
    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')
    model = model_id

    data = await state.get_data()
    base64_image = data.get("image_data")
    if not base64_image:
        await message.reply("🔔Сначала отправьте изображение.")
        await state.set_state(Form.waiting_for_message)
        return

    img_type = data.get("img_type")
    image_data_url = f"data:{img_type};base64,{base64_image}"

    messages_payload = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url}
                }
            ],
        }
    ]

    try:
        logging.info(f"[{start_time}] Начало запроса к OpenAI API IMAGE ({api_type}) с моделью {model}.")
        completion = await async_run_with_timeout(
            call_openai_completion_async,
            DEFAULT_API_TIMEOUT,
            api_type, 
            model, 
            messages_payload
        )
        
        if completion is None:
            return
            
        response_text = completion.choices[0].message.content
      
        user_context["messages"].extend(messages_payload)
        user_context["messages"].append({"role": "assistant", "content": response_text})
        await save_context(user_id, user_context)

        await message.reply(response_text)

        await calculate_and_show_processing_time(message, user_context, start_time)

    except Exception as e:
        logging.error(f"Ошибка при обработке изображения OpenAI: {e}")
        await message.reply("🔔Произошла ошибка при обработке изображения.")
    finally:
        await state.set_state(Form.waiting_for_message)
        await state.update_data(image_data=None, img_type=None)

async def process_custom_image_prompt_openai(message: types.Message, state: FSMContext):

    await process_image_with_openai(message, state, message.text)

async def handle_image_openai(message: types.Message, state: FSMContext):

    photo = message.photo[-1]

    file_info = await bot.get_file(photo.file_id)
    img_io = BytesIO()
    await bot.download_file(file_info.file_path, destination=img_io)
    image_bytes = img_io.getvalue()

    img_b64_str = await asyncio.to_thread(encode_image_to_base64_sync, image_bytes)

    if file_info.file_path.endswith(('.jpg', '.jpeg')):
        img_type = 'image/jpeg'
    elif file_info.file_path.endswith('.png'):
        img_type = 'image/png'
    else:
        await message.reply("🔔 Неподдерживаемый формат изображения. Пожалуйста, отправьте JPG или PNG.")
        return

    await state.update_data(image_data=img_b64_str, img_type=img_type)
    await message.reply("🔔 Теперь введите текстовый промпт к изображению.")

def encode_image_to_base64_sync(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")