from dotenv import load_dotenv 

load_dotenv()

from config import Form, bot, dp, init_enhance_prompt_client
from database import load_context,save_context, is_admin,is_allowed, initialize_database, clear_all_user_contexts, initialize_models, rec_models, whisp_models, def_rec_model, def_gen_model, def_aspect, db_pool, def_enhance, init_all_user_clients

from keyboards import get_admin_keyboard,get_glhf_keyboard,get_glhf_keyboard_with_admin_button,get_g4f_keyboard,get_g4f_keyboard_with_admin_button,get_gemini_keyboard,get_gemini_keyboard_with_admin_button

from func.gemini import handle_pdf, process_custom_image_prompt, handle_image
from func.g4f import process_image_generation_prompt, handle_image_recognition, handle_files_or_urls

from func.audio import handle_audio, process_whisper_model_selection
from func.search import process_search_query
from func.messages import handle_all_messages,cmd_long_message,handle_long_message
from func.admin import cmd_add_user, cmd_add_model,cmd_add_image_gen_model,cmd_add_image_rec_model,cmd_delete_image_gen_model,cmd_delete_model,cmd_delete_image_rec_model,cmd_remove_user,process_add_user_id,process_remove_user_id,process_new_model_name,process_new_model_id,process_new_model_api,process_confirm_delete,process_delete_model_name,process_add_image_rec_model_name,process_delete_image_rec_model_name,process_confirm_delete_image_rec_model,process_add_image_gen_model_name,process_delete_image_gen_model_name,process_confirm_delete_image_gen_model, cmd_send_to_all, cmd_send_to_user, process_message_to_all, process_user_id_to_send, process_message_to_user


from settings import cmd_settings, select_model_handler, select_image_gen_model_handler, select_image_rec_model_handler, select_aspect_ratio_handler, process_enhance_selection_handler, close_settings_handler, model_selection_handler, process_image_generation_model_handler, process_image_recognition_model_selection_handler, process_aspect_ratio_selection_handler, toggle_web_search_handler, toggle_processing_time_handler

from func.openai_image import process_custom_image_prompt_openai, handle_image_openai

from aiogram.enums import ParseMode
import logging
import asyncio
from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
logging.basicConfig(level=logging.INFO)



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

@dp.message(Form.waiting_for_add_image_rec_model_name)
async def process_add_image_rec_model_name_handler(message: types.Message, state: FSMContext):
    await process_add_image_rec_model_name(message, state)

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

@dp.message(Form.waiting_for_add_image_gen_model_name)
async def process_add_image_gen_model_name_handler(message: types.Message, state: FSMContext):
    await process_add_image_gen_model_name(message, state)

@dp.callback_query(Form.waiting_for_delete_image_gen_model_name)
async def process_delete_image_gen_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_image_gen_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_gen_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_gen_"))
async def process_confirm_delete_image_gen_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete_image_gen_model(callback_query, state)


otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    api_type = user_context["api_type"]
    
    await save_context(user_id, user_context)

    if api_type== "g4f":
        if is_admin(user_id):
            await message.reply(
                "Привет, админ! Я чат-бот, который может использовать различные ИИ-модели.\n"
                "Используйте /help, чтобы увидеть доступные команды.",
                reply_markup= await get_g4f_keyboard_with_admin_button()
            )
        else:
            await message.reply(
                "Привет! Я чат-бот, который может использовать различные ИИ-модели.\n"
                "Используйте /help, чтобы увидеть доступные команды.",
                reply_markup=await get_g4f_keyboard()
            )
    elif api_type == "gemini":
        if is_admin(user_id):
            await message.reply(
                "Привет, админ! Я чат-бот, который может использовать различные ИИ-модели.\n"
                "Используйте /help, чтобы увидеть доступные команды.",
                reply_markup=await get_gemini_keyboard_with_admin_button()
            )
        else:
            await message.reply(
                "Привет! Я чат-бот, который может использовать различные ИИ-модели.\n"
                "Используйте /help, чтобы увидеть доступные команды.",
                reply_markup=await get_gemini_keyboard()
            )
    else: 
        if is_admin(user_id):
            await message.reply(
                "Привет, админ! Я чат-бот, который может использовать различные ИИ-модели.\n"
                "Используйте /help, чтобы увидеть доступные команды.",
                reply_markup=await get_glhf_keyboard_with_admin_button()
            )
        else:
            await message.reply(
                "Привет! Я чат-бот, который может использовать различные ИИ-модели.\n"
                "Используйте /help, чтобы увидеть доступные команды.",
                reply_markup=await get_glhf_keyboard()
            )

    await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "Открыть админ-клавиатуру", lambda message: is_admin(message.from_user.id))
async def cmd_open_admin_keyboard(message: types.Message, state: FSMContext):
    await message.reply("🔔Вы открыли админ-клавиатуру.", reply_markup= await get_admin_keyboard())

@dp.message(F.text == "Главное меню", lambda message: is_admin(message.from_user.id))
async def cmd_back_to_main_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)
    api_type = user_context["api_type"]

    if api_type == "g4f":
        reply_markup = await get_g4f_keyboard_with_admin_button()
    elif api_type == "gemini":
        reply_markup = await get_gemini_keyboard_with_admin_button()
    else: 
        reply_markup = await get_glhf_keyboard_with_admin_button()

    await message.reply("🔔Вы вернулись в главное меню.", reply_markup=reply_markup)
    await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "ℹ️ Помощь")
