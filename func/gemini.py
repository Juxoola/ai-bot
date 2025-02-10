from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form,  bot
from database import load_context,save_context,av_models
import asyncio
import base64
import logging
from aiogram.enums import ParseMode
from func.messages import fix_markdown
import google.generativeai as genai

async def handle_image(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    photo = message.photo[-1]
    file_id = photo.file_id

    file = await bot.get_file(file_id)
    file_path = file.file_path

    image_data = await bot.download_file(file_path)

    base64_image = await asyncio.to_thread(
        lambda: base64.b64encode(image_data.read()).decode('utf-8')
    )

    user_context["messages"].append({
        "role": "user",
        "parts": [
            {"mime_type": "image/jpeg", "data": base64_image}
        ]
    })

    await save_context(user_id, user_context)
    await state.update_data(image_data=base64_image)
    await message.reply("🔔Изображение получено. Теперь отправьте текстовый промпт.")


async def process_custom_image_prompt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    prompt = message.text

    data = await state.get_data()
    base64_image = data.get("image_data")

    if not base64_image:
        await message.reply("🔔Сначала отправьте изображение.")
        return

    user_context = await load_context(user_id)
    model_key = user_context["model"]  # Формат: "model_id_api"
    model_id, api_type = model_key.split('_')

    new_message = {
        "role": "user",
        "parts": [
            {"text": prompt},
            {"mime_type": "image/jpeg", "data": base64_image}
        ]
    }

    user_context["messages"].append(new_message)

    await save_context(user_id, user_context)
    
    try:
        model = genai.GenerativeModel(model_id)
        chat = model.start_chat(history=user_context["messages"][:-1])
        response = await asyncio.to_thread(
            lambda: chat.send_message(user_context["messages"][-1])
        )

        await bot.send_message(user_id, response.text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logging.error(f"Ошибка Markdown при отправке сообщения: {e}")
        try:
            await bot.send_message(user_id,
                f"🔔Попытка фиксить форматирование сообщения"
            )
            fixed_response = await fix_markdown(response.text)
            await bot.send_message(user_id, fixed_response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await bot.send_message(user_id,
                f"🚨Произошла ошибка при форматировании сообщения: {e}\n\n"
                "Отправляю без форматирования."
            )
            await bot.send_message(user_id, response.text)

        user_context["messages"].append({"role": "assistant", "content": response.text})
        await save_context(user_id, user_context)

    except Exception as e:
        logging.error(f"Ошибка при работе с моделью Gemini: {e}")
        await bot.send_message(user_id, f"🚨Произошла ошибка при работе с моделью Gemini: {e}")

    await state.set_state(Form.waiting_for_message)
    await state.update_data(image_data=None)

async def handle_pdf(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context = await load_context(user_id)

    file_id = message.document.file_id

    file = await bot.get_file(file_id)
    file_path = file.file_path

    pdf_data = await bot.download_file(file_path)

    base64_pdf = await asyncio.to_thread(
        lambda: base64.b64encode(pdf_data.read()).decode('utf-8')
    )

    user_context["messages"].append({
        "role": "user",
        "parts": [
            {"mime_type": "application/pdf", "data": base64_pdf}
        ]
    })

    await save_context(user_id, user_context)

    await message.reply("🔔PDF-файл получен и добавлен в контекст. Теперь вы можете задавать вопросы.")
    await state.set_state(Form.waiting_for_message)

