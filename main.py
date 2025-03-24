import logging
logging.basicConfig(level=logging.INFO, force=True)

from dotenv import load_dotenv 

load_dotenv()

import os.path
from g4f.cookies import set_cookies_dir, read_cookie_files
from config import Form, bot, dp, init_enhance_prompt_client, update_image_client_for_recognition, openai_clients, DEFAULT_SYSTEM_PROMPTS
from database import load_context,save_context, is_admin,is_allowed, initialize_database, clear_all_user_contexts, initialize_models, rec_models, whisp_models, def_rec_model, def_gen_model, def_aspect, db_pool, def_enhance, init_all_user_clients, av_models, rec_models, def_voice

from keyboards import get_admin_keyboard, get_main_keyboard

from func.gemini import handle_pdf, process_custom_image_prompt, handle_image, handle_document_with_conversion
from func.g4f import process_image_generation_prompt, handle_image_recognition, handle_files_or_urls, process_image_editing, process_local_file

from func.audio import handle_audio, process_whisper_model_selection
from func.search import process_search_query
from func.messages import handle_all_messages,cmd_long_message,handle_long_message
from func.admin import cmd_add_user, cmd_add_model,cmd_add_image_gen_model,cmd_add_image_rec_model,cmd_delete_image_gen_model,cmd_delete_model,cmd_delete_image_rec_model,cmd_remove_user,process_add_user_id,process_remove_user_id,process_new_model_name,process_new_model_id,process_new_model_api,process_confirm_delete,process_delete_model_name,process_new_image_rec_model_id,process_new_image_rec_model_api,process_delete_image_rec_model_name,process_confirm_delete_image_rec_model,process_new_image_gen_model_api,process_new_image_gen_model_id, process_delete_image_gen_model_name,process_confirm_delete_image_gen_model, cmd_send_to_all, cmd_send_to_user, process_message_to_all, process_user_id_to_send, process_message_to_user


from settings import cmd_settings, select_model_handler, select_image_gen_model_handler, select_image_rec_model_handler, select_aspect_ratio_handler, process_enhance_selection_handler, close_settings_handler, model_selection_handler, process_image_generation_model_handler, process_image_recognition_model_selection_handler, process_aspect_ratio_selection_handler, toggle_processing_time_handler, select_role_handler, select_voice_handler, process_voice_selection_handler, role_selection_handler, api_selection_handler

from func.openai_image import process_custom_image_prompt_openai, handle_image_openai

from aiogram.enums import ParseMode
import asyncio
from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode



#admin section
@dp.message(Command("send_to_all"))
async def cmd_send_to_all_handler(message: types.Message, state: FSMContext):
    await cmd_send_to_all(message, state)

@dp.message(Form.waiting_for_message_to_all)
async def process_message_to_all_handler(message: types.Message, state: FSMContext):
    await process_message_to_all(message, state)

@dp.message(Command("send_to_user"))
async def cmd_send_to_user_handler(message: types.Message, state: FSMContext):
    await cmd_send_to_user(message, state)

@dp.message(Form.waiting_for_user_id_to_send)
async def process_user_id_to_send_handler(message: types.Message, state: FSMContext):
    await process_user_id_to_send(message, state)

@dp.message(Form.waiting_for_message_to_user)
async def process_message_to_user_handler(message: types.Message, state: FSMContext):
    await process_message_to_user(message, state)



@dp.message(Command("add_user"))
async def cmd_add_user_handler(message: types.Message, state: FSMContext):
    await cmd_add_user(message, state)

@dp.message(Form.waiting_for_add_user_id)
async def process_add_user_id_handler(message: types.Message, state: FSMContext):
    await process_add_user_id(message, state)

@dp.message(Command("remove_user"))
async def cmd_remove_user_handler(message: types.Message, state: FSMContext):
    await cmd_remove_user(message, state)

@dp.message(Form.waiting_for_remove_user_id)
async def process_remove_user_id_handler(message: types.Message, state: FSMContext):
    await process_remove_user_id(message, state)

