import base64
import logging
import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form, get_openai_client, bot
from database import load_context, save_context
from .messages import call_openai_completion_sync, async_run_with_timeout, DEFAULT_API_TIMEOUT
import time
from datetime import timedelta
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
        completion = await async_run_with_timeout(
            call_openai_completion_sync,
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

        end_time = time.time()
        processing_time = end_time - start_time
        formatted_processing_time = str(timedelta(seconds=int(processing_time)))
        service_info = f"⏳ Время обработки запроса: {formatted_processing_time}"

        if user_context.get("show_processing_time", True):
            await bot.send_message(user_id, service_info)

    except Exception as e:
        logging.error(f"Error during OpenAI image processing: {e}")
        await message.reply(f"🔔Произошла ошибка при обработке изображения: {e}")
    finally:
        await state.set_state(Form.waiting_for_message)
        await state.update_data(image_data=None, img_type=None)

async def process_custom_image_prompt_openai(message: types.Message, state: FSMContext):

    await process_image_with_openai(message, state, message.text)

async def handle_image_openai(message: types.Message, state: FSMContext):

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    img_bytes = await bot.download_file(file_info.file_path)
    img_b64_str = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

    if file_info.file_path.endswith('.jpg'):
        img_type = 'image/jpeg'
    elif file_info.file_path.endswith('.png'):
        img_type = 'image/png'
    else:
        await message.reply("🔔Неподдерживаемый формат изображения. Пожалуйста, отправьте JPG или PNG.")
        return

    await state.update_data(image_data=img_b64_str, img_type=img_type)
    await message.reply("🔔Теперь введите текстовый промпт к изображению.")