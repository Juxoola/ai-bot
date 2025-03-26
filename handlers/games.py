from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp
from database import is_allowed
from func.games import cmd_games
from func.tictactoe import process_tictactoe_callback, TicTacToeGame, game_sessions, get_game_keyboard

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(F.text == "🎮 Игры")
@dp.message(F.text == "/games")
async def cmd_games_handler(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return
    
    await cmd_games(message, state)


@dp.callback_query(lambda c: c.data and c.data == "game_tictactoe")
async def start_tictactoe_game(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    game = TicTacToeGame()
    game_sessions[user_id] = game
    
    keyboard = await get_game_keyboard(game.board)
    
    await callback_query.message.edit_text(
        "🎮 Крестики-нолики\n\n"
        "Вы играете за ❌, я за ⭕.\n"
        "Нажмите на ячейку, чтобы сделать ход.",
        reply_markup=keyboard
    )
    
    await state.set_state(Form.playing_tictactoe)
    
    if game.current_player == "O":
        ai_move = game.ai_make_move()
        keyboard = await get_game_keyboard(game.board)
        
        await callback_query.message.edit_text(
            "🎮 Крестики-нолики\n\n"
            "Вы играете за ❌, я за ⭕.\n"
            "Я сделал ход. Ваша очередь!",
            reply_markup=keyboard
        )
    
    await callback_query.answer()


@dp.callback_query(Form.playing_tictactoe, lambda c: c.data and (c.data.startswith("ttt_") or c.data == "ttt_restart" or c.data == "ttt_exit"))
async def tictactoe_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_tictactoe_callback(callback_query, state)


@dp.callback_query(lambda c: c.data and c.data == "close_games")
async def close_games_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Игры закрыты.")
    await state.set_state(Form.waiting_for_message)
    await callback_query.answer() 