@dp.message(Command("add_model"))
async def cmd_add_model_handler(message: types.Message, state: FSMContext):
    await cmd_add_model(message, state)

@dp.message(Command("delete_model"))
async def cmd_delete_model_handler(message: types.Message, state: FSMContext):
    await cmd_delete_model(message, state)

@dp.message(Form.waiting_for_new_model_name)
async def process_new_model_name_handler(message: types.Message, state: FSMContext):
    await process_new_model_name(message, state)

@dp.message(Form.waiting_for_new_model_id)
async def process_new_model_id_handler(message: types.Message, state: FSMContext):
    await process_new_model_id(message, state)

@dp.message(Form.waiting_for_new_model_api)
async def process_new_model_api_handler(message: types.Message, state: FSMContext):
    await process_new_model_api(message, state)

@dp.callback_query(Form.waiting_for_confirmation, lambda c: c.data and c.data.startswith('confirm_delete_'))
async def process_confirm_delete_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete(callback_query, state)

@dp.callback_query(Form.waiting_for_delete_model_name)
async def process_delete_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_model_name(callback_query, state)

@dp.message(Command("add_image_rec_model"))
async def cmd_add_image_rec_model_handler(message: types.Message, state: FSMContext):
    await cmd_add_image_rec_model(message, state)

@dp.message(Command("delete_image_rec_model"))
async def cmd_delete_image_rec_model_handler(message: types.Message, state: FSMContext):
    await cmd_delete_image_rec_model(message, state)


@dp.callback_query(Form.waiting_for_delete_image_rec_model_name)
async def process_delete_image_rec_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_image_rec_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_rec_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_rec_"))
async def process_confirm_delete_image_rec_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete_image_rec_model(callback_query, state)

@dp.message(Command("add_image_gen_model"))
async def cmd_add_image_gen_model_handler(message: types.Message, state: FSMContext):
    await cmd_add_image_gen_model(message, state)

@dp.message(Command("delete_image_gen_model"))
async def cmd_delete_image_gen_model_handler(message: types.Message, state: FSMContext):
    await cmd_delete_image_gen_model(message, state)



@dp.callback_query(Form.waiting_for_delete_image_gen_model_name)
async def process_delete_image_gen_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_image_gen_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_gen_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_gen_"))
async def process_confirm_delete_image_gen_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete_image_gen_model(callback_query, state)

@dp.message(Form.waiting_for_new_image_rec_model_id)
async def process_new_image_rec_model_id_handler(message: types.Message, state: FSMContext):
    await process_new_image_rec_model_id(message, state)

@dp.message(Form.waiting_for_new_image_rec_model_api)
async def process_new_image_rec_model_api_handler(message: types.Message, state: FSMContext):
    await process_new_image_rec_model_api(message, state)

@dp.message(Form.waiting_for_image_edit_instructions)
async def process_image_edit_instructions_handler(message: types.Message, state: FSMContext):
    instructions = message.text
    await state.update_data(image_edit_instructions=instructions)
    await state.set_state(Form.waiting_for_message)
    await process_image_editing(message, state)

@dp.message(Form.waiting_for_new_image_gen_model_id)
async def process_new_image_gen_model_id_handler(message: types.Message, state: FSMContext):
    await process_new_image_gen_model_id(message, state)

@dp.message(Form.waiting_for_new_image_gen_model_api)
async def process_new_image_gen_model_api_handler(message: types.Message, state: FSMContext):
    await process_new_image_gen_model_api(message, state)

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN,
                          reply_markup=await get_main_keyboard(include_admin_button=False))
        return

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    api_type = user_context["api_type"]
    
    await save_context(user_id, user_context)

    if is_admin(user_id):
        await message.reply(
            "Привет, админ! Я чат-бот, который может использовать различные ИИ-модели.\n"
            "Используйте /help, чтобы увидеть доступные команды.\n"
            "Если клавиатура пропала, используйте /keyboard для её восстановления.",
            reply_markup=await get_main_keyboard(include_admin_button=True)
        )
    else:
        await message.reply(
            "Привет! Я чат-бот, который может использовать различные ИИ-модели.\n"
            "Используйте /help, чтобы увидеть доступные команды.\n"
            "Если клавиатура пропала, используйте /keyboard для её восстановления.",
            reply_markup=await get_main_keyboard(include_admin_button=False)
        )

    await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "Открыть админ-клавиатуру", lambda message: is_admin(message.from_user.id))
