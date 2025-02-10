from aiogram.fsm.context import FSMContext
from config import Form, bot
import logging
from database import is_admin,gen_models, av_models, rec_models,init_av_models, init_gen_models,init_rec_models,initialize_allowed_users,DATABASE_FILE, get_all_allowed_users
from keyboards import get_image_gen_model_selection_keyboard,get_image_recognition_model_selection_keyboard, get_model_selection_keyboard
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite

async def cmd_add_user(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите ID пользователя, которого нужно добавить:")
    await state.set_state(Form.waiting_for_add_user_id)

async def process_add_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        async with aiosqlite.connect(DATABASE_FILE) as db:
            async with db.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,)) as cursor:
                if await cursor.fetchone() is None:
                    await db.execute("INSERT INTO allowed_users (user_id) VALUES (?)", (user_id,))
                    await db.commit()
                    await message.reply(f"Пользователь с ID {user_id} успешно добавлен.")
                else:
                    await message.reply(f"Пользователь с ID {user_id} уже добавлен.")
        await initialize_allowed_users()
    except ValueError:
        await message.reply("Неверный формат ID пользователя. Пожалуйста, введите число.")
    finally:
        await state.set_state(Form.waiting_for_message)

async def cmd_remove_user(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите ID пользователя, которого нужно удалить:")
    await state.set_state(Form.waiting_for_remove_user_id)

async def process_remove_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        async with aiosqlite.connect(DATABASE_FILE) as db:
            async with db.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,)) as cursor:
                if await cursor.fetchone() is not None:
                    await db.execute("DELETE FROM allowed_users WHERE user_id = ?", (user_id,))
                    await db.commit()
                    await message.reply(f"Пользователь с ID {user_id} успешно удален.")
                else:
                    await message.reply(f"Пользователя с ID {user_id} нет в списке разрешенных.")
        await initialize_allowed_users()
    except ValueError:
        await message.reply("Неверный формат ID пользователя. Пожалуйста, введите число.")
    finally:
        await state.set_state(Form.waiting_for_message)


async def cmd_add_model(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите имя новой модели для чата:")
    await state.set_state(Form.waiting_for_new_model_name)

async def process_new_model_name(message: types.Message, state: FSMContext):
    model_name = message.text
    await state.update_data(new_model_name=model_name)
    await message.reply("Введите ID новой модели для чата:")
    await state.set_state(Form.waiting_for_new_model_id)

async def process_new_model_id(message: types.Message, state: FSMContext):
    model_id = message.text
    await state.update_data(new_model_id=model_id)
    await message.reply("Введите тип API новой модели для чата (glhf, gemini или g4f):")
    await state.set_state(Form.waiting_for_new_model_api)

async def process_new_model_api(message: types.Message, state: FSMContext):
    model_api = message.text.lower()  # Приводим к нижнему регистру для унификации
    if model_api not in ["glhf", "gemini", "g4f"]:
        await message.reply("Неверный тип API. Пожалуйста, используйте команду /add_model снова и введите 'glhf', 'gemini' или 'g4f'.")
        await state.set_state(Form.waiting_for_message)
        return

    data = await state.get_data()
    model_name = data.get("new_model_name")
    model_id = data.get("new_model_id")

    async with aiosqlite.connect(DATABASE_FILE) as db:
        async with db.execute("SELECT 1 FROM models WHERE model_id = ? AND api = ?", (model_id, model_api)) as cursor:
            if await cursor.fetchone() is not None:
                await message.reply(f"Модель с ID {model_id} и API {model_api} уже существует. Пожалуйста, используйте команду /add_model снова с другими параметрами.")
                await state.set_state(Form.waiting_for_message)
                return

        await db.execute("INSERT INTO models (model_id, model_name, api) VALUES (?, ?, ?)", 
                        (model_id, model_name, model_api))
        await db.commit()

    await init_av_models()
    await message.reply(f"Модель {model_name} успешно добавлена для чата!")
    await state.set_state(Form.waiting_for_message)


async def cmd_delete_model(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    AVAILABLE_MODELS = await av_models()
    keyboard = await get_model_selection_keyboard(AVAILABLE_MODELS)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")])

    msg = await message.reply("Выберите модель для удаления:", reply_markup=keyboard)
    await state.update_data(delete_model_message_id=msg.message_id) 
    await state.set_state(Form.waiting_for_delete_model_name)


async def process_delete_model_name(callback_query: types.CallbackQuery, state: FSMContext):
    model_data = callback_query.data.split('_', 1)[1] if callback_query.data.startswith('model_') else callback_query.data

    data = await state.get_data()
    delete_model_message_id = data.get("delete_model_message_id")
    if delete_model_message_id:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=delete_model_message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")

    if model_data == "cancel_delete":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Удаление модели отменено.")
        await state.set_state(Form.waiting_for_message)
        return

    AVAILABLE_MODELS = await av_models()
    if model_data not in AVAILABLE_MODELS:
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Модель не найдена.")
        await state.set_state(Form.waiting_for_message)
        return

    model_id = model_data.split('_')[0]
    api_type = AVAILABLE_MODELS[model_data]['api']
    
    await state.update_data(
        delete_model_name=AVAILABLE_MODELS[model_data]['model_name'],
        delete_model_id=model_id,
        delete_model_api=api_type
    )

    await bot.send_message(
        callback_query.from_user.id,
        f"Вы уверены, что хотите удалить модель '{AVAILABLE_MODELS[model_data]['model_name']}'? (да/нет)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="confirm_delete_yes"),
             InlineKeyboardButton(text="Нет", callback_data="confirm_delete_no")]
        ])
    )
    await state.set_state(Form.waiting_for_confirmation)

