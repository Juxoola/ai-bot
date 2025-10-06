import asyncio
import logging

import httpx
from aiogram import F, types

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

MAX_RETRIES = 3
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from config import Form, bot, dp
from database import (av_models, is_admin, load_context, rec_models,
                      save_context)
from func.decorators import access_required
from func.guess_number import game_sessions as guess_game_sessions
from func.tictactoe import game_sessions as ttt_game_sessions
from handlers.check import clear_in_progress, exit_game
from handlers.rate_limit import check_rate_limit
from keyboards import get_main_keyboard


@dp.message(Command("start"))
@access_required
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not await check_rate_limit(message, "start"):
        return

    user_context = await load_context(user_id)
    
    await save_context(user_id, user_context)

    if is_admin(user_id):
        await message.reply(
            "Привет, админ! Я чат-бот, который может использовать различные ИИ-модели.\n"
            "Используйте /help, чтобы увидеть доступные команды.\n"
            "Если клавиатура пропала, используйте /keyboard для её восстановления.",
            reply_markup=await get_main_keyboard(include_admin_button=True)
        )
    else:
        await message.reply(
            "Привет! Я чат-бот, который может использовать различные ИИ-модели.\n"
            "Используйте /help, чтобы увидеть доступные команды.\n"
            "Если клавиатура пропала, используйте /keyboard для её восстановления.",
            reply_markup=await get_main_keyboard(include_admin_button=False)
        )

    await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "ℹ️ Помощь")
@dp.message(F.text == "/help")
@access_required
async def cmd_help(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "help"):
        return


    AVAILABLE_MODELS = await av_models()
    REC_MODELS = await rec_models()
    
    help_text = (
        "Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать это справочное сообщение\n"
        "/settings - Открыть меню настроек\n"
        "/clear - Очистить контекст беседы\n"
        "/generate_image - Сгенерировать изображение\n"
        "/audio - Отправить аудио для транскрипции (Whisper)\n"
        "/search - Выполнить поиск в интернете\n"
        "/long_message - Режим накопления сообщений\n"
        "/keyboard - Восстановить клавиатуру, если она исчезла\n"
        "/meme - Получить случайный мем\n"
        "/games - Открыть меню игр\n"
        "Также можно присылать документы и изображения\n"
    )
    
    await message.reply(help_text)
    
    rec_models_by_api = {}
    for model_key, model_data in REC_MODELS.items():
        api = model_data["api"]
        if api not in rec_models_by_api:
            rec_models_by_api[api] = []
        
        model_id = model_data["model_id"]
        display_name = None
        lookup_key = f"{model_id}_{api}"
        
        if lookup_key in AVAILABLE_MODELS:
            display_name = AVAILABLE_MODELS[lookup_key]["model_name"]
        else:
            display_name = model_id
            
        rec_models_by_api[api].append(display_name)
    
    if rec_models_by_api:
        models_text = "📷 Доступные модели для распознавания изображений:\n\n"
        for api, models in rec_models_by_api.items():
            models_text += f"API: {api.upper()}\n"
            models_text += "• " + "\n• ".join(models) + "\n\n"
        
        await message.answer(models_text)

    if is_admin(message.from_user.id):
        await message.answer(
            "Команды администратора:\n"
            "/add_model - Добавить новую модель для чата\n"
            "/delete_model - Удалить существующую модель для чата\n"
            "/add_image_gen_model - Добавить новую модель для генерации изображений\n"
            "/delete_image_gen_model - Удалить существующую модель для генерации изображений\n"
            "/add_image_rec_model - Добавить новую модель для распознавания изображений\n"
            "/delete_image_rec_model - Удалить существующую модель для распознавания изображений\n"
            "/add_user - Добавить пользователя\n"
            "/remove_user - Удалить пользователя\n"
            "/send_to_all - Отправить сообщение всем пользователям\n"
            "/send_to_user - Отправить сообщение конкретному пользователю\n"
        )


@dp.message(F.text == "⌨️ Вернуть клавиатуру")
@dp.message(F.text == "/keyboard")
@access_required
async def cmd_restore_keyboard(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "keyboard"):
        return
    
    user_id = message.from_user.id
    if is_admin(user_id):
        await message.reply(
            "Клавиатура восстановлена. Используйте кнопки для взаимодействия с ботом.",
            reply_markup=await get_main_keyboard(include_admin_button=True)
        )
    else:
        await message.reply(
            "Клавиатура восстановлена. Используйте кнопки для взаимодействия с ботом.",
            reply_markup=await get_main_keyboard(include_admin_button=False)
        )


async def fetch_random_meme():
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://meme-api.com/gimme")
                response.raise_for_status()
                data = response.json()
                
                if "url" in data and data["url"]:
                    return {
                        "url": data["url"],
                        "title": data.get("title", "Random Meme"),
                        "source": f"https://reddit.com{data.get('postLink', '')}"
                    }
                else:
                    logger.error(f"Attempt {attempt + 1}: Meme API response missing 'url' or 'url' is empty. Data: {data}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Attempt {attempt + 1}: HTTP error fetching from meme-api.com: {e}")
        except httpx.RequestError as e:
            logger.error(f"Attempt {attempt + 1}: Request error fetching from meme-api.com: {e}")
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Unexpected error fetching from meme-api.com: {e}")
        
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(1) 
    return None


@dp.message(F.text == "🎭 Мем")
@dp.message(F.text == "/meme")
@access_required
async def cmd_random_meme(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "meme"):
        return
    
    processing_message = await message.reply("Ищу смешной мем...")
    
    meme = await fetch_random_meme()
    
    if meme:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=meme["url"],
            caption=f"{meme['title']}"
        )
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
    else:
        await processing_message.edit_text("Не удалось найти мем. Попробуйте еще раз.")
        
    current_state = await state.get_state()
    if current_state != Form.waiting_for_message:
        await state.set_state(Form.waiting_for_message)


@dp.message(F.text == "/cancel")
@access_required
async def cmd_cancel(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "cancel"):
        return
    
    current_state = await state.get_state()
    
    if current_state in [Form.playing_tictactoe, Form.playing_guess_number]:
        user_id = message.from_user.id
        
        if current_state == Form.playing_tictactoe and user_id in ttt_game_sessions:
            del ttt_game_sessions[user_id]
        elif current_state == Form.playing_guess_number and user_id in guess_game_sessions:
            del guess_game_sessions[user_id]
            
        await exit_game(state)
        await message.reply("✅ Вы вышли из игры. Можете продолжать общение.")
    else:
        await clear_in_progress(state)
        await state.set_state(Form.waiting_for_message)
        await message.reply("✅ Текущая операция отменена. Можете продолжать общение.")