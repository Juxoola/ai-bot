from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_aspect_ratio_selection_keyboard, get_model_selection_keyboard, get_image_gen_model_selection_keyboard, get_image_recognition_model_selection_keyboard, get_settings_keyboard
from config import bot, Form, update_user_clients, update_image_gen_client
from aiogram.fsm.context import FSMContext
import logging
from aiogram import types
from database import load_context, save_context, av_models, gen_models, rec_models, def_rec_model, def_gen_model, def_aspect, def_enhance
import google.generativeai as genai
import asyncio



async def cmd_settings(message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()
    AVAILABLE_MODELS = await av_models()

    current_model_key = user_context["model"] 
    current_model = AVAILABLE_MODELS[current_model_key]['model_name'] if current_model_key in AVAILABLE_MODELS else "Unknown"
    
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    web_search_enabled = user_context.get("web_search_enabled", False)
    show_processing_time = user_context.get("show_processing_time", True)

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        web_search_enabled,
        show_processing_time
    )

    msg = await message.reply("⚙️Меню настроек:", reply_markup=keyboard)
    await state.update_data(settings_message_id=msg.message_id, user_message_id=message.message_id)
    await state.set_state(Form.waiting_for_settings_selection)


async def select_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    AVAILABLE_MODELS = await av_models()
    await state.update_data(available_models=AVAILABLE_MODELS)
    
    keyboard = await get_model_selection_keyboard(AVAILABLE_MODELS)

    await bot.edit_message_text(
        "Выберите модель для чата:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_for_model_selection)

async def select_image_gen_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    IMAGE_GENERATION_MODELS = await gen_models()
    await state.update_data(available_image_gen_models=IMAGE_GENERATION_MODELS)

    keyboard = await get_image_gen_model_selection_keyboard(IMAGE_GENERATION_MODELS)

    await bot.edit_message_text(
        "Выберите модель для генерации изображений:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_for_image_generation_model)

async def select_image_rec_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    IMAGE_RECOGNITION_MODELS = await rec_models()
    await state.update_data(available_image_rec_models=IMAGE_RECOGNITION_MODELS)
    
    keyboard = await get_image_recognition_model_selection_keyboard(IMAGE_RECOGNITION_MODELS)

    await bot.edit_message_text(
        "Выберите модель для распознавания изображений:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_for_image_recognition_model)

async def select_aspect_ratio_handler(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = await get_aspect_ratio_selection_keyboard()

    await bot.edit_message_text(
        "Выберите соотношение сторон для генерации изображений:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_for_aspect_ratio)


async def process_enhance_selection_handler(callback_query, state):
    user_id = callback_query.from_user.id
    user_context = await load_context(user_id)
    
    user_context["enhance"] = not user_context.get("enhance", False)
    await save_context(user_id, user_context)

    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()

    AVAILABLE_MODELS = await av_models()
    current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", False)
    web_search_enabled = user_context.get("web_search_enabled", False)

    show_processing_time = user_context.get("show_processing_time", True)

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        web_search_enabled,
        show_processing_time
    )

    await bot.edit_message_text(
        "⚙️Меню настроек:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )

    status_text = "включено" if user_context["enhance"] else "выключено"
    await bot.answer_callback_query(callback_query.id, f"Enhance {status_text}")
    await state.set_state(Form.waiting_for_settings_selection)

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
    
    model_key = callback_query.data.split("model_")[1] 
    
    user_context = await load_context(user_id)
    AVAILABLE_MODELS = await av_models()
    
    if model_key in AVAILABLE_MODELS:
        new_api_type = AVAILABLE_MODELS[model_key]["api"]
        
        if new_api_type == "gemini":
            initial_messages = []
        elif new_api_type == "g4f":
            model_name=model_key.replace("_g4f", "")
            await asyncio.to_thread(update_user_clients, user_id, model_name)
            initial_messages = [{"role": "system", "content": "###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE."}]
        else:  # glhf or other APIs
            initial_messages = [{"role": "system", "content": "###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE."}]

        user_context.update({
            "model": model_key,
            "api_type": new_api_type,
            "messages": initial_messages,
            "g4f_image": None,
            "g4f_image_base64": None,
            "long_message": ""
        })
        
        await save_context(user_id, user_context)

        DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
        DEFAULT_ASPECT_RATIO = await def_aspect()
        DEFAULT_ENHANCE = await def_enhance()

        current_model = AVAILABLE_MODELS[model_key]['model_name']
        current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
        current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
        current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
        web_search_enabled = user_context.get("web_search_enabled", False)

        show_processing_time = user_context.get("show_processing_time", True)

        keyboard = await get_settings_keyboard(
            current_model,
            current_image_gen_model,
            current_aspect_ratio,
            current_enhance,
            web_search_enabled,
            show_processing_time
        )

        await bot.edit_message_text(
            "⚙️Меню настроек:",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
        
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Модель изменена на {current_model} и контекст очищен"
        )
    else:
        await bot.answer_callback_query(
            callback_query.id,
            text="Ошибка: модель не найдена"
        )
    
    await state.set_state(Form.waiting_for_settings_selection)

async def process_image_generation_model_handler(callback_query, state):
    user_id = callback_query.from_user.id
    data = callback_query.data.split('_', 3)
    
    if len(data) >= 3:
        model_id = data[2]
        api = data[3] if len(data) >= 4 else ""
        
        user_context = await load_context(user_id)
        user_context["image_generation_model"] = {
            "model_id": model_id,
            "api": api
        }
        
        # # Debug code to verify models
        # logging.info(f"BEFORE UPDATE - Main model: {user_context['model']}, Image gen model: {user_context['image_generation_model']}")

        await save_context(user_id, user_context)

        # user_context = await load_context(user_id)
        # logging.info(f"AFTER UPDATE - Main model: {user_context['model']}, Image gen model: {user_context['image_generation_model']}")
        
        if api == "g4f":
            await update_image_gen_client(user_id, model_id)
        
        DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
        DEFAULT_ASPECT_RATIO = await def_aspect()
        DEFAULT_ENHANCE = await def_enhance()

        AVAILABLE_MODELS = await av_models()
        current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
        current_image_gen_model = f"{model_id} ({api})"
        current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
        current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
        web_search_enabled = user_context.get("web_search_enabled", False)
        show_processing_time = user_context.get("show_processing_time", True)

        keyboard = await get_settings_keyboard(
            current_model,
            current_image_gen_model,
            current_aspect_ratio,
            current_enhance,
            web_search_enabled,
            show_processing_time
        )

        await bot.edit_message_text(
            "⚙️Меню настроек:",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
        
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Модель для генерации изображений изменена на {model_id} ({api})"
        )
    else:
        await bot.answer_callback_query(
            callback_query.id,
            text="Ошибка при выборе модели"
        )
    
    await state.set_state(Form.waiting_for_settings_selection)

async def process_image_recognition_model_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    model_name = callback_query.data.split("rec_model_")[1]
    
    user_context = await load_context(user_id)
    user_context["image_recognition_model"] = model_name
    await save_context(user_id, user_context)

    AVAILABLE_MODELS = await av_models()
    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_IMAGE_RECOGNITION_MODEL = await def_rec_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()

    current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_image_rec_model = model_name
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    web_search_enabled = user_context.get("web_search_enabled", False)

    show_processing_time = user_context.get("show_processing_time", True)

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        web_search_enabled,
        show_processing_time
    )

    await bot.edit_message_text(
        "⚙️Меню настроек:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    
    await bot.answer_callback_query(
        callback_query.id,
        text=f"Модель распознавания изменена на {model_name}"
    )
    await state.set_state(Form.waiting_for_settings_selection)

async def process_aspect_ratio_selection_handler(callback_query, state):
    user_id = callback_query.from_user.id
    aspect_ratio = callback_query.data.split("_", 2)[2]
    user_context = await load_context(user_id)

    user_context["aspect_ratio"] = aspect_ratio
    await save_context(user_id, user_context)

    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()

    AVAILABLE_MODELS = await av_models()
    current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    web_search_enabled = user_context.get("web_search_enabled", False)
    show_processing_time = user_context.get("show_processing_time", True)

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        web_search_enabled,
        show_processing_time
    )

    await bot.edit_message_text(
        "⚙️Меню настроек:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await bot.answer_callback_query(callback_query.id, f"Выбрано соотношение сторон: {aspect_ratio}")
    await state.set_state(Form.waiting_for_settings_selection)

async def toggle_web_search_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_context = await load_context(user_id)

    user_context["web_search_enabled"] = not user_context.get("web_search_enabled", False)
    await save_context(user_id, user_context)

    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()

    AVAILABLE_MODELS = await av_models()
    current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", False)
    web_search_enabled = user_context["web_search_enabled"]
    show_processing_time = user_context.get("show_processing_time", True)

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        web_search_enabled,
        show_processing_time
    )

    await bot.edit_message_text(
        "⚙️Меню настроек:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )

    status_text = "включен" if web_search_enabled else "выключен"
    await bot.answer_callback_query(callback_query.id, f"Веб-поиск {status_text}")
    await state.set_state(Form.waiting_for_settings_selection)

async def toggle_processing_time_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_context = await load_context(user_id)
    
    user_context["show_processing_time"] = not user_context.get("show_processing_time", True)
    await save_context(user_id, user_context)
    
    show_processing_time = user_context.get("show_processing_time", True)
    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()
    AVAILABLE_MODELS = await av_models()
    current_model = AVAILABLE_MODELS[user_context["model"]]['model_name']
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    web_search_enabled = user_context.get("web_search_enabled", False)

    keyboard = await get_settings_keyboard(
        current_model,
        current_image_gen_model,
        current_aspect_ratio,
        current_enhance,
        web_search_enabled,
        show_processing_time  
    )

    await bot.edit_message_text(
        "⚙️Меню настроек:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    status_text = "включено" if show_processing_time else "выключено"
    await bot.answer_callback_query(callback_query.id, f"Время обработки {status_text}")
    await state.set_state(Form.waiting_for_settings_selection)