async def process_confirm_delete(callback_query: types.CallbackQuery, state: FSMContext):
    confirmation = callback_query.data.split('_', 2)[2]
    data = await state.get_data()
    model_name = data.get("delete_model_name")
    model_id = data.get("delete_model_id")
    model_api = data.get("delete_model_api")

    await bot.answer_callback_query(callback_query.id)

    if confirmation == "yes":
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute("DELETE FROM models WHERE model_id = ? AND api = ?", 
                           (model_id, model_api))
            await db.commit()

        await init_av_models()
        await bot.send_message(callback_query.from_user.id, 
                             f"Модель '{model_name}' успешно удалена для чата!")
    else:
        await bot.send_message(callback_query.from_user.id, 
                             "Удаление модели для чата отменено.")

    await state.set_state(Form.waiting_for_message)

async def cmd_add_image_rec_model(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите имя новой модели для распознавания изображений:")
    await state.set_state(Form.waiting_for_add_image_rec_model_name)

async def process_add_image_rec_model_name(message: types.Message, state: FSMContext):
    model_name = message.text

    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("INSERT INTO image_recognition_models (name) VALUES (?)", (model_name,))
        await db.commit()

    await init_rec_models()

    await message.reply(f"Модель {model_name} успешно добавлена для распознавания изображений!")
    await state.set_state(Form.waiting_for_message)

async def cmd_delete_image_rec_model(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    IMAGE_RECOGNITION_MODELS = await rec_models()
    keyboard = await get_image_recognition_model_selection_keyboard(IMAGE_RECOGNITION_MODELS)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_delete_image_rec")])

    msg = await message.reply("Выберите модель для удаления:", reply_markup=keyboard)
    await state.update_data(delete_image_rec_model_message_id=msg.message_id)  
    await state.set_state(Form.waiting_for_delete_image_rec_model_name)

async def process_delete_image_rec_model_name(callback_query: types.CallbackQuery, state: FSMContext):
    model_name = callback_query.data.split('_', 2)[2] if callback_query.data.startswith('rec_model_') else callback_query.data
    
    data = await state.get_data()
    delete_image_rec_model_message_id = data.get("delete_image_rec_model_message_id")
    if delete_image_rec_model_message_id:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=delete_image_rec_model_message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения выбора модели для удаления: {e}")

    if model_name == "cancel_delete_image_rec":
        await bot.send_message(callback_query.from_user.id, "Удаление модели распознавания изображений отменено.")
        await state.set_state(Form.waiting_for_message)
        return

    IMAGE_RECOGNITION_MODELS = await rec_models()
    if model_name not in IMAGE_RECOGNITION_MODELS:
        await bot.send_message(callback_query.from_user.id, "Модель не найдена.")
        await state.set_state(Form.waiting_for_message)
        return

    await state.update_data(delete_image_rec_model_name=model_name)
    await bot.send_message(callback_query.from_user.id,
                         f"Вы уверены, что хотите удалить модель '{model_name}' для распознавания изображений? (да/нет)",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Да", callback_data="confirm_delete_image_rec_yes"),
                              InlineKeyboardButton(text="Нет", callback_data="confirm_delete_image_rec_no")]
                         ]))
    await state.set_state(Form.waiting_for_confirmation_image_rec_model_delete)


async def process_confirm_delete_image_rec_model(
    callback_query: types.CallbackQuery, state: FSMContext
):
    confirmation = callback_query.data.split("_", 4)[4]
    data = await state.get_data()
    model_name = data.get("delete_image_rec_model_name")

    await bot.answer_callback_query(callback_query.id)

    if confirmation == "yes":
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute("DELETE FROM image_recognition_models WHERE name = ?", (model_name,))
            await db.commit()

        await init_rec_models()

        await bot.send_message(
            callback_query.from_user.id,
            f"Модель '{model_name}' успешно удалена для распознавания изображений!",
        )
    else:
        await bot.send_message(
            callback_query.from_user.id,
            "Удаление модели для распознавания изображений отменено.",
        )

    await state.set_state(Form.waiting_for_message)


