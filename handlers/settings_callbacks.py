
from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import Form, dp
from database import is_allowed
from settings import (
    cmd_settings, select_model_handler, select_image_gen_model_handler,
    select_image_rec_model_handler, select_aspect_ratio_handler,
    process_enhance_selection_handler, close_settings_handler,
    model_selection_handler, process_image_generation_model_handler,
    process_image_recognition_model_selection_handler, process_aspect_ratio_selection_handler,
    toggle_processing_time_handler, select_role_handler, select_voice_handler,
    process_voice_selection_handler, role_selection_handler, api_selection_handler
)

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

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
async def process_role_selection_handler_wrapper(callback_query: types.CallbackQuery, state: FSMContext):
    await role_selection_handler(callback_query, state) 