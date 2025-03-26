
from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp
from database import is_allowed
from func.search import process_search_query
from func.messages import handle_long_message, cmd_long_message

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(F.text == "🌐 Поиск")
@dp.message(F.text == "/search")
async def cmd_search(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
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
    await process_search_query(message, state)


@dp.message(F.text == "📝 Длинное сообщение")
@dp.message(F.text == "/long_message")
async def cmd_long_message_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await cmd_long_message(message, state)


@dp.message(Form.waiting_for_long_message)
async def handle_long_message_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    await handle_long_message(message, state) 