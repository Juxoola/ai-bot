from config import bot, get_client,Form, openai_clients, gemini_client
import config
from aiogram.fsm.context import FSMContext
from database import load_context,def_enhance, def_gen_model, def_aspect
from aiogram import types
import asyncio
import logging
from io import BytesIO
from func.messages import async_run_with_timeout
import aiohttp
from urllib.parse import quote, urlencode
import random
from google.genai import types as genai_types
import time
from PIL import Image
from .messages import DEFAULT_API_TIMEOUT, calculate_and_show_processing_time
import requests
from deep_translator import GoogleTranslator
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
import base64
import os
import config

new_api_models = ["flux", "turbo"]
fresed_models = ["stable-diffusion-3", "stable-diffusion-3-large", "stable-diffusion-3-large-turbo", "flux-pro-1.1", "flux-pro-1"]
google_ai_models = ["gemini-2.0-flash-preview-image-generation"]
pollinations_edit_models = ["nanobanana", "seedream"]


async def process_image_generation_prompt(message: types.Message, state: FSMContext):
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    await set_in_progress(state)
    
    start_time = time.time()

    data = await state.get_data()
    prompt = data.get("image_generation_prompt")
    is_direct_image_gen = data.get("is_direct_image_gen", False)
    
    original_message_id = message.message_id
    await state.update_data(original_message_id=original_message_id)

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
    
    model_info = user_context.get("image_generation_model", DEFAULT_IMAGE_GEN_MODEL)
    
    last_underscore_pos = model_info.rfind('_')
    if last_underscore_pos != -1:
        model_id = model_info[:last_underscore_pos]
        api_type = model_info[last_underscore_pos+1:]
    else:
        model_id = model_info
        api_type = "poli"
    
    aspect_ratio = user_context.get("aspect_ratio", DEFAULT_ASPECT_RATIO)
    enhance = user_context.get("enhance", DEFAULT_ENHANCE)
    
    await state.update_data(image_generation_model=model_id)
    await state.update_data(image_generation_model_api=api_type)
    await state.update_data(aspect_ratio=aspect_ratio)
    await state.update_data(enhance=enhance)

    aspect_ratio_options = {
        "1:1": (2048, 2048),
        "3:2": (1536, 1024),
        "2:3": (1024, 1536),
        "4:3": (1536, 1152),
        "3:4": (1152, 1536),
        "16:9": (1792, 1024),
        "9:16": (1024, 1792),
        "21:9": (2048, 896),
        "9:21": (896, 2048),
        "1:1(2)": (1024, 1024),
        "3:2(2)": (2496, 1664),
        "2:3(2)": (1664, 2496),
        "4:3(2)": (2304, 1856),
        "3:4(2)": (1856, 2304),
        "16:9(2)": (2752, 1536),
        "9:16(2)": (1536, 2752),
        "21:9(2)": (3136, 1344),
        "9:21(2)": (1344, 3136),
    }
    width, height = aspect_ratio_options.get(aspect_ratio, (1024, 1024)) 

    if not enhance:
        try:
            translator = GoogleTranslator(source='auto', target='en')
            translated_prompt = await asyncio.to_thread(translator.translate, prompt)
            
            if translated_prompt and translated_prompt != prompt:
                original_prompt = prompt
                prompt = translated_prompt
                await bot.send_message(
                    user_id, 
                    f"🔔 Ваш запрос был переведен на английский для лучших результатов:\n'{original_prompt}' → '{prompt}'",
                    reply_to_message_id=original_message_id
                )
        except Exception as e:
            logging.error(f"Error during prompt translation: {e}")
            await bot.send_message(
                user_id, 
                f"⚠️ Не удалось перевести запрос на английский: {e}",
                reply_to_message_id=original_message_id
            )

    # Улучшение промпта для всех моделей, если enhance=True
    if enhance:
        try:
            improved_prompt = await config.openai_clients["poli"].chat.completions.create(
                        model="openai-fast",
                        messages=[
                            {"role": "user", "content": f"You are a text prompt generator for creating images. I will give you a post topic, and you will generate one best-quality prompt and show it to me.\n\n{prompt}\n\nDo not ask for clarifications—just generate the best prompt using your creativity, and I will request changes if needed.\n\n### Prompt Structure:\n- Camera angle → Scene description → Character description → Camera settings\n- Character descriptions must always be separated by commas.\n- All parts of the structure must be separated by commas.\n\n### Notes:\n- At the end of the prompt, you may also include the camera type (if it's not a painting style), such as DSLR, Nikon D, Canon EOS R3, etc.\n- You can specify a lens type (e.g., 14mm focal length, 35mm, fisheye, wide-angle, etc.) if necessary.\n\n### Example Formatting:\n- Highly detailed watercolor painting, majestic lion, intricate fur detail, photograph, natural lighting, brush strokes, watercolor splatters\n- Portrait photo of a red-haired girl standing in water covered with lily pads, long braided hair, Canon EOS R3, volumetric lighting\n- Wide-angle, stunning sunset over a wide open beach, vibrant pink-orange and gold sky, water reflecting sunset colors, mesmerizing effect, lone tall tree in foreground, tree silhouetted against sunset, dramatic feel, Canon EOS R3, landscape scene\n- Watercolor painting, family of elephants roaming the savanna, delicate brush strokes, soft colors, Canon EOS R3, wide-angle lens\n\n### IMPORTANT:\nGenerate the best possible prompt immediately in English, and show only the prompt. Do not write anything else."}
                        ],
                    )
            prompt = improved_prompt.choices[0].message.content
        except Exception as e:
            logging.error(f"Error during prompt improvement: {e}")
            await bot.send_message(user_id, f"🚨Ошибка при улучшении промпта: {e}")
    if api_type == "poli":
        async def fetch_image_async():
            if config.http_session is None:
                raise RuntimeError("AIOHTTP session is not initialized. Check on_startup logic.")

            encoded_prompt = quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            params = {
                "width": width, "height": height, "enhance": "false", "model": model_id,
                "seed": random.randint(0, 1000000), "nologo": "true", "private": "true",
                "safe": "false", 
                "token": config.providers_config.get("poli", {}).get("api_key")
            }
            try:
                async with config.http_session.get(url, params=params, timeout=DEFAULT_API_TIMEOUT) as response:
                    response.raise_for_status()
                    return await response.read()
            except Exception as e:
                logging.error(f"Error during image generation request: {e}")
                raise e

        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                image_data = await async_run_with_timeout(fetch_image_async, DEFAULT_API_TIMEOUT)
                
                caption = f"Фото сгенерировано моделью {model_id}"
                if aspect_ratio:
                    caption += f" с соотношением сторон {aspect_ratio}"
                if enhance:
                    caption += f", enhance: {enhance}"
                caption += ":"
                
                await asyncio.gather(
                    bot.send_photo(
                        user_id,
                        photo=types.BufferedInputFile(image_data, filename="image.jpg"),
                        caption=caption,
                        reply_to_message_id=original_message_id
                    ),
                    bot.send_document(
                        user_id, 
                        document=types.BufferedInputFile(image_data, filename="image.jpg"), 
                        caption="Фото без сжатия",
                        reply_to_message_id=original_message_id
                    )
                )
                break
            except Exception as e:
                logging.error(f"Error during image generation (retry {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count == max_retries:
                    await bot.send_message(
                        user_id,
                        "🚨 Не удалось сгенерировать изображение после нескольких попыток. Пожалуйста, попробуйте еще раз.",
                        reply_to_message_id=original_message_id
                    )
                await asyncio.sleep(1)

    elif api_type in openai_clients and api_type != "poli":
        client = openai_clients.get(api_type)
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                size_str = f"{width}x{height}"
                async def generate_openai_content():
                    return await client.images.generate(
                        model=model_id,
                        prompt=prompt,
                        size=size_str,
                        response_format="url"
                    )
                
                response = await async_run_with_timeout(generate_openai_content, DEFAULT_API_TIMEOUT)

                if response is None:
                    raise Exception("Превышено время ожидания при генерации изображения.")
                if hasattr(response, 'generated_images'):
                    image_data = response.generated_images[0].image.getvalue()
                elif hasattr(response, 'data') and response.data:
                    image_url = response.data[0].url
                    if image_url.startswith('data:image/jpeg;base64,'):
                        import base64
                        base64_data = image_url.split('base64,')[1]
                        image_data = base64.b64decode(base64_data)
                    else:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_data = await resp.read()
                                else:
                                    raise Exception(f"Не удалось скачать изображение, статус: {resp.status}")
                else:
                    raise Exception(f"Неподдерживаемый формат ответа от {api_type} client")
                caption = f"Фото сгенерировано {api_type} моделью {model_id}"
                if aspect_ratio:
                    caption += f" с соотношением сторон {aspect_ratio}"
                if enhance:
                    caption += f", enhance: {enhance}"
                caption += ":"

                await asyncio.gather(
                    bot.send_photo(
                        user_id,
                        photo=types.BufferedInputFile(image_data, filename="image.jpg"),
                        caption=caption,
                        reply_to_message_id=original_message_id
                    ),
                    bot.send_document(
                        user_id,
                        document=types.BufferedInputFile(image_data, filename="image.jpg"),
                        caption="Фото без сжатия",
                        reply_to_message_id=original_message_id
                    )
                )
                break
            except Exception as e:
                logging.error(f"Error during {api_type} image generation (retry {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count == max_retries:
                    await bot.send_message(
                        user_id,
                        "🚨 Не удалось сгенерировать изображение после нескольких попыток. Пожалуйста, попробуйте еще раз.",
                        reply_to_message_id=original_message_id
                    )
                await asyncio.sleep(1)

    elif api_type == "gemini":
        if gemini_client:
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    async def generate_gemini_content():
                        return await gemini_client.aio.models.generate_content(
                            model=model_id,
                            contents=prompt,
                            config=genai_types.GenerateContentConfig(
                                response_modalities=['TEXT', 'IMAGE']
                            )
                        )
                    
                    response = await async_run_with_timeout(generate_gemini_content, DEFAULT_API_TIMEOUT)
                    
                    if response is None:
                        raise Exception("Превышено время ожидания при генерации изображения.")
                    
                    image_data = None
                    text_response = ""
                    
                    for part in response.candidates[0].content.parts:
                        if part.text is not None:
                            text_response += part.text
                        
                        elif part.inline_data is not None and part.inline_data.mime_type.startswith('image/'):
                            image = await asyncio.to_thread(
                                lambda: Image.open(BytesIO(part.inline_data.data))
                            )
                            img_byte_arr = BytesIO()
                            await asyncio.to_thread(
                                lambda: image.save(img_byte_arr, format='JPEG')
                            )
                            image_data = img_byte_arr.getvalue()
                    
                    if not image_data:
                        error_message = "🚨Модель не сгенерировала изображение в ответе."
                        if text_response:
                            error_message += f"\n\nОтвет модели: {text_response}"
                        raise Exception(error_message)

                    caption = f"Фото сгенерировано моделью {model_id}"
                    if enhance:
                        caption += f", enhance: {enhance}"
                    caption += ":"
                    
                    await asyncio.gather(
                    bot.send_photo(
                        user_id,
                        photo=types.BufferedInputFile(image_data, filename="image.jpg"),
                        caption=caption,
                        reply_to_message_id=original_message_id
                    ),
                    bot.send_document(
                        user_id,
                        document=types.BufferedInputFile(image_data, filename="image.jpg"),
                        caption="Фото без сжатия",
                        reply_to_message_id=original_message_id
                    )
                    )
                    break
                except Exception as e:
                    logging.error(f"Error during Gemini image generation (retry {retry_count + 1}/{max_retries}): {e}")
                    retry_count += 1
                    if retry_count == max_retries:
                        await bot.send_message(
                            user_id,
                            "🚨 Не удалось сгенерировать изображение после нескольких попыток. Пожалуйста, попробуйте еще раз.",
                            reply_to_message_id=original_message_id
                        )
                    await asyncio.sleep(1)
        else:
            await bot.send_message(
                user_id,
                "🚨Генерация изображений через Gemini недоступна. API-ключ не настроен.",
                reply_to_message_id=original_message_id
            )

    elif api_type == "g4f":
        image_gen_client = await get_client(user_id, "g4f_image_gen_client", model_name=model_id)
    
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                async def generate_g4f_content():
                    return await image_gen_client.images.generate(
                        prompt=prompt,
                        model=model_id,
                        response_format="url",
                        enhance=False,
                        private=True,
                        width=width,
                        height=height,
                    )
                
                response = await async_run_with_timeout(generate_g4f_content, DEFAULT_API_TIMEOUT)
                
                if response is None:
                    raise Exception("Превышено время ожидания при генерации изображения.")
                
                image_url = response.data[0].url
                caption = f"Фото сгенерировано моделью {model_id}"
                if aspect_ratio:
                    caption += f" с соотношением сторон {aspect_ratio}"
                if enhance:
                    caption += f", enhance: {enhance}"
                caption += ":"
                await bot.send_photo(
                    user_id,
                    photo=image_url,
                    caption=caption,
                    reply_to_message_id=original_message_id
                )
                caption2 = "Фото без сжатия"
                await bot.send_document(
                    user_id,
                    document=image_url,
                    caption=caption2,
                    reply_to_message_id=original_message_id
                )
                break
            except Exception as e:
                logging.error(f"Error during image generation (retry {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count == max_retries:
                    await bot.send_message(
                        user_id,
                        "🚨 Не удалось сгенерировать изображение после нескольких попыток. Пожалуйста, попробуйте еще раз.",
                        reply_to_message_id=original_message_id
                    )
                await asyncio.sleep(1)


    await calculate_and_show_processing_time(message, user_context, start_time)
    
    await clear_in_progress(state)
    await state.set_state(Form.waiting_for_message)
    await state.update_data(image_generation_prompt=None)
    await state.update_data(aspect_ratio=None)
    await state.update_data(enhance=None)
    await state.update_data(original_message_id=None)

IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "key")

async def process_image_editing(message: types.Message, state: FSMContext):
    await set_in_progress(state) 
    
    start_time = time.time()
    user_id = message.from_user.id
    
    data = await state.get_data()
    image_data = data.get("image_edit_data")
    instructions = data.get("image_edit_instructions")
    
    original_message_id = message.message_id
    
    if not image_data or not instructions:
        await message.reply("🚨 Не удалось получить данные изображения или инструкции по редактированию")
        await state.set_state(Form.waiting_for_message)
        return

    user_context = await load_context(user_id)
    model_info = user_context.get("image_generation_model")
    
    if isinstance(model_info, dict):
        model_id = model_info.get("model_id")
        api_type = model_info.get("api")
    else:
        last_underscore_pos = model_info.rfind('_')
        if last_underscore_pos != -1:
            model_id = model_info[:last_underscore_pos]
            api_type = model_info[last_underscore_pos+1:]
        else:
            model_id = model_info
            api_type = "poli"

    if api_type == "poli" and model_id in pollinations_edit_models:
        try:
            async def upload_to_imgbb_async(image_bytes: bytes) -> str:
                if not IMGBB_API_KEY or IMGBB_API_KEY == "key": 
                    raise ValueError("API-ключ для ImgBB не указан или используется значение по умолчанию.")
                
                url = "https://api.imgbb.com/1/upload"

                data = aiohttp.FormData()
                data.add_field('key', IMGBB_API_KEY)
                data.add_field('image', image_bytes, filename='image.jpg', content_type='image/jpeg')

                if config.http_session is None:
                    raise RuntimeError("AIOHTTP session is not initialized.")
                
                try:
                    async with config.http_session.post(url, data=data, timeout=30) as response:
                        response_json = await response.json()
                        if response.status == 200 and response_json.get('success'):
                            return response_json['data']['url']
                        else:
                            error_message = response_json.get('error', {}).get('message', 'Неизвестная ошибка')
                            raise Exception(f"API ImgBB вернуло ошибку: {response.status}, {error_message}")
                except aiohttp.ClientError as e:
                    logging.error(f"Сетевая ошибка при загрузке на ImgBB: {e}")
                    raise Exception(f"Сетевая ошибка при загрузке на ImgBB: {e}")
                except Exception as e:
                    logging.error(f"Произошла ошибка в функции upload_to_imgbb: {e}")
                    raise
                

            if isinstance(image_data, list):
                image_data = image_data[0]

            if hasattr(image_data, 'read'):
                image_bytes = image_data.read()
            else:
                image_bytes = image_data

            image_url = await upload_to_imgbb_async(image_bytes)

            with Image.open(BytesIO(image_bytes)) as img:
                width, height = img.size
                if width * height < 921600:
                    logging.info(f"Image is too small ({width}x{height}={width*height} pixels). Resizing...")
                    scale_factor = (921600 / (width * height)) ** 0.5 * 1.01
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)

                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    logging.info(f"Image resized to {new_width}x{new_height}={new_width*new_height} pixels.")
                    
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG")
                    image_bytes = buffer.getvalue()
                    width, height = new_width, new_height


            encoded_prompt = quote(instructions)
            base_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            params = {
                "model": model_id,
                "image": image_url,
                "width": width,
                "height": height,
                "nologo": "true",
                "private": "true",
                "safe": "false",
                "token": config.providers_config.get("poli", {}).get("api_key")
            }
            
            query_string = urlencode(params)
            full_url = f"{base_url}?{query_string}"
            logging.info(f"Запрос к Pollinations: {full_url}")

            async def fetch_edited_image_async():
                try:
                    async with config.http_session.get(full_url, timeout=DEFAULT_API_TIMEOUT) as response:
                        response.raise_for_status()
                        return await response.read()
                except Exception as e:
                    logging.error(f"Error during pollinations image editing: {e}")
                    raise e

            edited_image_data = await async_run_with_timeout(fetch_edited_image_async, DEFAULT_API_TIMEOUT)

            if not edited_image_data:
                raise Exception("Не удалось получить отредактированное изображение от Pollinations.")

            
            await asyncio.gather(
                bot.send_photo(
                    user_id,
                    photo=types.BufferedInputFile(edited_image_data, filename="edited_image.jpg"),
                    caption=f"✏️ Изображение отредактировано с помощью {model_id}",
                    reply_to_message_id=original_message_id
                ),
                bot.send_document(
                    user_id,
                    document=types.BufferedInputFile(edited_image_data, filename="edited_image.jpg"),
                    caption="Отредактированное изображение без сжатия",
                    reply_to_message_id=original_message_id
                )
            )


        except Exception as e:
            logging.error(f"Error during Pollinations image editing: {e}")
            await bot.send_message(user_id, f"🚨 Ошибка при редактировании изображения: {e}", reply_to_message_id=original_message_id)

    elif api_type == "gemini" and model_id in google_ai_models:
        try:
            if isinstance(image_data, list):
                pil_images = []
                for img in image_data:
                    if hasattr(img, 'read'):
                        image_bytes = BytesIO(img.read())
                    else:
                        image_bytes = BytesIO(img)
                    image_bytes.seek(0)
                    pil_img = await asyncio.to_thread(lambda: Image.open(image_bytes))
                    pil_images.append(pil_img)
            else:
                image_bytes = BytesIO(image_data.read())
                image_bytes.seek(0)
                pil_img = await asyncio.to_thread(lambda: Image.open(image_bytes))
                pil_images = [pil_img]

            try:
                translator = GoogleTranslator(source='auto', target='en')
                
                translated_prompt = await asyncio.to_thread(translator.translate(instructions))
                
                if translated_prompt and translated_prompt != instructions:
                    original_prompt = instructions
                    instructions = translated_prompt
                    await bot.send_message(
                        user_id,
                        f"🔔 Ваш запрос был переведен на английский для лучших результатов:\n'{original_prompt}' → '{instructions}'",
                        reply_to_message_id=original_message_id
                    )
            except Exception as e:
                logging.error(f"Error during prompt translation: {e}")
                await bot.send_message(
                    user_id,
                    f"⚠️ Не удалось перевести запрос на английский: {e}",
                    reply_to_message_id=original_message_id
                )
    
            contents = [instructions, *pil_images]

            async def generate_gemini_content():
                return gemini_client.aio.models.generate_content(
                    model=model_id,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
            
            response = await async_run_with_timeout(generate_gemini_content, DEFAULT_API_TIMEOUT)
            
            if response is None:
                await bot.send_message(
                    user_id,
                    "🚨 Превышено время ожидания при редактировании изображения. Пожалуйста, попробуйте еще раз.",
                    reply_to_message_id=original_message_id
                )
                await state.set_state(Form.waiting_for_message)
                return
            
            edited_image_data = None
            text_response = ""
            
            if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'content'):
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text is not None:
                        text_response += part.text
                    
                    elif hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type.startswith('image/'):
                        image = await asyncio.to_thread(
                            lambda: Image.open(BytesIO(part.inline_data.data))
                        )
                        img_byte_arr = BytesIO()
                        await asyncio.to_thread(
                            lambda: image.save(img_byte_arr, format='JPEG')
                        )
                        edited_image_data = img_byte_arr.getvalue()
            
            if not edited_image_data:
                error_message = "🚨 Модель не сгенерировала отредактированное изображение в ответе."
                if text_response:
                    error_message += "\n\nОтвет модели: " + text_response[:3000]
                await bot.send_message(
                    user_id,
                    error_message,
                    reply_to_message_id=original_message_id
                )
                await state.set_state(Form.waiting_for_message)
                return
            
            tasks = [
                bot.send_photo(
                    user_id,
                    photo=types.BufferedInputFile(edited_image_data, filename="edited_image.jpg"),
                    caption=f"✏️ Изображение отредактировано с помощью {model_id}",
                    reply_to_message_id=original_message_id
                ),
                bot.send_document(
                    user_id,
                    document=types.BufferedInputFile(edited_image_data, filename="edited_image.jpg"),
                    caption="Отредактированное изображение без сжатия",
                    reply_to_message_id=original_message_id
                )
            ]

            if text_response:
                tasks.append(bot.send_message(user_id, text_response, reply_to_message_id=original_message_id))
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logging.error(f"Error during image editing: {e}")
            error_message = f"🚨 Ошибка при редактировании изображения: {str(e)[:200]}"
            await bot.send_message(
                user_id,
                error_message,
                reply_to_message_id=original_message_id
            )
    else:
        await bot.send_message(
            user_id,
            "🚨 Редактирование изображений поддерживается только моделями Google AI и Pollinations (nanobanana, seedream). Пожалуйста, измените модель в настройках.",
            reply_to_message_id=original_message_id
        )
    
    await calculate_and_show_processing_time(message, user_context, start_time)
    
    await clear_in_progress(state)
    await state.set_state(Form.waiting_for_message)
    await state.update_data(image_edit_data=None)
    await state.update_data(image_edit_instructions=None)
