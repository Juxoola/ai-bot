import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import (Form, anthropic_clients, dp, openai_clients,
                    update_image_client_for_recognition)
from database import load_context, rec_models
from func.anthropic_image import (handle_image_anthropic,
                                  process_custom_image_prompt_anthropic)
from func.decorators import access_required
from func.files import handle_files_or_urls
from func.g4f import handle_image_recognition
from func.gemini import (handle_document_with_conversion, handle_image,
                         process_custom_image_prompt)
from func.messages import handle_all_messages
from func.openai_image import (handle_image_openai,
                               process_custom_image_prompt_openai)
from handlers.check import (check_in_progress, clear_in_progress,
                            set_in_progress)
from handlers.rate_limit import check_rate_limit
import logging

FILE_PROCESSING_UNSUPPORTED = "🚨Обработка файлов не поддерживается данной моделью."
IMAGE_RECOGNITION_UNSUPPORTED = "🚨Распознавание изображений не поддерживается этой моделью."
IMAGE_RECOGNITION_HANDLER_NOT_FOUND = "🚨Распознавание изображений настроено, но обработчик не найден."
PROMPT_REQUIRED = "🔔Пожалуйста, сначала введите текстовый промпт."
IMAGE_PROMPT_REQUIRED = "🔔Пожалуйста, введите текстовый промпт к изображению."

ALLOWED_APIS = list(openai_clients.keys()) + ["g4f"]

IMAGE_HANDLERS = {
    "g4f": (Form.waiting_for_custom_image_recognition_prompt, handle_image_recognition, update_image_client_for_recognition),
    "gemini": (Form.waiting_for_image_and_prompt, handle_image, None),
    **{api: (Form.waiting_for_image_and_prompt_openai, handle_image_openai, None) for api in openai_clients},
    **{api: (Form.waiting_for_image_and_prompt_anthropic, handle_image_anthropic, None) for api in anthropic_clients},
}


async def is_model_supported_for_image_rec(model_id, api_type, image_rec_models):
    if api_type == "gemini":
        return True
    lookup_key = f"{model_id}_{api_type}"
    return lookup_key in image_rec_models


@dp.message()
@access_required
async def handle_all_messages_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not await check_rate_limit(message, "message"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
        
    user_context, current_state = await asyncio.gather(
        load_context(user_id),
        state.get_state()
    )
    if current_state is None:
        current_state = Form.waiting_for_message
        await state.set_state(Form.waiting_for_message)

    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')
    
    await set_in_progress(state, message)
    try:
        image_rec_models = None
        if current_state in [Form.waiting_for_image_and_prompt_openai, Form.waiting_for_image_and_prompt_anthropic]:
            image_rec_models = await rec_models()

        if (message.voice or message.audio or message.text) and api_type == "poli" and model_id == "openai-audio":
            await handle_all_messages(message, state, audio_response=True)
            return
            
        if message.document:
            if api_type in ALLOWED_APIS:
                await handle_files_or_urls(message, state)
            elif api_type == "gemini":
                await handle_document_with_conversion(message, state)
            else:
                await message.reply(FILE_PROCESSING_UNSUPPORTED)
            return
 
        if message.photo:
            image_rec_models = await rec_models()
            if await is_model_supported_for_image_rec(model_id, api_type, image_rec_models):
                handler_info = IMAGE_HANDLERS.get(api_type)
                if handler_info:
                    target_state, handler_func, update_func = handler_info
                    if current_state == target_state:
                        await message.reply(PROMPT_REQUIRED)
                    else:
                        if update_func:
                            await update_func(user_id, model_id)
                        await state.set_state(target_state)
                        await handler_func(message, state)
                else:
                    await message.reply(IMAGE_RECOGNITION_HANDLER_NOT_FOUND)
            else:
                await message.reply(IMAGE_RECOGNITION_UNSUPPORTED)
            return
 
        if current_state == Form.waiting_for_message:
            await handle_all_messages(message, state)
        elif current_state == Form.waiting_for_image_and_prompt:
            if message.text and api_type == "gemini":
                await process_custom_image_prompt(message, state)
            else:
                await message.reply(IMAGE_PROMPT_REQUIRED)
        elif current_state == Form.waiting_for_image_and_prompt_openai:
            lookup_key = f"{model_id}_{api_type}"
            if message.text and lookup_key in image_rec_models:
                await process_custom_image_prompt_openai(message, state)
            else:
                await message.reply(IMAGE_PROMPT_REQUIRED)
        elif current_state == Form.waiting_for_image_and_prompt_anthropic:
            lookup_key = f"{model_id}_{api_type}"
            if message.text and lookup_key in image_rec_models:
                await process_custom_image_prompt_anthropic(message, state)
            else:
                await message.reply(IMAGE_PROMPT_REQUIRED)
        else:
            await handle_all_messages(message, state)
            
    except ValueError as e:
        logging.error(f"🚨Ошибка конфигурации или данных: {e}")
        await message.reply(f"🚨Ошибка конфигурации или данных: {e}")
    except Exception as e:
        logging.error(f"🚨Произошла непредвиденная ошибка: {e}")
        await message.reply("🚨Произошла непредвиденная ошибка.")
    finally:
        await clear_in_progress(state, message)