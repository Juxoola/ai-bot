import asyncio
import random
import httpx
from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, bot, dp
from database import is_allowed
from func.g4f import process_image_generation_prompt, process_image_editing

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(F.text == "🎨 Сгенерировать")
@dp.message(F.text == "/generate_image")
async def cmd_generate_image(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await message.reply("🔔Пожалуйста, введите запрос для генерации изображения:")
    await state.update_data(is_direct_image_gen=True)
    await state.set_state(Form.waiting_for_image_generation_prompt)


@dp.message(Form.waiting_for_image_generation_prompt, F.photo)
async def process_image_edit_prompt_handler(message: types.Message, state: FSMContext):
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
async def process_image_generation_prompt_handler(message: types.Message, state: FSMContext):
    await state.update_data(image_generation_prompt=message.text)
    await state.set_state(Form.waiting_for_message)
    await process_image_generation_prompt(message, state)


@dp.message(Form.waiting_for_image_edit_instructions)
async def process_image_edit_instructions_handler(message: types.Message, state: FSMContext):
    instructions = message.text
    await state.update_data(image_edit_instructions=instructions)
    await state.set_state(Form.waiting_for_message)
    await process_image_editing(message, state)


async def fetch_random_meme():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://meme-api.com/gimme")
            data = response.json()
            
            if "url" in data and data["url"]:
                return {
                    "url": data["url"],
                    "title": data.get("title", "Random Meme"),
                    "source": f"https://reddit.com{data.get('postLink', '')}"
                }
    except Exception as e:
        print(f"Error fetching from meme-api.com: {e}")


@dp.message(F.text == "🎭 Мем")
@dp.message(F.text == "/meme")
async def cmd_random_meme(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    processing_message = await message.reply("Ищу смешной мем...")
    
    try:
        meme = await fetch_random_meme()
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=meme["url"],
            caption=f"{meme['title']}"
        )
        
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        
    except Exception as e:
        await processing_message.edit_text(f"Не удалось найти мем. Ошибка: {str(e)}")
        
    current_state = await state.get_state()
    if current_state != Form.waiting_for_message:
        await state.set_state(Form.waiting_for_message) 