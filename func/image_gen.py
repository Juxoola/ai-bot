import asyncio
import logging
import os
import random
import time
from io import BytesIO
from urllib.parse import quote, urlencode

import aiohttp
import config
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form, bot, gemini_client, get_client, openai_clients
from database import def_aspect, def_enhance, def_gen_model, load_context
from deep_translator import GoogleTranslator
from google.genai import types as genai_types
from handlers.check import check_in_progress
from PIL import Image

from .utils import (async_run_with_timeout,
                    calculate_and_show_processing_time, DEFAULT_API_TIMEOUT)

new_api_models = ["flux", "turbo"]
fresed_models = ["stable-diffusion-3", "stable-diffusion-3-large", "stable-diffusion-3-large-turbo", "flux-pro-1.1", "flux-pro-1"]
google_ai_models = ["gemini-2.0-flash-preview-image-generation"]
pollinations_edit_models = ["nanobanana", "seedream"]


async def get_user_settings(user_id):
    user_context = await load_context(user_id)
    DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()
    DEFAULT_ASPECT_RATIO = await def_aspect()
    DEFAULT_ENHANCE = await def_enhance()

    model_info = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    enhance = user_context.get("enhance", DEFAULT_ENHANCE)

    last_underscore_pos = model_info.rfind('_')
    if last_underscore_pos != -1:
        model_id = model_info[:last_underscore_pos]
        api_type = model_info[last_underscore_pos + 1:]
    else:
        model_id = model_info
        api_type = "poli"

    return model_id, api_type, aspect_ratio, enhance, user_context


async def get_image_dimensions(aspect_ratio):
    aspect_ratio_options = {
        "1:1": (2048, 2048), "3:2": (1536, 1024), "2:3": (1024, 1536),
        "4:3": (1536, 1152), "3:4": (1152, 1536), "16:9": (1792, 1024),
        "9:16": (1024, 1792), "21:9": (2048, 896), "9:21": (896, 2048),
        "1:1(2)": (1024, 1024), "3:4(2)": (896, 1280), "4:3(2)": (1280, 896),
        "9:16(2)": (768, 1408), "16:9(2)": (1408, 768), "3:4(3)": (1792, 2560),
        "4:3(3)": (2560, 1792), "9:16(3)": (1536, 2816), "16:9(3)": (2816, 1536)
    }
    return aspect_ratio_options.get(aspect_ratio, (1024, 1024))


async def translate_prompt(prompt, user_id, original_message_id):
    try:
        translator = GoogleTranslator(source='auto', target='en')
        translated_prompt = await asyncio.to_thread(translator.translate, prompt)
        if translated_prompt and translated_prompt != prompt:
            await bot.send_message(
                user_id,
                f"🔔 Ваш запрос был переведен на английский для лучших результатов:\n'{prompt}' → '{translated_prompt}'",
                reply_to_message_id=original_message_id
            )
            return translated_prompt
    except Exception as e:
        logging.error(f"Ошибка во время перевода промпта: {e}")
        await bot.send_message(
            user_id,
            f"⚠️ Не удалось перевести запрос на английский: {e}",
            reply_to_message_id=original_message_id
        )
    return prompt


async def enhance_prompt(prompt, user_id):
    try:
        improved_prompt = await config.openai_clients["poli"].chat.completions.create(
            model="openai-large",
            messages=[
                {"role": "user", "content": f"You are a text prompt generator for creating images. I will give you a post topic, and you will generate one best-quality prompt and show it to me.\n\n{prompt}\n\nDo not ask for clarifications—just generate the best prompt using your creativity, and I will request changes if needed.\n\n### Prompt Structure:\n- Camera angle → Scene description → Character description → Camera settings\n- Character descriptions must always be separated by commas.\n- All parts of the structure must be separated by commas.\n\n### Notes:\n- At the end of the prompt, you may also include the camera type (if it's not a painting style), such as DSLR, Nikon D, Canon EOS R3, etc.\n- You can specify a lens type (e.g., 14mm focal length, 35mm, fisheye, wide-angle, etc.) if necessary.\n\n### Example Formatting:\n- Highly detailed watercolor painting, majestic lion, intricate fur detail, photograph, natural lighting, brush strokes, watercolor splatters\n- Portrait photo of a red-haired girl standing in water covered with lily pads, long braided hair, Canon EOS R3, volumetric lighting\n- Wide-angle, stunning sunset over a wide open beach, vibrant pink-orange and gold sky, water reflecting sunset colors, mesmerizing effect, lone tall tree in foreground, tree silhouetted against sunset, dramatic feel, Canon EOS R3, landscape scene\n- Watercolor painting, family of elephants roaming the savanna, delicate brush strokes, soft colors, Canon EOS R3, wide-angle lens\n\n### IMPORTANT:\nGenerate the best possible prompt immediately in English, and show only the prompt. Do not write anything else."}
            ],
        )
        return improved_prompt.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка во время улучшения промпта: {e}")
        await bot.send_message(user_id, f"🚨Ошибка при улучшении промпта: {e}")
        return prompt


