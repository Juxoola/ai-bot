from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

async def get_admin_keyboard():
    keyboard = [
        [
            KeyboardButton(text="/add_model"),
            KeyboardButton(text="/delete_model")
        ],
        [
            KeyboardButton(text="/add_image_gen_model"),
            KeyboardButton(text="/delete_image_gen_model")
        ],
        [
            KeyboardButton(text="/add_image_rec_model"),
            KeyboardButton(text="/delete_image_rec_model")
        ],
        [
            KeyboardButton(text="/add_user"),
            KeyboardButton(text="/remove_user")
        ],
        [
            KeyboardButton(text="/send_to_all"),
            KeyboardButton(text="/send_to_user")
        ],
        [
            KeyboardButton(text="Главное меню")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

async def get_main_keyboard(include_admin_button=False):
    keyboard = [
        [
            KeyboardButton(text="⚙️ Настройки"),
            KeyboardButton(text="🗑️ Очистить")
        ],
        [
            KeyboardButton(text="🎨 Сгенерировать"),
            KeyboardButton(text="🌐 Поиск")
        ],
        [
            KeyboardButton(text="🎤 Аудио"),
            KeyboardButton(text="📝 Длинное сообщение")
        ],
        [
            KeyboardButton(text="ℹ️ Помощь")
        ]
    ]
    
    if include_admin_button:
        keyboard.append([KeyboardButton(text="Открыть админ-клавиатуру")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

async def get_model_selection_keyboard(available_models):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    priority_api_order = ["gemini", "g4f", "glhf", "openrouter" ]
    
    grouped_models = {}
    for model_id, model_data in available_models.items():
        api_type = model_data["api"]
        if api_type not in grouped_models:
            grouped_models[api_type] = []
        grouped_models[api_type].append((model_id, model_data["model_name"]))

    for api_type in priority_api_order:
        if api_type in grouped_models:
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=f"----- {api_type.upper()} -----", callback_data="ignore")]
            )

            buttons_row = []
            for model_id, model_name in grouped_models[api_type]:
                button = InlineKeyboardButton(text=model_name, callback_data=f"model_{model_id}")
                buttons_row.append(button)

                if len(buttons_row) == 2:
                    keyboard.inline_keyboard.append(buttons_row)
                    buttons_row = []

            if buttons_row:
                keyboard.inline_keyboard.append(buttons_row)
            
            del grouped_models[api_type]

    for api_type in sorted(grouped_models.keys()):
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"----- {api_type.upper()} -----", callback_data="ignore")]
        )

        buttons_row = []
        for model_id, model_name in grouped_models[api_type]:
            button = InlineKeyboardButton(text=model_name, callback_data=f"model_{model_id}")
            buttons_row.append(button)

            if len(buttons_row) == 2:
                keyboard.inline_keyboard.append(buttons_row)
                buttons_row = []

        if buttons_row:
            keyboard.inline_keyboard.append(buttons_row)

    return keyboard

async def get_image_gen_model_selection_keyboard(IMAGE_GENERATION_MODELS):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=f"----- Модели для генерации изображений -----", callback_data="ignore")]
    )
    buttons_row = []
    for model_name in IMAGE_GENERATION_MODELS:
        button = InlineKeyboardButton(text=model_name, callback_data=f"gen_model_{model_name}")
        buttons_row.append(button)
        if len(buttons_row) == 2:
            keyboard.inline_keyboard.append(buttons_row)
            buttons_row = []
    if buttons_row:
        keyboard.inline_keyboard.append(buttons_row)
    return keyboard

async def get_image_recognition_model_selection_keyboard(IMAGE_RECOGNITION_MODELS):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=f"----- Модели для распознавания изображений -----", callback_data="ignore")]
    )
    buttons_row = []
    for model_name in IMAGE_RECOGNITION_MODELS:
        callback_data = f"rec_model_{model_name}" 
        if len(callback_data.encode('utf-8')) > 64:
            raise ValueError(f"Callback data too long: {callback_data}")
        
        button = InlineKeyboardButton(text=model_name, callback_data=callback_data)
        buttons_row.append(button)
        if len(buttons_row) == 2:
            keyboard.inline_keyboard.append(buttons_row)
            buttons_row = []
    if buttons_row:
        keyboard.inline_keyboard.append(buttons_row)
    return keyboard


async def get_settings_keyboard(
    current_model,
    current_image_gen_model,
    current_aspect_ratio,
    current_enhance,
    web_search_enabled,
    show_processing_time,
):
    buttons = [
        [InlineKeyboardButton(text=f"💬 Модель: {current_model}", callback_data="select_model")],
        [InlineKeyboardButton(text=f"🎨 Модель генерации: {current_image_gen_model}", callback_data="select_image_gen_model")],
        [InlineKeyboardButton(text=f"📐 Соотношение сторон: {current_aspect_ratio}", callback_data="select_aspect_ratio")],
        [InlineKeyboardButton(text=f"✨ Enhance: {'включено' if current_enhance else 'выключено'}", callback_data="toggle_enhance")],
        [InlineKeyboardButton(
            text=f"🔍 Веб-поиск: {'включен' if web_search_enabled else 'выключен'}",
            callback_data="toggle_web_search"
        )],
        [InlineKeyboardButton(text=f"⏱️ Время обработки: {'включено' if show_processing_time else 'выключено'}", callback_data="toggle_processing_time")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_aspect_ratio_selection_keyboard():
    aspect_ratio_options = {
        "1:1": (2048, 2048),
        "3:2": (1536, 1024),
        "2:3": (1024, 1536),
        "4:3": (1536, 1152),
        "3:4": (1152, 1536),
        "16:9": (1792, 1024),
        "9:16": (1024, 1792),
        "21:9": (2048, 896),
        "9:21": (896, 2048),
    }
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for ratio, dimensions in aspect_ratio_options.items():
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{ratio} ({dimensions[0]}x{dimensions[1]})",
                    callback_data=f"aspect_ratio_{ratio}",
                )
            ]
        )
    return keyboard





