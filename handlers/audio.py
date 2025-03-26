from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import Form, dp
from database import is_allowed, whisp_models
from func.audio import handle_audio, process_whisper_model_selection

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

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