async def send_generated_image(user_id, image_data, caption, original_message_id):
    if isinstance(image_data, str):  # URL
        photo = image_data
        document = image_data
    else:  # Bytes
        photo = types.BufferedInputFile(image_data, filename="image.jpg")
        document = types.BufferedInputFile(image_data, filename="image.jpg")

    await asyncio.gather(
        bot.send_photo(user_id, photo=photo, caption=caption, reply_to_message_id=original_message_id),
        bot.send_document(user_id, document=document, caption="Фото без сжатия", reply_to_message_id=original_message_id)
    )


async def generate_with_retry(generation_func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await async_run_with_timeout(generation_func, DEFAULT_API_TIMEOUT)
        except Exception as e:
            logging.error(f"Ошибка во время генерации изображения (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt + 1 == max_retries:
                raise
            await asyncio.sleep(1)


async def generate_image_poli(prompt, width, height, model_id):
    async def fetch():
        if config.http_session is None:
            raise RuntimeError("AIOHTTP session is not initialized.")
        encoded_prompt = quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        params = {
            "width": width, "height": height, "enhance": "false", "model": model_id,
            "seed": random.randint(0, 1000000), "nologo": "true", "private": "true",
            "safe": "false", "token": config.providers_config.get("poli", {}).get("api_key")
        }
        async with config.http_session.get(url, params=params, timeout=DEFAULT_API_TIMEOUT) as response:
            response.raise_for_status()
            return await response.read()
    return await generate_with_retry(fetch)


async def generate_image_openai(prompt, width, height, model_id, api_type):
    client = openai_clients.get(api_type)
    async def generate():
        response = await client.images.generate(
            model=model_id, prompt=prompt, size=f"{width}x{height}", n=1, response_format="url"
        )
        if response is None:
            raise Exception("Превышено время ожидания при генерации изображения.")
        if hasattr(response, 'data') and response.data:
            image_url = response.data[0].url
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    resp.raise_for_status()
                    return await resp.read()
        raise Exception(f"Неподдерживаемый формат ответа от {api_type} client")
    return await generate_with_retry(generate)


async def generate_image_gemini(prompt, model_id):
    async def generate():
        response = await gemini_client.aio.models.generate_content(
            model=model_id, contents=prompt,
            config=genai_types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
        )
        if response is None:
            raise Exception("Превышено время ожидания при генерации изображения.")
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                return part.inline_data.data
        text_response = response.text if hasattr(response, 'text') else ""
        raise Exception(f"Модель не сгенерировала изображение. Ответ: {text_response}")
    return await generate_with_retry(generate)


async def generate_image_g4f(prompt, width, height, model_id, user_id):
    client = await get_client(user_id, "g4f_image_gen_client", model_name=model_id)
    async def generate():
        response = await client.images.generate(
            prompt=prompt, model=model_id, response_format="url",
            enhance=False, private=True, width=width, height=height
        )
        if response is None:
            raise Exception("Превышено время ожидания при генерации изображения.")
        return response.data[0].url
    return await generate_with_retry(generate)


async def process_image_generation_prompt(message: types.Message, state: FSMContext):
    if not await check_in_progress(message, state):
        return

    start_time = time.time()
    user_id = message.from_user.id
    original_message_id = message.message_id

    data = await state.get_data()
    prompt = data.get("image_generation_prompt")
    is_direct_image_gen = data.get("is_direct_image_gen", False)

    if not is_direct_image_gen:
        await message.reply(f"🔔Твой запрос '{message.text}' был переведен как '{prompt}'.\nНачинаю генерацию...")

    model_id, api_type, aspect_ratio, enhance, user_context = await get_user_settings(user_id)
    width, height = await get_image_dimensions(aspect_ratio)

    if not enhance:
        prompt = await translate_prompt(prompt, user_id, original_message_id)
    else:
        prompt = await enhance_prompt(prompt, user_id)

    try:
        image_data = None
        if api_type == "poli":
            image_data = await generate_image_poli(prompt, width, height, model_id)
        elif api_type in openai_clients:
            image_data = await generate_image_openai(prompt, width, height, model_id, api_type)
        elif api_type == "gemini":
            if not gemini_client:
                await bot.send_message(user_id, "🚨Генерация изображений через Gemini недоступна.", reply_to_message_id=original_message_id)
                return
            image_data = await generate_image_gemini(prompt, model_id)
        elif api_type == "g4f":
            image_data = await generate_image_g4f(prompt, width, height, model_id, user_id)

        if image_data:
            caption = f"Фото сгенерировано моделью {model_id}"
            if aspect_ratio:
                caption += f" с соотношением сторон {aspect_ratio}"
            if enhance:
                caption += f", enhance: {enhance}"
            caption += ":"
            await send_generated_image(user_id, image_data, caption, original_message_id)

    except Exception as e:
        logging.error(f"Не удалось сгенерировать изображение с помощью {api_type}/{model_id}: {e}")
        await bot.send_message(
            user_id,
            "🚨 Не удалось сгенерировать изображение после нескольких попыток. Пожалуйста, попробуйте еще раз.",
            reply_to_message_id=original_message_id
        )
    finally:
        await calculate_and_show_processing_time(message, user_context, start_time)
        await state.set_state(Form.waiting_for_message)
        await state.update_data(image_generation_prompt=None, aspect_ratio=None, enhance=None, original_message_id=None)

IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "key")


async def upload_to_imgbb(image_bytes: bytes) -> str:
    if not IMGBB_API_KEY or IMGBB_API_KEY == "key":
        raise ValueError("API-ключ для ImgBB не указан.")
    if config.http_session is None:
        raise RuntimeError("AIOHTTP session is not initialized.")

    url = "https://api.imgbb.com/1/upload"
    data = aiohttp.FormData()
    data.add_field('key', IMGBB_API_KEY)
    data.add_field('image', image_bytes, filename='image.jpg', content_type='image/jpeg')

    try:
        async with config.http_session.post(url, data=data, timeout=30) as response:
            response_json = await response.json()
            if response.status == 200 and response_json.get('success'):
                return response_json['data']['url']
            error_message = response_json.get('error', {}).get('message', 'Неизвестная ошибка')
            raise Exception(f"API ImgBB вернуло ошибку: {response.status}, {error_message}")
    except aiohttp.ClientError as e:
        logging.error(f"Сетевая ошибка при загрузке на ImgBB: {e}")
        raise Exception(f"Сетевая ошибка при загрузке на ImgBB: {e}")


def resize_image_if_needed(image_bytes: bytes) -> tuple[bytes, int, int]:
    with Image.open(BytesIO(image_bytes)) as img:
        width, height = img.size
        if width * height < 921600:  # 960*960
            scale_factor = (921600 / (width * height)) ** 0.5 * 1.01
            new_width, new_height = int(width * scale_factor), int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            width, height = new_width, new_height
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue(), width, height


async def edit_image_pollinations(instructions, image_data, model_id, user_id, original_message_id):
    try:
        image_bytes = image_data[0] if isinstance(image_data, list) else image_data
        if hasattr(image_bytes, 'read'):
            image_bytes = image_bytes.read()

        image_bytes, width, height = await asyncio.to_thread(resize_image_if_needed, image_bytes)
        image_url = await upload_to_imgbb(image_bytes)

        encoded_prompt = quote(instructions)
        base_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        params = {
            "model": model_id, "image": image_url, "width": width, "height": height,
            "nologo": "true", "private": "true", "safe": "false",
            "token": config.providers_config.get("poli", {}).get("api_key")
        }
        full_url = f"{base_url}?{urlencode(params)}"

        async def fetch():
            async with config.http_session.get(full_url, timeout=DEFAULT_API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.read()

        edited_image_data = await async_run_with_timeout(fetch, DEFAULT_API_TIMEOUT)
        if not edited_image_data:
            raise Exception("Не удалось получить отредактированное изображение.")

        caption = f"✏️ Изображение отредактировано с помощью {model_id}"
        await send_generated_image(user_id, edited_image_data, caption, original_message_id)

    except Exception as e:
        logging.error(f"Ошибка во время редактирования изображения Pollinations: {e}")
        await bot.send_message(user_id, "🚨 Ошибка при редактировании изображения", reply_to_message_id=original_message_id)


async def prepare_gemini_edit_payload(image_data):
    images_bytes = image_data if isinstance(image_data, list) else [image_data]
    pil_images = []
    for img_bytes in images_bytes:
        if hasattr(img_bytes, 'read'):
            img_bytes = img_bytes.read()
        pil_images.append(await asyncio.to_thread(lambda: Image.open(BytesIO(img_bytes))))
    return pil_images


async def edit_image_gemini(instructions, image_data, model_id, user_id, original_message_id):
    try:
        pil_images = await prepare_gemini_edit_payload(image_data)
        translated_instructions = await translate_prompt(instructions, user_id, original_message_id)
        contents = [translated_instructions, *pil_images]

        async def generate():
            return await gemini_client.aio.models.generate_content(
                model=model_id, contents=contents,
                config=genai_types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
            )

        response = await async_run_with_timeout(generate, DEFAULT_API_TIMEOUT)
        if response is None:
            raise Exception("Превышено время ожидания.")

        edited_image_data, text_response = None, ""
        if hasattr(response, 'candidates') and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    text_response += part.text
                elif hasattr(part, 'inline_data') and part.inline_data:
                    edited_image_data = part.inline_data.data

        if not edited_image_data:
            error_msg = "🚨 Модель не вернула изображение." + (f"\n\nОтвет: {text_response}" if text_response else "")
            raise Exception(error_msg)

        tasks = [
            send_generated_image(user_id, edited_image_data, f"✏️ Отредактировано с помощью {model_id}", original_message_id)
        ]
        if text_response:
            tasks.append(bot.send_message(user_id, text_response, reply_to_message_id=original_message_id))
        await asyncio.gather(*tasks)

    except Exception as e:
        logging.error(f"Ошибка во время редактирования изображения Gemini: {e}")
        await bot.send_message(user_id, f"🚨 Ошибка при редактировании: {e}", reply_to_message_id=original_message_id)


async def process_image_editing(message: types.Message, state: FSMContext):
    start_time = time.time()
    user_id = message.from_user.id
    original_message_id = message.message_id

    data = await state.get_data()
    image_data = data.get("image_edit_data")
    instructions = data.get("image_edit_instructions")

    if not image_data or not instructions:
        await message.reply("🚨 Не найдены изображение или инструкции.")
        await state.set_state(Form.waiting_for_message)
        return

    model_id, api_type, _, _, user_context = await get_user_settings(user_id)

    if api_type == "poli" and model_id in pollinations_edit_models:
        await edit_image_pollinations(instructions, image_data, model_id, user_id, original_message_id)
    elif api_type == "gemini" and model_id in google_ai_models:
        await edit_image_gemini(instructions, image_data, model_id, user_id, original_message_id)
    else:
        await bot.send_message(
            user_id,
            "🚨 Редактирование поддерживается только моделями Google AI и Pollinations (nanobanana, seedream).",
            reply_to_message_id=original_message_id
        )

    await calculate_and_show_processing_time(message, user_context, start_time)
    await state.set_state(Form.waiting_for_message)
    await state.update_data(image_edit_data=None, image_edit_instructions=None)
