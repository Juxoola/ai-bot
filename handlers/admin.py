from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import dp, Form, bot
from keyboards import get_admin_keyboard, get_main_keyboard
from database import is_admin
from func.decorators import admin_required
from func.admin import (cmd_send_to_all, process_message_to_all, cmd_send_to_user,
                        process_user_id_to_send, process_message_to_user,
                        cmd_add_user, process_add_user_id, cmd_remove_user,
                        process_remove_user_id, cmd_add_model, process_new_model_name,
                        process_new_model_id, process_new_model_api, cmd_delete_model,
                        process_delete_model_name, process_confirm_delete,
                        cmd_add_image_rec_model, cmd_delete_image_rec_model,
                        process_delete_image_rec_model_name, process_confirm_delete_image_rec_model,
                        cmd_add_image_gen_model, cmd_delete_image_gen_model,
                        process_delete_image_gen_model_name, process_confirm_delete_image_gen_model,
                        process_new_image_rec_model_id, process_new_image_rec_model_api,
                        process_new_image_gen_model_id, process_new_image_gen_model_api,
                        process_delete_model_api_selection, process_delete_model_by_api)

@dp.message(F.text == "👑 Панель администратора")
@admin_required
async def cmd_open_admin_keyboard(message: types.Message, state: FSMContext):
    await message.reply("🔔Вы открыли админ-клавиатуру.", reply_markup= await get_admin_keyboard())


@dp.message(F.text == "Главное меню")
@admin_required
async def cmd_back_to_main_menu(message: types.Message, state: FSMContext):
    await message.reply("🔔Вы вернулись в главное меню.", reply_markup=await get_main_keyboard(include_admin_button=True))
    await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "📢 Отправить всем")
@admin_required
async def cmd_send_to_all_handler(message: types.Message, state: FSMContext):
    await cmd_send_to_all(message, state)

@dp.message(Form.waiting_for_message_to_all)
@admin_required
async def process_message_to_all_handler(message: types.Message, state: FSMContext):
    await process_message_to_all(message, state)

@dp.message(F.text == "📩 Отправить пользователю")
@admin_required
async def cmd_send_to_user_handler(message: types.Message, state: FSMContext):
    await cmd_send_to_user(message, state)

@dp.message(Form.waiting_for_user_id_to_send)
@admin_required
async def process_user_id_to_send_handler(message: types.Message, state: FSMContext):
    await process_user_id_to_send(message, state)

@dp.message(Form.waiting_for_message_to_user)
@admin_required
async def process_message_to_user_handler(message: types.Message, state: FSMContext):
    await process_message_to_user(message, state)



@dp.message(F.text == "👤 Добавить пользователя")
@admin_required
async def cmd_add_user_handler(message: types.Message, state: FSMContext):
    await cmd_add_user(message, state)

@dp.message(Form.waiting_for_add_user_id)
@admin_required
async def process_add_user_id_handler(message: types.Message, state: FSMContext):
    await process_add_user_id(message, state)

@dp.message(F.text == "🚫 Удалить пользователя")
@admin_required
async def cmd_remove_user_handler(message: types.Message, state: FSMContext):
    await cmd_remove_user(message, state)

@dp.message(Form.waiting_for_remove_user_id)
@admin_required
async def process_remove_user_id_handler(message: types.Message, state: FSMContext):
    await process_remove_user_id(message, state)

@dp.message(F.text == "➕ Добавить модель")
@admin_required
async def cmd_add_model_handler(message: types.Message, state: FSMContext):
    await cmd_add_model(message, state)

@dp.message(F.text == "❌ Удалить модель")
@admin_required
async def cmd_delete_model_handler(message: types.Message, state: FSMContext):
    await cmd_delete_model(message, state)

@dp.message(Form.waiting_for_new_model_name)
@admin_required
async def process_new_model_name_handler(message: types.Message, state: FSMContext):
    await process_new_model_name(message, state)

@dp.message(Form.waiting_for_new_model_id)
@admin_required
async def process_new_model_id_handler(message: types.Message, state: FSMContext):
    await process_new_model_id(message, state)

@dp.message(Form.waiting_for_new_model_api)
@admin_required
async def process_new_model_api_handler(message: types.Message, state: FSMContext):
    await process_new_model_api(message, state)

@dp.callback_query(Form.waiting_for_confirmation, lambda c: c.data and c.data.startswith('confirm_delete_'))
@admin_required
async def process_confirm_delete_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete(callback_query, state)

@dp.callback_query(Form.waiting_for_delete_model_name)
@admin_required
async def process_delete_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_model_name(callback_query, state)

@dp.message(F.text == "➕ Добавить модель распознавания")
@admin_required
async def cmd_add_image_rec_model_handler(message: types.Message, state: FSMContext):
    await cmd_add_image_rec_model(message, state)

@dp.message(F.text == "❌ Удалить модель распознавания")
@admin_required
async def cmd_delete_image_rec_model_handler(message: types.Message, state: FSMContext):
    await cmd_delete_image_rec_model(message, state)


@dp.callback_query(Form.waiting_for_delete_image_rec_model_name)
@admin_required
async def process_delete_image_rec_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_image_rec_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_rec_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_rec_"))
@admin_required
async def process_confirm_delete_image_rec_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete_image_rec_model(callback_query, state)

@dp.message(F.text == "➕ Добавить модель генерации")
@admin_required
async def cmd_add_image_gen_model_handler(message: types.Message, state: FSMContext):
    await cmd_add_image_gen_model(message, state)

@dp.message(F.text == "❌ Удалить модель генерации")
@admin_required
async def cmd_delete_image_gen_model_handler(message: types.Message, state: FSMContext):
    await cmd_delete_image_gen_model(message, state)



@dp.callback_query(Form.waiting_for_delete_image_gen_model_name)
@admin_required
async def process_delete_image_gen_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_image_gen_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_gen_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_gen_"))
@admin_required
async def process_confirm_delete_image_gen_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_confirm_delete_image_gen_model(callback_query, state)

@dp.message(Form.waiting_for_new_image_rec_model_id)
@admin_required
async def process_new_image_rec_model_id_handler(message: types.Message, state: FSMContext):
    await process_new_image_rec_model_id(message, state)

@dp.message(Form.waiting_for_new_image_rec_model_api)
@admin_required
async def process_new_image_rec_model_api_handler(message: types.Message, state: FSMContext):
    await process_new_image_rec_model_api(message, state)

@dp.message(Form.waiting_for_new_image_gen_model_id)
@admin_required
async def process_new_image_gen_model_id_handler(message: types.Message, state: FSMContext):
    await process_new_image_gen_model_id(message, state)

@dp.message(Form.waiting_for_new_image_gen_model_api)
@admin_required
async def process_new_image_gen_model_api_handler(message: types.Message, state: FSMContext):
    await process_new_image_gen_model_api(message, state)

@dp.callback_query(Form.waiting_for_delete_model_api_selection)
@admin_required
async def process_delete_model_api_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_model_api_selection(callback_query, state)

@dp.callback_query(Form.waiting_for_delete_model_by_api)
@admin_required
async def process_delete_model_by_api_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_delete_model_by_api(callback_query, state)
