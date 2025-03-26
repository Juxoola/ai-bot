from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp, DEFAULT_SYSTEM_PROMPTS
from database import load_context, save_context, is_admin, is_allowed, av_models, rec_models, def_gen_model, def_rec_model, def_aspect, def_enhance, def_voice
from keyboards import get_admin_keyboard, get_main_keyboard

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN,
                          reply_markup=await get_main_keyboard(include_admin_button=False))
        return

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    
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
        "/meme - Получить случайный мем\n"
        "/games - Открыть меню игр\n"
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


@dp.message(F.text == "⌨️ Вернуть клавиатуру")
@dp.message(F.text == "/keyboard")
async def cmd_restore_keyboard(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    if is_admin(user_id):
        await message.reply(
            "Клавиатура восстановлена. Используйте кнопки для взаимодействия с ботом.",
            reply_markup=await get_main_keyboard(include_admin_button=True)
        )
    else:
        await message.reply(
            "Клавиатура восстановлена. Используйте кнопки для взаимодействия с ботом.",
            reply_markup=await get_main_keyboard(include_admin_button=False)
        )


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