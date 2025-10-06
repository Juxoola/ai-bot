from config import bot,Form,groq_client
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
import asyncio
import logging
import os
import aiofiles.tempfile
import aiofiles.os

async def handle_audio(message: types.Message, state: FSMContext,WHISPER_MODELS):

    if message.audio:
        file_size = message.audio.file_size
        file_id = message.audio.file_id
    elif message.voice:
        file_size = message.voice.file_size
        file_id = message.voice.file_id
    elif message.document and message.document.mime_type.startswith('audio/'):
        file_size = message.document.file_size
        file_id = message.document.file_id
    elif message.video_note:
        file_size = message.video_note.file_size
        file_id = message.video_note.file_id
    else:
        await message.reply("🔔Неверный формат файла. Пожалуйста, отправьте аудио, голосовое сообщение, видеосообщение или аудио-документ.")
        return

    max_telegram_file_size = 20 * 1024 * 1024  # 20 MB limit for Telegram
    if file_size > max_telegram_file_size:
        await message.reply("🔔Аудиофайл или видеосообщение слишком большое. Пожалуйста, отправьте файл меньше 20 МБ.")
        return

    try:
        file = await bot.get_file(file_id)
        file_path = file.file_path
        audio_data = await bot.download_file(file_path)

        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
            await tmp_file.write(audio_data.read())
            temp_audio_path = tmp_file.name
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"----- Выберите модель Whisper -----", callback_data="ignore")])

        buttons_row = []
        for model_name in WHISPER_MODELS:
            button = InlineKeyboardButton(text=model_name, callback_data=f"whisper_model_{model_name}")
            buttons_row.append(button)
            if len(buttons_row) == 2:
                keyboard.inline_keyboard.append(buttons_row)
                buttons_row = []

        if buttons_row:
            keyboard.inline_keyboard.append(buttons_row)

        msg = await message.reply("Выберите модель для транскрипции аудио:", reply_markup=keyboard)
        await state.update_data(model_selection_message_id=msg.message_id, temp_audio_path=temp_audio_path)
        await state.set_state(Form.waiting_for_whisper_model_selection)
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла из Telegram: {e}")
        await message.reply("🚨Не удалось загрузить файл из Telegram. Возможно, файл слишком большой.")



async def process_whisper_model_selection(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    model_name = callback_query.data.split("_", 2)[2]

    data = await state.get_data()
    model_selection_message_id = data.get("model_selection_message_id")
    temp_audio_path = data.get("temp_audio_path")

    if model_selection_message_id:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=model_selection_message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения выбора модели: {e}")

    try:
        file_size = os.path.getsize(temp_audio_path)
        max_file_size = 25 * 1024 * 1024  # 25 MB limit

        if file_size > max_file_size:
            await bot.send_message(user_id, "🔔Аудиофайл слишком большой. Пожалуйста, отправьте файл меньше 25 МБ.")
            return

        transcription_text = await asyncio.to_thread(
            lambda: transcribe_audio_sync(groq_client, temp_audio_path, model_name)
        )

        if transcription_text:
            await bot.send_message(user_id, transcription_text)
        else:
            await bot.send_message(user_id, "Не удалось получить транскрипцию.")
    except Exception as e:
        logging.error(f"Ошибка при транскрипции аудио: {e}")
        await bot.send_message(user_id, f"🚨Произошла ошибка при транскрипции аудио: {e}")
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            await aiofiles.os.remove(temp_audio_path)
    await state.set_state(Form.waiting_for_message)


def transcribe_audio_sync(groq_client, temp_audio_path, model_name):
    try:
        with open(temp_audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=audio_file,
                model=model_name,
                response_format="verbose_json",
            )
            return transcription.text
    except Exception as e:
        logging.error(f"Ошибка при транскрипции аудио: {e}")
        return None
