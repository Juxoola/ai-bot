from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp
from database import is_allowed
from func.games import cmd_games
from func.tictactoe import process_tictactoe_callback, TicTacToeGame, game_sessions as ttt_game_sessions, get_game_keyboard, COMPUTER
from func.guess_number import process_guess_callback, GuessNumberGame, game_sessions as guess_game_sessions, get_input_keyboard
import asyncio
import logging

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
    ttt_game_sessions[user_id] = game
    
    keyboard = get_game_keyboard(game)
    
    await callback_query.message.edit_text(
        "🎮 Крестики-нолики\n\n"
        "Вы играете за ❌, я за ⭕.\n"
        "Нажмите на ячейку, чтобы сделать ход.",
        reply_markup=keyboard
    )
    
    await state.set_state(Form.playing_tictactoe)
    
    if game.current_player == COMPUTER:
        # Run the CPU-intensive computer move in a separate thread to avoid blocking
        await asyncio.to_thread(game.computer_move)
        keyboard = get_game_keyboard(game)
        
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


@dp.callback_query(lambda c: c.data and c.data == "game_guess_number")
async def start_guess_number_game(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"Пользователь {user_id} начинает игру 'Угадай число'")
    
    game = GuessNumberGame()
    guess_game_sessions[user_id] = game
    
    # Инициализируем игру в отдельном потоке
    await game.async_reset()
    await state.update_data(current_input="")
    await state.set_state(Form.playing_guess_number)
    
    message_text = (
        "🎮 Угадай число 🎮\n\n"
        f"Я загадал число от {game.min_number} до {game.max_number}.\n"
        f"У вас есть {game.max_attempts} попыток, чтобы угадать его.\n\n"
        "Введите ваше предположение:"
    )
    
    await callback_query.message.edit_text(
        message_text,
        reply_markup=get_input_keyboard()
    )
    
    await callback_query.answer()


@dp.callback_query(Form.playing_guess_number, lambda c: c.data and c.data.startswith("guess_"))
async def guess_number_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await process_guess_callback(callback_query, state)


@dp.callback_query(lambda c: c.data and c.data == "close_games")
async def close_games_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Игры закрыты.")
    await state.set_state(Form.waiting_for_message)
    await callback_query.answer() 