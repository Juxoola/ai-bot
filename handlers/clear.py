import logging

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from config import dp
from database import reset_user_context
from func.decorators import access_required
from handlers.check import (check_in_progress, clear_in_progress,
                            set_in_progress)
from handlers.rate_limit import check_rate_limit


@dp.message(F.text == "🗑️ Очистить")
@dp.message(F.text == "Очистить")
@dp.message(F.text == "/clear")
@access_required
async def cmd_clear_context(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "clear"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return

    try:
        await set_in_progress(state)
        
        user_id = message.from_user.id
        
        await reset_user_context(user_id)
        
        await message.reply("Контекст очищен.")
        
    except Exception as e:
        logging.error(f"Произошла ошибка при очистке контекста для user_id {message.from_user.id}: {e}")
        await message.reply(f"🔔 Произошла ошибка при очистке контекста.")
    finally:
        await clear_in_progress(state)