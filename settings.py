
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import (DEFAULT_SYSTEM_PROMPTS, Form, bot, update_image_gen_client,
                    update_user_clients, get_providers_for_model)
from database import (av_models, av_voices, def_aspect, def_enhance,
                      def_gen_model, def_voice, gen_models, load_context,
                      rec_models, save_context)
from keyboards import (get_api_selection_keyboard,
                       get_aspect_ratio_selection_keyboard,
                       get_image_gen_model_selection_keyboard,
                       get_models_by_api_keyboard, get_role_selection_keyboard,
                       get_settings_keyboard, get_voice_selection_keyboard)

import logging

async def format_image_gen_model_name(model_data):
    if isinstance(model_data, dict):
        return f"{model_data['model_id']} ({model_data['api']})"
    elif isinstance(model_data, str) and "_" in model_data:
        model, api = model_data.rsplit("_", 1)
        return f"{model} ({api})"
    return model_data

async def get_default_settings_values():
    return {
        "DEFAULT_IMAGE_GEN_MODEL": await def_gen_model(),
        "DEFAULT_ASPECT_RATIO": await def_aspect(),
        "DEFAULT_ENHANCE": await def_enhance(),
        "DEFAULT_VOICE": await def_voice(),
        "AVAILABLE_MODELS": await av_models(),
    }

async def update_system_message(messages, api_type, system_prompt):
    system_message_found = False
    for i, msg in enumerate(messages):
        if msg["role"] == "system":
            if api_type == "gemini" and "parts" in msg:
                messages[i] = {"role": "system", "parts": [{"text": system_prompt}]}
                system_message_found = True
                break
            elif api_type != "gemini" and "content" in msg:
                messages[i] = {"role": "system", "content": system_prompt}
                system_message_found = True
                break
    if not system_message_found:
        if api_type == "gemini":
            messages.insert(0, {"role": "system", "parts": [{"text": system_prompt}]})
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})
    return messages

async def _edit_message_reply_markup(callback_query: types.CallbackQuery, text: str, reply_markup: types.InlineKeyboardMarkup):
    await bot.edit_message_text(
        text,
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=reply_markup
    )

async def cmd_settings(message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    defaults = await get_default_settings_values()
    DEFAULT_IMAGE_GEN_MODEL = defaults["DEFAULT_IMAGE_GEN_MODEL"]
    DEFAULT_ASPECT_RATIO = defaults["DEFAULT_ASPECT_RATIO"]
    DEFAULT_ENHANCE = defaults["DEFAULT_ENHANCE"]
    DEFAULT_VOICE = defaults["DEFAULT_VOICE"]
    AVAILABLE_MODELS = defaults["AVAILABLE_MODELS"]

    current_model_key = user_context["model"]
    current_model = AVAILABLE_MODELS[current_model_key]['model_name'] if current_model_key in AVAILABLE_MODELS else "Unknown"
    
    current_image_gen_model = await format_image_gen_model_name(user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL))
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    current_voice = user_context.get("voice", DEFAULT_VOICE)
    show_processing_time = user_context.get("show_processing_time", False)
    current_role = user_context.get("system_role", "default")

    settings_keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        show_processing_time,
        current_voice,
        current_role
    )
    
    await message.reply("⚙️ Настройки:", reply_markup=settings_keyboard)
    await state.set_state(Form.waiting_for_settings_selection)


async def select_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    AVAILABLE_MODELS = await av_models()
    await state.update_data(available_models=AVAILABLE_MODELS)
    
    keyboard = await get_api_selection_keyboard(AVAILABLE_MODELS)

    await _edit_message_reply_markup(
        callback_query,
        "Выберите API для чата:",
        keyboard
    )
    await state.set_state(Form.waiting_for_api_selection)

