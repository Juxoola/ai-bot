from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, bot, dp
from func.image_gen import process_image_generation_prompt, process_image_editing
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
from handlers.rate_limit import check_rate_limit
from func.decorators import access_required

@dp.message(F.text == "🎨 Сгенерировать")
@dp.message(F.text == "/generate_image")
@access_required
async def cmd_generate_image(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "generate_image"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    await message.reply("🔔Пожалуйста, введите запрос для генерации изображения:")
    await state.update_data(is_direct_image_gen=True)
    await state.set_state(Form.waiting_for_image_generation_prompt)


@dp.message(Form.waiting_for_image_generation_prompt, F.photo)
@access_required
async def process_image_edit_prompt_handler(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "image_edit"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    image_data = await bot.download_file(file_path)
    
    data = await state.get_data()
    existing_images = data.get("image_edit_data", [])
    if not isinstance(existing_images, list):
        existing_images = [existing_images] if existing_images else []
    existing_images.append(image_data)
    await state.update_data(image_edit_data=existing_images)
    
    await message.reply("🖌️ Фото добавлено для редактирования. Пришлите инструкцию или добавьте еще фото:")
    await state.set_state(Form.waiting_for_image_edit_instructions)


@dp.message(Form.waiting_for_image_generation_prompt)
@access_required
async def process_image_generation_prompt_handler(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "image_generation"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    try:
        await set_in_progress(state, message)
        await state.update_data(image_generation_prompt=message.text)
        await state.set_state(Form.waiting_for_message)
        await process_image_generation_prompt(message, state)
        await clear_in_progress(state, message)
    except Exception as e:
        await clear_in_progress(state, message)
        await message.reply(f"🔔Произошла ошибка при генерации изображения: {e}")


@dp.message(Form.waiting_for_image_edit_instructions)
@access_required
async def process_image_edit_instructions_handler(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "image_edit_instructions"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    try:
        await set_in_progress(state, message)
        instructions = message.text
        await state.update_data(image_edit_instructions=instructions)
        await state.set_state(Form.waiting_for_message)
        await process_image_editing(message, state)
        await clear_in_progress(state, message)
    except Exception as e:
        await clear_in_progress(state, message)
        await message.reply(f"🔔Произошла ошибка при редактировании изображения: {e}")


