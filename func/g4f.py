from config import bot
from aiogram.fsm.context import FSMContext
from database import load_context,save_context
from aiogram import types
from io import BytesIO


async def handle_image_recognition(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    image_data = await bot.download_file(file_path)
    image = BytesIO(image_data.read())
    image.seek(0)

    user_context = await load_context(user_id)
    user_context["g4f_image"] = image
    await save_context(user_id, user_context)

    await bot.send_message(user_id, "🔔Введите промпт для распознавания изображения:")