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


@dp.message()
@access_required
async def handle_all_messages_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not await check_rate_limit(message, "message"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
        
    user_id = message.from_user.id
    user_context = await load_context(user_id)
    current_state = await state.get_state() or Form.waiting_for_message
    if await state.get_state() is None:
        await state.set_state(Form.waiting_for_message)

    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')
    
    try:
        await set_in_progress(state, message)
        
        if message.voice or message.audio:
            if api_type == "poli" and model_id == "openai-audio":
                await handle_all_messages(message, state, audio_response=True)
                await clear_in_progress(state, message)
                return
        if message.text and api_type == "poli" and model_id == "openai-audio":
            await handle_all_messages(message, state, audio_response=True)
            await clear_in_progress(state, message)
            return
            
        image_rec_models = await rec_models()
        allowed_apis = list(openai_clients.keys()) + ["g4f"]
        if message.document:
            if api_type in allowed_apis:
                await handle_files_or_urls(message, state)
            elif api_type == "gemini":
                await handle_document_with_conversion(message, state)
            else:
                await message.reply("🚨Обработка файлов не поддерживается данной моделью.")
            await clear_in_progress(state, message)
            return

        if message.photo:
            model_supported = False
            
            if api_type == "gemini":
                model_supported = True
            else:
                lookup_key = f"{model_id}_{api_type}"
                if lookup_key in image_rec_models:
                    model_supported = True
            
            if model_supported:
                if api_type == "g4f":
                    await update_image_client_for_recognition(user_id, model_id)
                    await state.set_state(Form.waiting_for_custom_image_recognition_prompt)
                    await handle_image_recognition(message, state)
                elif api_type == "gemini":
                    if current_state == Form.waiting_for_image_and_prompt:
                        await message.reply("🔔Пожалуйста, сначала введите текстовый промпт.")
                    else:
                        await state.set_state(Form.waiting_for_image_and_prompt)
                        await handle_image(message, state)
                elif api_type in openai_clients:
                    if current_state == Form.waiting_for_image_and_prompt_openai:
                        await message.reply("🔔Пожалуйста, сначала введите текстовый промпт.")
                    else:
                        await state.set_state(Form.waiting_for_image_and_prompt_openai)
                        await handle_image_openai(message, state)
                elif api_type in anthropic_clients:
                    if current_state == Form.waiting_for_image_and_prompt_anthropic:
                        await message.reply("🔔Пожалуйста, сначала введите текстовый промпт.")
                    else:
                        await state.set_state(Form.waiting_for_image_and_prompt_anthropic)
                        await handle_image_anthropic(message, state)
                else:
                    await message.reply("🚨Распознавание изображений настроено, но обработчик не найден.")
            else:
                await message.reply("🚨Распознавание изображений не поддерживается этой моделью.")
            await clear_in_progress(state, message)
            return

        if current_state == Form.waiting_for_message:
            await handle_all_messages(message, state)
        elif current_state == Form.waiting_for_image_and_prompt:
            if message.text and api_type == "gemini":
                await process_custom_image_prompt(message, state)
            else:
                await message.reply("🔔Пожалуйста, введите текстовый промпт к изображению.")
        elif current_state == Form.waiting_for_image_and_prompt_openai:
            model_supported = False
            lookup_key = f"{model_id}_{api_type}"
            if lookup_key in image_rec_models:
                model_supported = True
            
            if message.text and model_supported:
                await process_custom_image_prompt_openai(message, state)
            else:
                await message.reply("🔔Пожалуйста, введите текстовый промпт к изображению.")
        elif current_state == Form.waiting_for_image_and_prompt_anthropic:
            model_supported = False
            lookup_key = f"{model_id}_{api_type}"
            if lookup_key in image_rec_models:
                model_supported = True
            
            if message.text and api_type in anthropic_clients:
                await process_custom_image_prompt_anthropic(message, state)
            else:
                await message.reply("🔔Пожалуйста, введите текстовый промпт к изображению.")
        else:
            await handle_all_messages(message, state)
            
        await clear_in_progress(state, message)
    except Exception as e:
        await clear_in_progress(state, message)
        await message.reply(f"🚨Произошла ошибка: {e}") 