async def cmd_add_image_gen_model(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите имя новой модели для генерации изображений:")
    await state.set_state(Form.waiting_for_add_image_gen_model_name)

async def process_add_image_gen_model_name(message: types.Message, state: FSMContext):
    model_name = message.text

    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("INSERT INTO image_generation_models (name) VALUES (?)", (model_name,))
        await db.commit()

    await init_gen_models()

    await message.reply(f"Модель {model_name} успешно добавлена для генерации изображений!")
    await state.set_state(Form.waiting_for_message)

async def cmd_delete_image_gen_model(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    IMAGE_GENERATION_MODELS = await gen_models()
    keyboard = await get_image_gen_model_selection_keyboard(IMAGE_GENERATION_MODELS)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_delete_image_gen")])

    msg = await message.reply("Выберите модель для удаления:", reply_markup=keyboard)
    await state.update_data(delete_image_gen_model_message_id=msg.message_id) 
    await state.set_state(Form.waiting_for_delete_image_gen_model_name)

async def process_delete_image_gen_model_name(callback_query: types.CallbackQuery, state: FSMContext):
    model_name = callback_query.data.split('_', 2)[2] if callback_query.data.startswith('gen_model_') else callback_query.data

    data = await state.get_data()
    delete_image_gen_model_message_id = data.get("delete_image_gen_model_message_id")
    if delete_image_gen_model_message_id:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=delete_image_gen_model_message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения выбора модели для удаления: {e}")

    if model_name == "cancel_delete_image_gen":
        await bot.send_message(callback_query.from_user.id, "Удаление модели для генерации изображений отменено.")
        await state.set_state(Form.waiting_for_message)
        return

    IMAGE_GENERATION_MODELS = await gen_models()
    if model_name not in IMAGE_GENERATION_MODELS:
        await bot.send_message(callback_query.from_user.id, "Модель не найдена.")
        await state.set_state(Form.waiting_for_message)
        return

    await state.update_data(delete_image_gen_model_name=model_name)
    await bot.send_message(callback_query.from_user.id,
                         f"Вы уверены, что хотите удалить модель '{model_name}' для генерации изображений? (да/нет)",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Да", callback_data="confirm_delete_image_gen_yes"),  # Исправлено здесь
                              InlineKeyboardButton(text="Нет", callback_data="confirm_delete_image_gen_no")]  # Исправлено здесь
                         ]))
    await state.set_state(Form.waiting_for_confirmation_image_gen_model_delete)

async def process_confirm_delete_image_gen_model(
    callback_query: types.CallbackQuery, state: FSMContext
):
    confirmation = callback_query.data.split("_", 4)[4]
    data = await state.get_data()
    model_name = data.get("delete_image_gen_model_name")

    await bot.answer_callback_query(callback_query.id)

    if confirmation == "yes":
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute("DELETE FROM image_generation_models WHERE name = ?", (model_name,))
            await db.commit()

        await init_gen_models()

        await bot.send_message(
            callback_query.from_user.id,
            f"Модель '{model_name}' успешно удалена для генерации изображений!",
        )
    else:
        await bot.send_message(
            callback_query.from_user.id,
            "Удаление модели для генерации изображений отменено.",
        )

    await state.set_state(Form.waiting_for_message) 

async def cmd_send_to_all(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите сообщение, которое нужно отправить всем пользователям:")
    await state.set_state(Form.waiting_for_message_to_all)

async def process_message_to_all(message: types.Message, state: FSMContext):
    user_ids = await get_all_allowed_users()

    for user_id in user_ids:
        try:
            if message.text:
                await bot.send_message(user_id, message.text)
            elif message.photo:
                await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.audio:
                await bot.send_audio(user_id, message.audio.file_id, caption=message.caption)
            elif message.voice:
                await bot.send_voice(user_id, message.voice.file_id)
            elif message.document:
                await bot.send_document(user_id, message.document.file_id, caption=message.caption)
            elif message.sticker:
                await bot.send_sticker(user_id, message.sticker.file_id)
            elif message.video_note:
                await bot.send_video_note(user_id, message.video_note.file_id)
            elif message.animation:
                await bot.send_animation(user_id, message.animation.file_id, caption=message.caption)

        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

    await message.reply("Сообщение отправлено всем пользователям.")
    await state.set_state(Form.waiting_for_message)

async def cmd_send_to_user(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return

    await message.reply("Введите ID пользователя, которому нужно отправить сообщение:")
    await state.set_state(Form.waiting_for_user_id_to_send)

async def process_user_id_to_send(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(user_id_to_send=user_id)
        await message.reply("Введите сообщение для пользователя:")
        await state.set_state(Form.waiting_for_message_to_user)
    except ValueError:
        await message.reply("Неверный формат ID пользователя. Пожалуйста, введите число.")
        await state.set_state(Form.waiting_for_message)

async def process_message_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id_to_send")

    try:
        if message.text:
            await bot.send_message(user_id, message.text)
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption=message.caption)
        elif message.audio:
            await bot.send_audio(user_id, message.audio.file_id, caption=message.caption)
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id)
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption)
        elif message.sticker:
            await bot.send_sticker(user_id, message.sticker.file_id)
        elif message.video_note:
            await bot.send_video_note(user_id, message.video_note.file_id)
        elif message.animation:
            await bot.send_animation(user_id, message.animation.file_id, caption=message.caption)

        await message.reply(f"Сообщение отправлено пользователю с ID {user_id}.")
    except Exception as e:
        await message.reply(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")

    await state.set_state(Form.waiting_for_message)