async def cmd_open_admin_keyboard(message: types.Message, state: FSMContext):
    await message.reply("🔔Вы открыли админ-клавиатуру.", reply_markup= await get_admin_keyboard())

@dp.message(F.text == "Главное меню", lambda message: is_admin(message.from_user.id))
async def cmd_back_to_main_menu(message: types.Message, state: FSMContext):
    await message.reply("🔔Вы вернулись в главное меню.", reply_markup=await get_main_keyboard(include_admin_button=True))
    await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "ℹ️ Помощь")
@dp.message(F.text == "/help")
async def cmd_help(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    AVAILABLE_MODELS = await av_models()
    REC_MODELS = await rec_models()
    
    help_text = (
        "Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать это справочное сообщение\n"
        "/settings - Открыть меню настроек\n"
        "/clear - Очистить контекст беседы\n"
        "/generate_image - Сгенерировать изображение\n"
        "/audio - Отправить аудио для транскрипции (Whisper)\n"
        "/search - Выполнить поиск в интернете\n"
        "/long_message - Режим накопления сообщений\n"
        "/keyboard - Восстановить клавиатуру, если она исчезла\n"
        "Также можно присылать документы и изображения\n"
    )
    
    await message.reply(help_text)
    
    rec_models_by_api = {}
    for model_key, model_data in REC_MODELS.items():
        api = model_data["api"]
        if api not in rec_models_by_api:
            rec_models_by_api[api] = []
        
        model_id = model_data["model_id"]
        display_name = None
        lookup_key = f"{model_id}_{api}"
        
        if lookup_key in AVAILABLE_MODELS:
            display_name = AVAILABLE_MODELS[lookup_key]["model_name"]
        else:
            display_name = model_id
            
        rec_models_by_api[api].append(display_name)
    
    if rec_models_by_api:
        models_text = "📷 Доступные модели для распознавания изображений:\n\n"
        for api, models in rec_models_by_api.items():
            models_text += f"API: {api.upper()}\n"
            models_text += "• " + "\n• ".join(models) + "\n\n"
        
        await message.answer(models_text)

    if is_admin(message.from_user.id):
        await message.answer(
            "Команды администратора:\n"
            "/add_model - Добавить новую модель для чата\n"
            "/delete_model - Удалить существующую модель для чата\n"
            "/add_image_gen_model - Добавить новую модель для генерации изображений\n"
            "/delete_image_gen_model - Удалить существующую модель для генерации изображений\n"
            "/add_image_rec_model - Добавить новую модель для распознавания изображений\n"
            "/delete_image_rec_model - Удалить существующую модель для распознавания изображений\n"
            "/add_user - Добавить пользователя\n"
            "/remove_user - Удалить пользователя\n"
            "/send_to_all - Отправить сообщение всем пользователям\n"
            "/send_to_user - Отправить сообщение конкретному пользователю\n"
        )

@dp.message(F.text == "⚙️ Настройки")
@dp.message(F.text == "/settings")
async def cmd_settings_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    await cmd_settings(message, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "select_model")
async def select_model_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await select_model_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "select_image_gen_model")
async def select_image_gen_model_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await select_image_gen_model_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "select_image_rec_model")
async def select_image_rec_model_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await select_image_rec_model_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "select_aspect_ratio")
async def select_aspect_ratio_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await select_aspect_ratio_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "toggle_enhance")
async def toggle_enhance_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_enhance_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "close_settings")
async def close_settings_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await close_settings_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_model_selection, lambda c: c.data and c.data.startswith('model_'))
async def model_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await model_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_api_selection, lambda c: c.data and c.data.startswith('api_'))
async def api_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await api_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_image_generation_model, lambda c: c.data and c.data.startswith('gen_model_'))
async def process_image_generation_model_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_image_generation_model_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_image_recognition_model, lambda c: c.data and c.data.startswith('rec_model_'))
async def process_image_recognition_model_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_image_recognition_model_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_aspect_ratio, lambda c: c.data and c.data.startswith("aspect_ratio_"))
async def process_aspect_ratio_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_aspect_ratio_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "toggle_processing_time")
async def toggle_processing_time_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await toggle_processing_time_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "select_voice")
async def select_voice_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await select_voice_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "select_role")
async def select_role_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await select_role_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_voice_selection, lambda c: c.data and c.data.startswith("voice_"))
async def process_voice_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_voice_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_role_selection, lambda c: c.data and c.data.startswith("role_"))
async def process_role_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await role_selection_handler(callback_query, state)

