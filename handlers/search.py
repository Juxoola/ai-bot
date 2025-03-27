from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp
from database import is_allowed
from func.search import process_search_query
from func.messages import handle_long_message, cmd_long_message
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
from handlers.rate_limit import check_rate_limit

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(F.text == "🌐 Поиск")
@dp.message(F.text == "/search")
async def cmd_search(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
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
async def process_search_query_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    if not await check_rate_limit(message, "process_search"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
        
    try:
        await set_in_progress(state)
        await process_search_query(message, state)
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await message.reply(f"🔔Произошла ошибка при выполнении поискового запроса: {e}")


@dp.message(F.text == "📝 Длинное сообщение")
@dp.message(F.text == "/long_message")
async def cmd_long_message_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    if not await check_rate_limit(message, "long_message"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    await cmd_long_message(message, state)


@dp.message(Form.waiting_for_long_message)
async def handle_long_message_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    if not await check_rate_limit(message, "handle_long_message"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
        
    try:
        await set_in_progress(state)
        await handle_long_message(message, state)
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await message.reply(f"🔔Произошла ошибка при обработке длинного сообщения: {e}") 