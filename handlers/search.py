from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp
from func.search import process_search_query
from func.messages import handle_long_message, cmd_long_message
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
from handlers.rate_limit import check_rate_limit
from func.decorators import access_required

@dp.message(F.text == "🌐 Поиск")
@dp.message(F.text == "/search")
@access_required
async def cmd_search(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "search"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    await message.reply(
        "Пожалуйста, введите поисковый запрос для поиска в интернете."
    )
    
    await state.set_state(Form.waiting_for_search_query)


@dp.message(Form.waiting_for_search_query)
@access_required
async def process_search_query_handler(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "process_search"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
        
    try:
        await set_in_progress(state, message)
        await process_search_query(message, state)
        await clear_in_progress(state, message)
    except Exception as e:
        await clear_in_progress(state, message)
        await message.reply(f"🔔Произошла ошибка при выполнении поискового запроса: {e}")


@dp.message(F.text == "📝 Длинное сообщение")
@dp.message(F.text == "/long_message")
@access_required
async def cmd_long_message_handler(message: types.Message, state: FSMContext):
    if not await check_rate_limit(message, "long_message"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    await cmd_long_message(message, state)


@dp.message(Form.waiting_for_long_message)
@access_required
async def handle_long_message_handler(message: types.Message, state: FSMContext):
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
        
    try:
        await set_in_progress(state, message)
        await handle_long_message(message, state)
        await clear_in_progress(state, message)
    except Exception as e:
        await clear_in_progress(state, message)
        await message.reply(f"🔔Произошла ошибка при обработке длинного сообщения: {e}")