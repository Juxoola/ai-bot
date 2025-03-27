#admin section
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import dp, Form, bot
from keyboards import get_admin_keyboard, get_main_keyboard
from database import is_admin
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
                        process_new_image_gen_model_id, 
                        process_new_image_gen_model_api)


@dp.message(F.text == "Открыть админ-клавиатуру")
async def cmd_open_admin_keyboard(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await message.reply("🔔Вы открыли админ-клавиатуру.", reply_markup= await get_admin_keyboard())


@dp.message(F.text == "Главное меню")
async def cmd_back_to_main_menu(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await message.reply("🔔Вы вернулись в главное меню.", reply_markup=await get_main_keyboard(include_admin_button=True))
    await state.set_state(Form.waiting_for_message)


@dp.message(Command("send_to_all"))
async def cmd_send_to_all_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_send_to_all(message, state)

@dp.message(Form.waiting_for_message_to_all)
async def process_message_to_all_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_message_to_all(message, state)

@dp.message(Command("send_to_user"))
async def cmd_send_to_user_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_send_to_user(message, state)

@dp.message(Form.waiting_for_user_id_to_send)
async def process_user_id_to_send_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_user_id_to_send(message, state)

@dp.message(Form.waiting_for_message_to_user)
async def process_message_to_user_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_message_to_user(message, state)



@dp.message(Command("add_user"))
async def cmd_add_user_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_add_user(message, state)

@dp.message(Form.waiting_for_add_user_id)
async def process_add_user_id_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_add_user_id(message, state)

@dp.message(Command("remove_user"))
async def cmd_remove_user_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_remove_user(message, state)

@dp.message(Form.waiting_for_remove_user_id)
async def process_remove_user_id_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_remove_user_id(message, state)

@dp.message(Command("add_model"))
async def cmd_add_model_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_add_model(message, state)

@dp.message(Command("delete_model"))
async def cmd_delete_model_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_delete_model(message, state)

@dp.message(Form.waiting_for_new_model_name)
async def process_new_model_name_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_model_name(message, state)

@dp.message(Form.waiting_for_new_model_id)
async def process_new_model_id_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_model_id(message, state)

@dp.message(Form.waiting_for_new_model_api)
async def process_new_model_api_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_model_api(message, state)

@dp.callback_query(Form.waiting_for_confirmation, lambda c: c.data and c.data.startswith('confirm_delete_'))
async def process_confirm_delete_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_confirm_delete(callback_query, state)

@dp.callback_query(Form.waiting_for_delete_model_name)
async def process_delete_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_delete_model_name(callback_query, state)

@dp.message(Command("add_image_rec_model"))
async def cmd_add_image_rec_model_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_add_image_rec_model(message, state)

@dp.message(Command("delete_image_rec_model"))
async def cmd_delete_image_rec_model_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_delete_image_rec_model(message, state)


@dp.callback_query(Form.waiting_for_delete_image_rec_model_name)
async def process_delete_image_rec_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_delete_image_rec_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_rec_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_rec_"))
async def process_confirm_delete_image_rec_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_confirm_delete_image_rec_model(callback_query, state)

@dp.message(Command("add_image_gen_model"))
async def cmd_add_image_gen_model_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_add_image_gen_model(message, state)

@dp.message(Command("delete_image_gen_model"))
async def cmd_delete_image_gen_model_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await cmd_delete_image_gen_model(message, state)



@dp.callback_query(Form.waiting_for_delete_image_gen_model_name)
async def process_delete_image_gen_model_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_delete_image_gen_model_name(callback_query, state)

@dp.callback_query(Form.waiting_for_confirmation_image_gen_model_delete, lambda c: c.data and c.data.startswith("confirm_delete_image_gen_"))
async def process_confirm_delete_image_gen_model_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_confirm_delete_image_gen_model(callback_query, state)

@dp.message(Form.waiting_for_new_image_rec_model_id)
async def process_new_image_rec_model_id_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_image_rec_model_id(message, state)

@dp.message(Form.waiting_for_new_image_rec_model_api)
async def process_new_image_rec_model_api_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_image_rec_model_api(message, state)

@dp.message(Form.waiting_for_new_image_gen_model_id)
async def process_new_image_gen_model_id_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_image_gen_model_id(message, state)

@dp.message(Form.waiting_for_new_image_gen_model_api)
async def process_new_image_gen_model_api_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Извините, у вас нет прав для выполнения этого действия.")
        return
        
    await process_new_image_gen_model_api(message, state)