@dp.message(F.text == "/help")
async def cmd_help(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await message.reply(
        "Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать это справочное сообщение\n"
        "/settings - Открыть меню настроек\n"
        "/clear - Очистить контекст беседы\n"
        "/generate_image - Сгенерировать изображение\n"
        "/audio - Отправить аудио для транскрипции (Whisper)\n"
        "/search - Выполнить поиск в интернете\n"
        "/long_message - Режим накопления сообщений\n"
        "Также можно присылать pdf и изображения\n"
    )

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

@dp.callback_query(Form.waiting_for_image_generation_model, lambda c: c.data and c.data.startswith('gen_model_'))
async def process_image_generation_model_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_image_generation_model_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_image_recognition_model, lambda c: c.data and c.data.startswith('rec_model_'))
async def process_image_recognition_model_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_image_recognition_model_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_aspect_ratio, lambda c: c.data and c.data.startswith("aspect_ratio_"))
async def process_aspect_ratio_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await process_aspect_ratio_selection_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "toggle_web_search")
async def toggle_web_search_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await toggle_web_search_handler(callback_query, state)

@dp.callback_query(Form.waiting_for_settings_selection, lambda c: c.data == "toggle_processing_time")
async def toggle_processing_time_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await toggle_processing_time_handler(callback_query, state)


@dp.message(F.text == "🗑️ Очистить")
@dp.message(F.text == "/clear")
async def cmd_clear_context(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return

    user_id = message.from_user.id

    user_context = await load_context(user_id)

    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_IMAGE_RECOGNITION_MODEL = await def_rec_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()

    model_key = user_context["model"] 
    current_api_type = user_context["api_type"]
    current_image_gen_model = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    current_image_rec_model = user_context.get("image_recognition_model", DEFAULT_IMAGE_RECOGNITION_MODEL)
    current_aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    current_enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    current_web_search = user_context.get("web_search_enabled", False)

    if current_api_type == "gemini":
        user_context["messages"] = []
    elif current_api_type == "g4f":
        user_context["messages"] = [{"role": "system", "content": "###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE."}]
    else:
        user_context["messages"] = [{"role": "system", "content": "###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE."}]


    user_context.update({
        "model": model_key,
        "api_type": current_api_type,
        "g4f_image": None,
        "g4f_image_base64": None,
        "long_message": "",
        "image_generation_model": current_image_gen_model,
        "image_recognition_model": current_image_rec_model,
        "aspect_ratio": current_aspect_ratio,
        "enhance": current_enhance,
        "web_search_enabled": current_web_search
    })

    await save_context(user_id, user_context)
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

@dp.message(Form.waiting_for_image_generation_prompt)
async def process_image_generation_prompt_handler(message: types.Message, state: FSMContext):
    await state.update_data(image_generation_prompt=message.text)
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
        # Already in waiting mode, exit 
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
    
    await cmd_long_message(message, state, is_allowed)

@dp.message(Form.waiting_for_long_message)
async def handle_long_message_handler(message: types.Message, state: FSMContext):
    await handle_long_message(message, state)


@dp.message()
async def handle_all_messages_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    user_context = await load_context(user_id) 
    current_state = await state.get_state()
    model_key = user_context["model"]  
    model_id, api_type = model_key.split('_')


    IMAGE_RECOGNITION_MODELS = await rec_models()

    if current_state is None:
        await state.set_state(Form.waiting_for_message)

    if message.document:
        if api_type in ["g4f", "glhf"]:
            await handle_files_or_urls(message, state)
        elif api_type == "gemini" and message.document.mime_type == "application/pdf":
            await handle_pdf(message, state)
        elif api_type == "gemini":
            await message.reply("🔔Модель Gemini поддерживает только PDF. Пожалуйста, смените модель или отправьте PDF файл.")
        else:
            await message.reply("🔔Обработка файлов не поддерживается данной моделью.")

    elif message.photo:
        if api_type == "g4f" and model_id in IMAGE_RECOGNITION_MODELS:
            await state.set_state(Form.waiting_for_custom_image_recognition_prompt)
            await handle_image_recognition(message, state)
        elif api_type == "gemini":
            if current_state == Form.waiting_for_image_and_prompt:
                await message.reply("🔔Пожалуйста, сначала введите текстовый промпт.")
            else:
                await state.set_state(Form.waiting_for_image_and_prompt)
                await handle_image(message, state)
        elif api_type == "glhf" and model_id in ["openai", "openai-large"]: 
            if current_state == Form.waiting_for_image_and_prompt_openai:
                await message.reply("🔔Пожалуйста, сначала введите текстовый промпт.")
            else:
                await state.set_state(Form.waiting_for_image_and_prompt_openai)
                await handle_image_openai(message, state)
        else:
            await message.reply("🔔Распознавание изображений не поддерживается этой моделью.")


    elif current_state == Form.waiting_for_message:
        await handle_all_messages(message, state, is_admin, is_allowed)

    elif current_state == Form.waiting_for_image_and_prompt:
        if message.text:
            if api_type == "gemini":
              await process_custom_image_prompt(message, state)
            else:
              await message.reply("🔔Пожалуйста, введите текстовый промпт к изображению.")

    elif current_state == Form.waiting_for_image_and_prompt_openai:
      if message.text:
          if api_type == "glhf" and model_id in ["openai", "openai-large"]: 
            await process_custom_image_prompt_openai(message, state)
          else:
              await message.reply("🔔Пожалуйста, введите текстовый промпт к изображению.")
      else:
          await message.reply("🔔Пожалуйста, введите текстовый промпт к изображению.")

    else:
        await handle_all_messages(message, state, is_admin, is_allowed)

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
        
        print("Бот запущен и клиенты для всех пользователей инициализированы.")

        while True:
          try:
              await dp.start_polling(bot, timeout=60, skip_updates=True)
          except Exception as e:
              print(f"Ошибка polling-а: {e}")
              await asyncio.sleep(3)  # Небольшая пауза перед повторной попыткой
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