@dp.message(F.text == "🗑️ Очистить")
@dp.message(F.text == "/clear")
async def cmd_clear_context(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    api_type = user_context["api_type"]
    
    system_role = user_context.get("system_role", "default")
    system_prompt = DEFAULT_SYSTEM_PROMPTS.get(system_role, DEFAULT_SYSTEM_PROMPTS["default"])
    
    new_context = {
        "model": user_context["model"],
        "api_type": api_type,
        "g4f_image": None,
        "g4f_image_base64": None,
        "long_message": "",
        "image_generation_model": user_context.get("image_generation_model", await def_gen_model()),
        "image_recognition_model": user_context.get("image_recognition_model", await def_rec_model()),
        "aspect_ratio": user_context.get("aspect_ratio", await def_aspect()),
        "enhance": user_context.get("enhance", await def_enhance()),
        "show_processing_time": user_context.get("show_processing_time", True),
        "voice": user_context.get("voice", await def_voice()),
        "system_role": system_role,
        "messages": []
    }
    
    if api_type == "gemini":
        new_context["messages"] = [{"role": "system", "parts": [{"text": system_prompt}]}]
    else:
        new_context["messages"] = [{"role": "system", "content": system_prompt}]

    await save_context(user_id, new_context)
    await message.reply("Контекст очищен.")


@dp.message(F.text == "🎨 Сгенерировать")
@dp.message(F.text == "/generate_image")
async def cmd_generate_image(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await message.reply("🔔Пожалуйста, введите запрос для генерации изображения:")
    await state.update_data(is_direct_image_gen=True)
    await state.set_state(Form.waiting_for_image_generation_prompt)

@dp.message(Form.waiting_for_image_generation_prompt, F.photo)
async def process_image_edit_prompt_handler(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    image_data = await bot.download_file(file_path)
    
    data = await state.get_data()
    existing_images = data.get("image_edit_data", [])
    if not isinstance(existing_images, list):
        existing_images = [existing_images] if existing_images else []
    existing_images.append(image_data)
    await state.update_data(image_edit_data=existing_images)
    
    await message.reply("🖌️ Фото добавлено для редактирования. Пришлите инструкцию или добавьте еще фото:")
    await state.set_state(Form.waiting_for_image_edit_instructions)

@dp.message(Form.waiting_for_image_generation_prompt)
async def process_image_generation_prompt_handler(message: types.Message, state: FSMContext):
    await state.update_data(image_generation_prompt=message.text)
    await state.set_state(Form.waiting_for_message)
    await process_image_generation_prompt(message, state)


@dp.message(F.text == "🎤 Аудио")
@dp.message(F.text == "/audio")
async def cmd_audio(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    current_state = await state.get_state()

    if current_state == Form.waiting_for_audio:
        await state.set_state(Form.waiting_for_message)
        await message.reply("🔔Режим ожидания аудио отключен.")
        return
    else:
        await message.reply("🔔Пожалуйста, отправьте аудиофайл для транскрипции.")
        await state.set_state(Form.waiting_for_audio)

@dp.message(Form.waiting_for_audio, lambda message: message.audio or message.voice or message.document and message.document.mime_type.startswith('audio/') or message.video_note)
async def handle_audio_handler(message: types.Message, state: FSMContext):
    WHISPER_MODELS = await whisp_models()
    await handle_audio(message, state, WHISPER_MODELS)

@dp.callback_query(Form.waiting_for_whisper_model_selection, lambda c: c.data and c.data.startswith("whisper_model_"))
async def process_whisper_model_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_whisper_model_selection(callback_query, state)    

@dp.message(F.text == "🌐 Поиск")
@dp.message(F.text == "/search")
async def cmd_search(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply("Извините, у вас нет доступа к этому боту.")
        return
    
    await message.reply("🔔Пожалуйста, введите запрос для поиска в интернете:")
    await state.set_state(Form.waiting_for_search_query)

@dp.message(Form.waiting_for_search_query)
async def process_search_query_handler(message: types.Message, state: FSMContext):
    await process_search_query(message, state)


@dp.message(F.text == "📝 Длинное сообщение")
@dp.message(F.text == "/long_message")
async def cmd_long_message_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await cmd_long_message(message, state)

@dp.message(F.text == "⌨️ Вернуть клавиатуру")
@dp.message(F.text == "/keyboard")
async def cmd_restore_keyboard(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    
    if is_admin(user_id):
        await message.reply(
            "🔔 Клавиатура восстановлена.",
            reply_markup=await get_main_keyboard(include_admin_button=True)
        )
    else:
        await message.reply(
            "🔔 Клавиатура восстановлена.",
            reply_markup=await get_main_keyboard(include_admin_button=False)
        )
    
    await state.set_state(Form.waiting_for_message)

@dp.message(Form.waiting_for_long_message)
async def handle_long_message_handler(message: types.Message, state: FSMContext):
    await handle_long_message(message, state)

@dp.message()
async def handle_all_messages_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_allowed(user_id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    current_state = await state.get_state() or Form.waiting_for_message
    if await state.get_state() is None:
        await state.set_state(Form.waiting_for_message)

    model_key = user_context["model"]
    model_id, api_type = model_key.split('_')
    
    if message.voice or message.audio:
        if api_type == "poli" and model_id == "openai-audio":
            await handle_all_messages(message, state, audio_response=True)
            return
    if message.text and api_type == "poli" and model_id == "openai-audio":
        await handle_all_messages(message, state, audio_response=True)
        return
        
    image_rec_models = await rec_models()
    allowed_apis = list(openai_clients.keys()) + ["g4f"]
    if message.document:
        if api_type in allowed_apis:
            await handle_files_or_urls(message, state)
        elif api_type == "gemini":
            await handle_document_with_conversion(message, state)
        else:
            await message.reply("🔔Обработка файлов не поддерживается данной моделью.")
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
            else:
                await message.reply("🔔Распознавание изображений настроено, но обработчик не найден.")
        else:
            await message.reply("🔔Распознавание изображений не поддерживается этой моделью.")
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
    else:
        await handle_all_messages(message, state)



async def shutdown():
    try:
        await db_pool.close_all()
        print("Database connections closed successfully")
    except Exception as e:
        print(f"Error closing database connections: {e}")

async def main():
    try:
        await initialize_database()
        await initialize_models()
        await clear_all_user_contexts()
        await init_all_user_clients()
        await init_enhance_prompt_client()
        
        cookies_dir = os.path.join(os.path.dirname(__file__), "har_and_cookies")
        set_cookies_dir(cookies_dir)
        read_cookie_files(cookies_dir)
        print("Бот запущен и клиенты для всех пользователей инициализированы.")
        
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        print(f"Error during bot execution: {e}")
    finally:
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")