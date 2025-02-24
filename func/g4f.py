from config import bot, g4f_client, get_client,Form
import config
from key import GEMINI_API_KEY
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import load_context,save_context,def_enhance, def_gen_model, def_aspect
from aiogram import types
import asyncio
import logging
import concurrent
from io import BytesIO
import fitz  # PyMuPDF
import tempfile
import os
from aiogram.enums import ParseMode
from func.messages import fix_markdown
import aiohttp
from urllib.parse import quote
import random
import aiofiles
from google import genai
from google.genai import types as genai_types


if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai_client = None
    logging.warning("GEMINI_API_KEY is not set. Google AI image generation will be unavailable.")

async def process_image_generation_prompt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prompt = data.get("image_generation_prompt")
    is_direct_image_gen = data.get("is_direct_image_gen", False)

    if not is_direct_image_gen:
        await message.reply(
            f"🔔Твой запрос '{message.text}' был переведен как '{prompt}'.\nНачинаю генерацию..."
        )

    await state.update_data(image_generation_prompt=prompt)

    user_id = message.from_user.id
    user_context = await load_context(user_id)
    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()
    model_name = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    await state.update_data(image_generation_model=model_name)
    await state.update_data(aspect_ratio=aspect_ratio)
    await state.update_data(enhance=enhance)

    aspect_ratio_options = {
        "1:1": (1024, 1024),
        "3:2": (1536, 1024),
        "2:3": (1024, 1536),
        "4:3": (1536, 1152),
        "3:4": (1152, 1536),
        "16:9": (1792, 1024),
        "9:16": (1024, 1792),
        "21:9": (2048, 896),
        "9:21": (896, 2048),
    }
    width, height = aspect_ratio_options.get(aspect_ratio, (1024, 1024)) 

    new_api_models = ["flux", "turbo"]
    
    google_ai_models = ["imagen-3.0-generate-002"]

    # Улучшение промпта для всех моделей, если enhance=True
    if enhance:
        try:
            system_prompt = "YOU ARE AN ELITE PROMPT ENGINEER SPECIALIZING IN ENHANCING PROMPTS FOR IMAGE DESCRIPTION GENERATION. YOUR TASK IS TO ACCEPT A TEXT INPUT IN ANY LANGUAGE AND PRODUCE AN OPTIMIZED PROMPT IN ENGLISH FOR A GENERATIVE MODEL. THE OPTIMIZED PROMPT MUST INCLUDE A DETAILED DESCRIPTION OF THE SCENE, SPECIFYING WHAT IS HAPPENING AND INCORPORATING SUBTLE DETAILS TO ENSURE BEAUTIFUL VISUALIZATION. YOUR OUTPUT SHOULD BE THE DESCRIPTION IN ENGLISH ONLY, WITHOUT ANY ADDITIONAL COMMENTS OR EXPLANATIONS. ###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE. 1. **TRANSLATE** the provided input text to English if necessary. 2. **ANALYZE** the scene to identify all critical elements such as the setting, actions, characters, and objects. 3. **ENRICH** the description by adding subtle details that enhance the visual quality and realism of the scene. 4. **ENSURE** the prompt is clear. vivid. and evocative to aid the generative model in"
            improved_prompt = await asyncio.to_thread(
                lambda:
                    config.enhance_prompt_client.chat.completions.create(
                        model="llama-3.1-70b",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                    )
            )
            prompt = improved_prompt.choices[0].message.content
        except Exception as e:
            logging.error(f"Error during prompt improvement: {e}")
            await bot.send_message(user_id, f"🚨Ошибка при улучшении промпта: {e}")

    if model_name in new_api_models:
        async def fetch_image():
            encoded_prompt = quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"

            # Отображение модели
            model_mapping = {
                "flux": "flux",
                "turbo": "turbo"
            }
            api_model_name = model_mapping.get(model_name, "turbo")  

            params = {
                "width": width,
                "height": height,
                "enhance": "false", 
                "model": api_model_name,
                "seed": random.randint(0, 1000000),
                "nologo": "true",
                "private": "true",
                "safe": "false"
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            return image_data
                        else:
                            error_message = await response.text()
                            return response.status, error_message 

            except Exception as e:
                logging.error(f"Error during image generation: {e}")
                raise e
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                result = await asyncio.to_thread(lambda: asyncio.run(fetch_image()))
                if isinstance(result, tuple) and result[0] == 500: 
                    status_code, error_message = result
                    retry_count += 1
                    await bot.send_message(
                        user_id, f"⚠️ Ошибка 500 при генерации изображения. Попытка {retry_count}/{max_retries}..."
                    )
                    if retry_count == max_retries:
                        await bot.send_message(
                            user_id, f"🚨 Не удалось сгенерировать изображение после {max_retries} попыток. Ошибка: {error_message}"
                        )
                        break 
                    await asyncio.sleep(1) 
                else:
                    image_data = result
                    caption = f"Фото сгенерировано моделью {model_name}"
                    if aspect_ratio:
                        caption += f" с соотношением сторон {aspect_ratio}"
                    if enhance:
                        caption += f", enhance: {enhance}"
                    caption += ":"

                    await bot.send_photo(
                        user_id,
                        photo=types.BufferedInputFile(image_data, filename="image.jpg"),
                        caption=caption,
                    )
                    caption2 = "Фото без сжатия"
                    await bot.send_document(user_id, document=types.BufferedInputFile(image_data, filename="image.jpg"), caption=caption2)
                    break
            except Exception as e:
                await bot.send_message(
                    user_id, f"🚨Ошибка во время генерации изображения: {e}"
                )
                break 

    elif model_name in google_ai_models:
        if genai_client:
            try:
                google_ai_aspect_ratio = aspect_ratio
                if aspect_ratio not in ["1:1", "3:4", "4:3", "9:16", "16:9"]:
                    google_ai_aspect_ratio = "1:1" 

                response = await asyncio.to_thread(
                    lambda: genai_client.models.generate_image(
                        model=model_name,
                        prompt=prompt,
                        config=genai_types.GenerateImageConfig(
                            number_of_images=1,
                            aspect_ratio=google_ai_aspect_ratio,
                            output_mime_type='image/jpeg'
                        )
                    )
                )

                image_data = response.generated_images[0].image.getvalue()

                caption = f"Фото сгенерировано моделью {model_name}"
                caption += f" с соотношением сторон {google_ai_aspect_ratio}" 
                if enhance:
                    caption += f", enhance: {enhance}"
                caption += ":"

                await bot.send_photo(
                    user_id,
                    photo=types.BufferedInputFile(image_data, filename="image.jpg"),
                    caption=caption,
                )
                caption2 = "Фото без сжатия"
                await bot.send_document(user_id, document=types.BufferedInputFile(image_data, filename="image.jpg"), caption=caption2)
            except Exception as e:
                logging.error(f"Error during Google AI image generation: {e}")
                await bot.send_message(user_id, f"🚨Ошибка во время генерации изображения с помощью Google AI: {e}")
        else:
            await bot.send_message(user_id, "🚨Генерация изображений с помощью Google AI недоступна, так как не указан GEMINI_API_KEY.")

    else:
        image_gen_client = get_client(user_id, "g4f_image_gen_client", model_name=model_name)

        try:
            response = await asyncio.to_thread(
                lambda: (
                    image_gen_client.images.generate(
                        prompt=prompt,
                        model=model_name,
                        response_format="url",
                        enhance=False,  
                        private=True,
                        width=width,
                        height=height,
                    )
                )
            )
            image_url = response.data[0].url
            caption = f"Фото сгенерировано моделью {model_name}"
            if aspect_ratio:
                caption += f" с соотношением сторон {aspect_ratio}"
            if enhance:
                caption += f", enhance: {enhance}"
            caption += ":"
            await bot.send_photo(
                user_id,
                photo=image_url,
                caption=caption,
            )
            caption2 = "Фото без сжатия"
            await bot.send_document(user_id, document=image_url, caption=caption2)
        except Exception as e:
            logging.error(f"Error during image generation: {e}")
            await bot.send_message(
                user_id, f"🚨Ошибка во время генерации изображения: {e}"
            )

    await state.set_state(Form.waiting_for_message)
    await state.update_data(image_generation_prompt=None)
    await state.update_data(aspect_ratio=None)
    await state.update_data(enhance=None)


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


async def handle_files_or_urls(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        if message.document:
            processing_msg = await message.reply("🔔 Начинается обработка файла...")

            file_id = message.document.file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_data = await bot.download_file(file_path)

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f"_{message.document.file_name}"
            ) as tmp_file:
                tmp_file.write(file_data.read())
                temp_file_path = tmp_file.name

            file_content = await asyncio.to_thread(process_local_file, temp_file_path)

            if file_content == "Unsupported file type":
                await processing_msg.edit_text(
                    "🚨 Неподдерживаемый тип файла. Пожалуйста, отправьте текстовый файл или PDF."
                )
                return
            elif file_content == "Error processing file":
                await processing_msg.edit_text(
                    "🚨 Произошла ошибка при обработке файла. Пожалуйста, попробуйте еще раз."
                )
                return

            user_context = await load_context(user_id)
            model_key = user_context["model"]  
            model_id, api_type = model_key.split('_')

            if api_type == "gemini":
                last_message = user_context["messages"][-1] if user_context["messages"] else None
                if last_message and last_message["role"] == "user" and any("data" in part for part in last_message["parts"]):
                    user_context["messages"][-1]["parts"].append({"text": file_content})
                else:
                    user_context["messages"].append({"role": "user", "parts": [{"text": file_content}]})
            elif api_type in ["glhf", "g4f"]:
                user_context["messages"].append({"role": "user", "content": file_content})

            await save_context(user_id, user_context)

            await processing_msg.edit_text("🔔 Файл успешно обработан и добавлен в контекст.")
            await state.set_state(Form.waiting_for_message)

    except Exception as e:
        logging.error(f"Ошибка при обработке файла: {e}")
        if 'processing_msg' in locals():
            await processing_msg.edit_text(f"🚨 Произошла ошибка при обработке файла: {e}")
        else:
            await message.reply(f"🚨 Произошла ошибка при обработке файла: {e}")
        await state.set_state(Form.waiting_for_message)
    finally:
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def process_local_file(file_path):

    import fitz 

    file_content = ""
    try:
        if file_path.endswith(".pdf"):
            with fitz.open(file_path) as doc:
                for page in doc:
                    file_content += page.get_text()
        elif file_path.endswith((
            ".txt", ".xml", ".json", ".js", ".har", ".sh", ".py",
            ".php", ".css", ".yaml", ".sql", ".log", ".csv", ".twig", ".md",
        )):
            with open(file_path, "r", encoding="utf-8") as f:
                file_content += f.read()
        else:
            return "Unsupported file type"
        return file_content
    except Exception as e:
        logging.error(f"Ошибка при обработке файла {file_path}: {e}")
        return "Error processing file"
