import asyncio
import random
import httpx
from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, bot, dp
from database import load_context, is_allowed
from func.g4f import process_image_generation_prompt

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(F.text == "🎨 Сгенерировать")
@dp.message(F.text == "/generate_image")
async def cmd_generate_image(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    user_context = await load_context(user_id)
    
    await message.reply(
        "Пожалуйста, отправьте текстовый запрос для генерации изображения или отправьте фото для редактирования.\n"
        f"Текущее соотношение сторон: {user_context.get('aspect', '1:1')}"
    )
    
    await state.set_state(Form.waiting_for_image_generation_prompt)


@dp.message(Form.waiting_for_image_generation_prompt, F.photo)
async def process_image_edit_prompt_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await state.update_data(photo=message.photo[-1].file_id)
    
    await message.reply(
        "Пожалуйста, опишите желаемые изменения, которые нужно внести в изображение."
    )
    
    await state.set_state(Form.waiting_for_image_edit_instructions)


@dp.message(Form.waiting_for_image_generation_prompt)
async def process_image_generation_prompt_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await process_image_generation_prompt(message, state)


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
            caption=f"{meme['title']}\nИсточник: {meme['source']}"
        )
        
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        
    except Exception as e:
        await processing_message.edit_text(f"Не удалось найти мем. Ошибка: {str(e)}")
        
    current_state = await state.get_state()
    if current_state != Form.waiting_for_message:
        await state.set_state(Form.waiting_for_message) 