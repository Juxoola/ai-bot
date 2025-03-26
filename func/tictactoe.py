from aiogram import types
from aiogram.fsm.context import FSMContext
import random
from config import Form
import asyncio
import json
import logging

# Константы для игры
EMPTY = "⬜️"
PLAYER = "❌"
COMPUTER = "⭕️"
WINNING_COMBINATIONS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],  # горизонтальные линии
    [0, 3, 6], [1, 4, 7], [2, 5, 8],  # вертикальные линии
    [0, 4, 8], [2, 4, 6]              # диагональные линии
]

class TicTacToeGame:
    def __init__(self):
        self.board = [EMPTY] * 9
        self.current_player = PLAYER
        self.game_over = False
        self.winner = None
    
    def reset(self):
        self.board = [EMPTY] * 9
        self.current_player = PLAYER 
        self.game_over = False
        self.winner = None
    
    def make_move(self, position):
        if self.game_over or position < 0 or position >= 9 or self.board[position] != EMPTY:
            return False
        
        self.board[position] = self.current_player
        self.check_winner()
                
        return True
    
    def check_winner(self):
        # Проверка на выигрышные комбинации
        for combo in WINNING_COMBINATIONS:
            if self.board[combo[0]] != EMPTY and self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]]:
                self.game_over = True
                self.winner = self.current_player
                return
        
        # Проверка на ничью
        if EMPTY not in self.board:
            self.game_over = True
            self.winner = None
    
    def computer_move(self):
        if self.game_over:
            return False
        
        saved_player = self.current_player
        self.current_player = COMPUTER
        
        # 1. Проверка, может ли компьютер выиграть за один ход
        for i in range(9):
            if self.board[i] == EMPTY:
                self.board[i] = COMPUTER
                if self.is_winner(COMPUTER):
                    self.check_winner()
                    return True
                self.board[i] = EMPTY
        
        # 2. Блокировка хода игрока, если он может выиграть в следующем ходу
        for i in range(9):
            if self.board[i] == EMPTY:
                self.board[i] = PLAYER
                if self.is_winner(PLAYER):
                    self.board[i] = COMPUTER
                    self.check_winner()
                    return True
                self.board[i] = EMPTY
        
        # 3. Стратегические ходы
        # Центр
        if self.board[4] == EMPTY:
            self.board[4] = COMPUTER
            self.check_winner()
            return True
        
        # Углы
        corners = [0, 2, 6, 8]
        random.shuffle(corners)
        for corner in corners:
            if self.board[corner] == EMPTY:
                self.board[corner] = COMPUTER
                self.check_winner()
                return True
        
        # Стороны
        sides = [1, 3, 5, 7]
        random.shuffle(sides)
        for side in sides:
            if self.board[side] == EMPTY:
                self.board[side] = COMPUTER
                self.check_winner()
                return True
        
        if not self.game_over:
            self.current_player = saved_player
            
        return False
    
    def is_winner(self, player):
        for combo in WINNING_COMBINATIONS:
            if self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] == player:
                return True
        return False
    
    def get_board_message(self):
        board_str = ""
        for i in range(0, 9, 3):
            board_str += "".join(self.board[i:i+3]) + "\n"
        
        return board_str.strip()

game_sessions = {}

def get_game_keyboard(game_state):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    for row in range(3):
        buttons_row = []
        for col in range(3):
            position = row * 3 + col
            
            if game_state.board[position] == EMPTY and not game_state.game_over:
                callback_data = f"ttt_{position}"
                button = types.InlineKeyboardButton(text=EMPTY, callback_data=callback_data)
            else:
                button = types.InlineKeyboardButton(text=game_state.board[position], callback_data=f"ignore_{position}")
            
            buttons_row.append(button)
        
        keyboard.inline_keyboard.append(buttons_row)
    
    restart_button = types.InlineKeyboardButton(text="🔄 Новая игра", callback_data="ttt_restart")
    exit_button = types.InlineKeyboardButton(text="🚪 Выход", callback_data="ttt_exit")
    keyboard.inline_keyboard.append([restart_button, exit_button])
    
    return keyboard

# Команда для начала игры
async def cmd_tictactoe(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    game_sessions[user_id] = TicTacToeGame()
    game = game_sessions[user_id]
    
    keyboard = get_game_keyboard(game)
    
    await message.reply(
        "🎮 *Крестики-нолики* 🎮\n\n"
        "Вы играете за ❌. Сделайте свой ход, нажав на клетку.\n\n"
        f"{game.get_board_message()}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(Form.playing_tictactoe)

# Обработчик нажатий кнопок в игре
async def process_tictactoe_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    current_state = await state.get_state()
    logging_text = f"TicTacToe callback от пользователя {user_id}, data={data}, состояние={current_state}"
    print(logging_text)
    logging.info(logging_text)
    
    if user_id not in game_sessions:
        logging.warning(f"Игровая сессия для пользователя {user_id} не найдена, создаем новую")
        game_sessions[user_id] = TicTacToeGame()
    
    game = game_sessions[user_id]
    
    if data == "ttt_restart":
        game.reset()
        keyboard = get_game_keyboard(game)
        
        await callback_query.message.edit_text(
            "🎮 *Крестики-нолики* 🎮\n\n"
            "Вы играете за ❌. Сделайте свой ход, нажав на клетку.\n\n"
            f"{game.get_board_message()}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    elif data == "ttt_exit":
        await callback_query.message.edit_text(
            "Игра в крестики-нолики завершена. Спасибо за игру!",
            reply_markup=None
        )
        del game_sessions[user_id]
        await state.set_state(Form.waiting_for_message)
    elif data.startswith("ttt_") and not data == "ttt_restart":
        position = int(data.split("_")[1])
        
        
        if not game.game_over and game.board[position] == EMPTY:
            game.board[position] = PLAYER
            game.check_winner()
                        
            message_text = "🎮 *Крестики-нолики* 🎮\n\n"
            
            if game.game_over:
                if game.winner == PLAYER:
                    message_text += "🎉 Поздравляем! Вы выиграли! 🎉\n\n"
                else:
                    message_text += "🤝 Ничья! 🤝\n\n"
            else:
                await asyncio.sleep(0.1) 
                game.computer_move()  
                
                
                if game.game_over:
                    if game.winner == COMPUTER:
                        message_text += "😔 Компьютер выиграл! 😔\n\n"
                    else:
                        message_text += "🤝 Ничья! 🤝\n\n"
                else:
                    message_text += "Вы играете за ❌. Сделайте свой ход, нажав на клетку.\n\n"
            
            message_text += game.get_board_message()
            keyboard = get_game_keyboard(game)
            
            await callback_query.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    await callback_query.answer() 