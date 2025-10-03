from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp
from func.games import cmd_games
from func.tictactoe import process_tictactoe_callback, TicTacToeGame, game_sessions as ttt_game_sessions, get_game_keyboard, COMPUTER
from func.guess_number import process_guess_callback, GuessNumberGame, game_sessions as guess_game_sessions, get_input_keyboard
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
from handlers.rate_limit import check_rate_limit, check_callback_rate_limit
import asyncio
import logging
from func.decorators import access_required

@dp.message(F.text == "🎮 Игры")
@dp.message(F.text == "/games")
@access_required
async def cmd_games_handler(message: types.Message, state: FSMContext):
    # Проверяем rate limit
    if not await check_rate_limit(message, "games"):
        return
    
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return
    
    await cmd_games(message, state)


@dp.callback_query(lambda c: c.data and c.data == "game_tictactoe")
async def start_tictactoe_game(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    if not await check_callback_rate_limit(callback_query, "tictactoe_start"):
        return
    
    # Проверяем, не находится ли пользователь в процессе выполнения операции
    message = callback_query.message
    mock_message = types.Message(
        message_id=message.message_id,
        date=message.date,
        chat=message.chat,
        from_user=callback_query.from_user,
        content_type="text",
        text="/game_tictactoe"
    )
    can_proceed = await check_in_progress(mock_message, state)
    if not can_proceed:
        await callback_query.answer("⏳ Дождитесь завершения текущей операции или используйте /cancel")
        return
    
    try:
        # Устанавливаем состояние in_progress перед операцией
        await set_in_progress(state)
        
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
            await asyncio.to_thread(game.computer_move)
            keyboard = get_game_keyboard(game)
            
            await callback_query.message.edit_text(
                "🎮 Крестики-нолики\n\n"
                "Вы играете за ❌, я за ⭕.\n"
                "Я сделал ход. Ваша очередь!",
                reply_markup=keyboard
            )
        
        await callback_query.answer()
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await callback_query.message.reply(f"🔔 Произошла ошибка при запуске игры: {e}")
        await callback_query.answer()


@dp.callback_query(lambda c: c.data and (c.data.startswith("ttt_") or c.data == "ttt_restart" or c.data == "ttt_exit"))
async def tictactoe_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):

    try:
        await process_tictactoe_callback(callback_query, state)
    except Exception as e:
        await state.set_state(Form.waiting_for_message)
        await callback_query.message.reply(f"🔔 Произошла ошибка в игре: {e}")
        await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data == "game_guess_number")
async def start_guess_number_game(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"Пользователь {user_id} начинает игру 'Угадай число'")
    
    if not await check_callback_rate_limit(callback_query, "guess_number_start"):
        return
    
    message = callback_query.message
    mock_message = types.Message(
        message_id=message.message_id,
        date=message.date,
        chat=message.chat,
        from_user=callback_query.from_user,
        content_type="text",
        text="/game_guess_number"
    )
    can_proceed = await check_in_progress(mock_message, state)
    if not can_proceed:
        await callback_query.answer("⏳ Дождитесь завершения текущей операции или используйте /cancel")
        return
    
    try:
        await set_in_progress(state)
        
        game = GuessNumberGame()
        guess_game_sessions[user_id] = game
        
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
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await callback_query.message.reply(f"🔔 Произошла ошибка при запуске игры: {e}")
        await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith("guess_"))
async def guess_number_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await process_guess_callback(callback_query, state)
    except Exception as e:
        await state.set_state(Form.waiting_for_message)
        await callback_query.message.reply(f"🔔 Произошла ошибка в игре: {e}")
        await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data == "close_games")
async def close_games_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not await check_callback_rate_limit(callback_query, "close_games"):
        return
        
    await callback_query.message.edit_text("Игры закрыты.")
    await state.set_state(Form.waiting_for_message)
    await callback_query.answer() 