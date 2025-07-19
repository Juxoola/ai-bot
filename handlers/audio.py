from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import Form, dp
from database import whisp_models
from func.audio import handle_audio, process_whisper_model_selection
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
from handlers.rate_limit import check_rate_limit, check_callback_rate_limit
from func.decorators import access_required

@dp.message(F.text == "🎤 Аудио")
@dp.message(F.text == "/audio")
@access_required
async def cmd_audio(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "audio"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    user_id = message.from_user.id
    current_state = await state.get_state()

    try:
        await set_in_progress(state)
        
        if current_state == Form.waiting_for_audio:
            await state.set_state(Form.waiting_for_message)
            await message.reply("🔔Режим ожидания аудио отключен.")
        else:
            await message.reply("🔔Пожалуйста, отправьте аудиофайл для транскрипции.")
            await state.set_state(Form.waiting_for_audio)
        
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await message.reply(f"🔔Произошла ошибка: {e}")

@dp.message(Form.waiting_for_audio, lambda message: message.audio or message.voice or message.document and message.document.mime_type.startswith('audio/') or message.video_note)
async def handle_audio_handler(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "audio_processing"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    try:
        await set_in_progress(state)
        
        WHISPER_MODELS = await whisp_models()
        await handle_audio(message, state, WHISPER_MODELS)
        
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await message.reply(f"🔔Произошла ошибка при обработке аудио: {e}")

@dp.callback_query(Form.waiting_for_whisper_model_selection, lambda c: c.data and c.data.startswith("whisper_model_"))
async def process_whisper_model_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not await check_callback_rate_limit(callback_query, "whisper_model_selection"):
        return
    
    message = callback_query.message
    mock_message = types.Message(
        message_id=message.message_id,
        date=message.date,
        chat=message.chat,
        from_user=callback_query.from_user,
        content_type="text",
        text="/whisper_model_selection"
    )
    
    can_proceed = await check_in_progress(mock_message, state)
    if not can_proceed:
        await callback_query.answer("⏳ Дождитесь завершения текущей операции или используйте /cancel")
        return
    
    try:
        await set_in_progress(state)
        
        await process_whisper_model_selection(callback_query, state)
        
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await callback_query.message.reply(f"🔔Произошла ошибка при выборе модели: {e}")
        await callback_query.answer()