async def api_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    AVAILABLE_MODELS = data.get("available_models", await av_models())
    
    api_type = callback_query.data.split("api_")[1]
    await state.update_data(selected_api=api_type)
    
    recognition_models = await rec_models()
    
    keyboard, model_map = await get_models_by_api_keyboard(AVAILABLE_MODELS, api_type, recognition_models)
    await state.update_data(model_map=model_map)

    await _edit_message_reply_markup(
        callback_query,
        f"Выберите модель {api_type.upper()} для чата:",
        keyboard
    )
    await state.set_state(Form.waiting_for_model_selection)

async def select_image_gen_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    IMAGE_GENERATION_MODELS = await gen_models()
    
    keyboard, model_map = await get_image_gen_model_selection_keyboard(IMAGE_GENERATION_MODELS)
    
    await state.update_data(image_gen_model_map=model_map)

    await _edit_message_reply_markup(
        callback_query,
        "Выберите модель для генерации изображений:",
        keyboard
    )
    await state.set_state(Form.waiting_for_image_generation_model)

async def select_aspect_ratio_handler(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = await get_aspect_ratio_selection_keyboard()

    await _edit_message_reply_markup(
        callback_query,
        "Выберите соотношение сторон для генерации изображений:",
        keyboard
    )
    await state.set_state(Form.waiting_for_aspect_ratio)

async def select_voice_handler(callback_query: types.CallbackQuery, state: FSMContext):
    available_voices = await av_voices()
    keyboard = await get_voice_selection_keyboard(available_voices)

    await _edit_message_reply_markup(
        callback_query,
        "Выберите голос для аудио-ответов:",
        keyboard
    )
    await state.set_state(Form.waiting_for_voice_selection)

async def select_role_handler(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = await get_role_selection_keyboard()

    await _edit_message_reply_markup(
        callback_query,
        "Выберите роль для бота:",
        keyboard
    )
    await state.set_state(Form.waiting_for_role_selection)

async def update_setting_and_refresh_keyboard(callback_query, state, user_context):

    user_id = callback_query.from_user.id
    await save_context(user_id, user_context)

    defaults = await get_default_settings_values()
    DEFAULT_IMAGE_GEN_MODEL = defaults["DEFAULT_IMAGE_GEN_MODEL"]
    DEFAULT_ASPECT_RATIO = defaults["DEFAULT_ASPECT_RATIO"]
    DEFAULT_ENHANCE = defaults["DEFAULT_ENHANCE"]
    DEFAULT_VOICE = defaults["DEFAULT_VOICE"]
    AVAILABLE_MODELS = defaults["AVAILABLE_MODELS"]
    
    current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
    
    current_image_gen_model = await format_image_gen_model_name(user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL))
    
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    show_processing_time = user_context.get("show_processing_time", False)
    current_voice = user_context.get("voice", DEFAULT_VOICE)
    current_role = user_context.get("system_role", "default")

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        show_processing_time,
        current_voice,
        current_role
    )

    await _edit_message_reply_markup(
        callback_query,
        "⚙️ Меню настроек:",
        keyboard
    )
    
    await state.set_state(Form.waiting_for_settings_selection)
    return keyboard

async def process_enhance_selection_handler(callback_query, state):
    user_id = callback_query.from_user.id
    user_context = await load_context(user_id)
    
    user_context["enhance"] = not user_context.get("enhance", False)
    
    await update_setting_and_refresh_keyboard(callback_query, state, user_context)
    
    status_text = "включено" if user_context["enhance"] else "выключено"
    await bot.answer_callback_query(callback_query.id, f"Enhance {status_text}")

