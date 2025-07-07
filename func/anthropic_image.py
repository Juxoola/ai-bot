import base64
import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form, get_anthropic_client, bot
from database import load_context, save_context
from .messages import call_anthropic_completion_sync, async_run_with_timeout, DEFAULT_API_TIMEOUT
import time
from datetime import timedelta

async def process_image_with_anthropic(message: types.Message, state: FSMContext, prompt: str):
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
    
    messages_payload = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_type,
                        "data": base64_image
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }
    ]
    
    system_content = None
    if user_context["messages"] and user_context["messages"][0]["role"] == "system":
        system_content = user_context["messages"][0]["content"]

    try:
        logging.info(f"[{start_time}] Начало запроса к Anthropic API IMAGE ({api_type}) с моделью {model}.")
        completion = await async_run_with_timeout(
            call_anthropic_completion_sync,
            DEFAULT_API_TIMEOUT,
            api_type, 
            model, 
            messages_payload,
            system=system_content,
        )
        
        if completion is None:
            return
            
        response_text = completion.content[0].text
      
        for msg in messages_payload:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                text_parts = []
                for part in msg["content"]:
                    if part["type"] == "text":
                        text_parts.append(part["text"])
                    elif part["type"] == "image":
                        text_parts.append("[IMAGE]")
                
                user_context["messages"].append({"role": "user", "content": " ".join(text_parts)})
            else:
                user_context["messages"].append(msg)
                
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
        logging.error(f"Error during Anthropic image processing: {e}")
        await message.reply(f"🔔Произошла ошибка при обработке изображения: {e}")
    finally:
        await state.set_state(Form.waiting_for_message)
        await state.update_data(image_data=None, img_type=None)

async def process_custom_image_prompt_anthropic(message: types.Message, state: FSMContext):
    await process_image_with_anthropic(message, state, message.text)

async def handle_image_anthropic(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    img_bytes = await bot.download_file(file_info.file_path)
    img_b64_str = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

    if file_info.file_path.endswith('.jpg') or file_info.file_path.endswith('.jpeg'):
        img_type = 'image/jpeg'
    elif file_info.file_path.endswith('.png'):
        img_type = 'image/png'
    elif file_info.file_path.endswith('.gif'):
        img_type = 'image/gif'
    elif file_info.file_path.endswith('.webp'):
        img_type = 'image/webp'
    else:
        await message.reply("🔔Неподдерживаемый формат изображения. Пожалуйста, отправьте JPG, PNG, GIF или WEBP.")
        return

    await state.update_data(image_data=img_b64_str, img_type=img_type)
    await message.reply("🔔Теперь введите текстовый промпт к изображению.") 