from aiogram import types
from aiogram.fsm.context import FSMContext


async def get_games_keyboard():
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎮 Крестики-нолики", callback_data="game_tictactoe")],
        [types.InlineKeyboardButton(text="🎯 Угадай число", callback_data="game_guess_number")],
        [types.InlineKeyboardButton(text="🚪 Закрыть", callback_data="close_games")]
    ])
    return keyboard

async def cmd_games(message: types.Message, state: FSMContext):
    keyboard = await get_games_keyboard()
    
    await message.reply(
        "🎮 Игры 🎮\n\n"
        "Выберите игру, в которую хотите поиграть:",
        reply_markup=keyboard
    )

async def process_game_selection(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    
    if data == "close_games":
        await callback_query.message.edit_text(
            "Меню игр закрыто.",
            reply_markup=None
        )
    
    await callback_query.answer() 