async def close_settings_handler(callback_query, state):
    data = await state.get_data()

    await bot.delete_message(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    await state.set_state(Form.waiting_for_message)

async def model_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = await state.get_data()
    
    short_id = callback_query.data.split("model_")[1]
    model_map = data.get("model_map", {})
    
    if short_id not in model_map:
        await bot.answer_callback_query(callback_query.id, text="Модель не найдена")
        return
        
    model_key = model_map[short_id]
    
    user_context = await load_context(user_id)
    AVAILABLE_MODELS = await av_models()
    
    if model_key in AVAILABLE_MODELS:
        new_api_type = AVAILABLE_MODELS[model_key]["api"]
        
        system_role = user_context.get("system_role", "default")
        system_prompt = DEFAULT_SYSTEM_PROMPTS.get(system_role, DEFAULT_SYSTEM_PROMPTS["default"])
        
        user_context["messages"] = await update_system_message(user_context.get("messages", []), new_api_type, system_prompt)
            
        if new_api_type == "g4f":
            model_name = model_key.replace("_g4f", "")
            await update_user_clients(user_id, model_name)
            
            # Получаем список провайдеров для выбранной g4f модели
            providers = await get_providers_for_model(model_name)
            providers_text = ", ".join(providers) if providers else "Нет доступных провайдеров"
            
            logging.info(f"User {user_id}: Доступные провайдеры для модели {model_name}: {providers_text}")

        user_context.update({
            "model": model_key,
            "api_type": new_api_type,
            "g4f_image": None,
            "g4f_image_base64": None,
            "long_message": ""
        })
        
        await update_setting_and_refresh_keyboard(callback_query, state, user_context)
        
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Модель изменена на {AVAILABLE_MODELS[model_key]['model_name']} и контекст очищен"
        )
    else:
        await bot.answer_callback_query(
            callback_query.id,
            text="Ошибка: модель не найдена"
        )
    
    await state.set_state(Form.waiting_for_settings_selection)

async def process_image_generation_model_handler(callback_query, state):
    user_id = callback_query.from_user.id
    short_id = callback_query.data.split("gen_model_")[1]
    
    data = await state.get_data()
    model_map = data.get("image_gen_model_map", {})
    
    if short_id not in model_map:
        await bot.answer_callback_query(callback_query.id, text="Модель не найдена")
        return
        
    model_key = model_map[short_id]
    
    model_id, api = model_key.split('_', 1)
    
    user_context = await load_context(user_id)
    user_context["image_generation_model"] = f"{model_id}_{api}"

    if api == "g4f":
        await update_image_gen_client(user_id, model_id)
    
    await update_setting_and_refresh_keyboard(callback_query, state, user_context)
    
    await bot.answer_callback_query(
        callback_query.id,
        text=f"Модель для генерации изображений изменена на {model_id} ({api})"
    )

async def process_aspect_ratio_selection_handler(callback_query, state):
    user_id = callback_query.from_user.id
    aspect_ratio = callback_query.data.split("_", 2)[2]
    user_context = await load_context(user_id)

    user_context["aspect_ratio"] = aspect_ratio
    
    await update_setting_and_refresh_keyboard(callback_query, state, user_context)
    
    await bot.answer_callback_query(callback_query.id, f"Выбрано соотношение сторон: {aspect_ratio}")

async def toggle_processing_time_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_context = await load_context(user_id)
    
    user_context["show_processing_time"] = not user_context.get("show_processing_time", True)
    
    await update_setting_and_refresh_keyboard(callback_query, state, user_context)
    
    status_text = "включено" if user_context["show_processing_time"] else "выключено"
    await bot.answer_callback_query(callback_query.id, f"Время обработки {status_text}")

async def process_voice_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    selected_voice = callback_query.data.split("voice_")[1]
    
    user_context = await load_context(user_id)
    user_context["voice"] = selected_voice
    
    await update_setting_and_refresh_keyboard(callback_query, state, user_context)
    
    await bot.answer_callback_query(callback_query.id, f"Выбран голос: {selected_voice}")

async def role_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    selected_role = callback_query.data.split("role_")[1]
    
    user_context = await load_context(user_id)
    api_type = user_context["api_type"]
    
    user_context["system_role"] = selected_role
    
    system_prompt = DEFAULT_SYSTEM_PROMPTS.get(selected_role, DEFAULT_SYSTEM_PROMPTS["default"])
    user_context["messages"] = await update_system_message(user_context.get("messages", []), api_type, system_prompt)
    
    await update_setting_and_refresh_keyboard(callback_query, state, user_context)
    
    await bot.answer_callback_query(callback_query.id, f"Роль успешно изменена на: {selected_role}")
