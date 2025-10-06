import asyncio
import logging
import random

from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Form


class GuessNumberGame:
    def __init__(self, min_number=1, max_number=100, max_attempts=8):
        self.min_number = min_number
        self.max_number = max_number
        self.max_attempts = max_attempts
        self.reset()
    
    def reset(self):
        self.secret_number = random.randint(self.min_number, self.max_number)
        self.attempts = 0
        self.game_over = False
        self.won = False
        self.guesses = []
    
    def make_guess(self, number):
        if self.game_over:
            return False
        
        self.attempts += 1
        self.guesses.append(number)
        
        if number == self.secret_number:
            self.game_over = True
            self.won = True
            return True
        
        if self.attempts >= self.max_attempts:
            self.game_over = True
            return False
        
        return False
    
    def get_hint(self, number):
        if number < self.secret_number:
            return "больше"
        elif number > self.secret_number:
            return "меньше"
        else:
            return "угадал"
    
    def get_attempts_left(self):
        return self.max_attempts - self.attempts

    def get_previous_guesses(self):
        return ", ".join(map(str, self.guesses))

    async def async_reset(self):
        await asyncio.to_thread(self._thread_safe_reset)
        
    def _thread_safe_reset(self):
        self.secret_number = random.randint(self.min_number, self.max_number)
        self.attempts = 0
        self.game_over = False
        self.won = False
        self.guesses = []
    
    async def async_make_guess(self, number):
        return await asyncio.to_thread(self._thread_safe_make_guess, number)
    
    def _thread_safe_make_guess(self, number):
        if self.game_over:
            return False, None
        
        self.attempts += 1
        self.guesses.append(number)
        
        hint = self.get_hint(number)
        
        if number == self.secret_number:
            self.game_over = True
            self.won = True
            return True, hint
        
        if self.attempts >= self.max_attempts:
            self.game_over = True
            return False, hint
        
        return False, hint

game_sessions = {}

def get_game_keyboard():
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔄 Новая игра", callback_data="guess_restart"),
            types.InlineKeyboardButton(text="🚪 Выход", callback_data="guess_exit")
        ]
    ])
    return keyboard

def get_input_keyboard():
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    for row in range(3):
        buttons_row = []
        for col in range(3):
            number = row * 3 + col + 1
            buttons_row.append(types.InlineKeyboardButton(text=str(number), callback_data=f"guess_{number}"))
        keyboard.inline_keyboard.append(buttons_row)
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="0", callback_data="guess_0"),
        types.InlineKeyboardButton(text="⌫", callback_data="guess_backspace"),
        types.InlineKeyboardButton(text="✓", callback_data="guess_submit")
    ])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="🔄 Новая игра", callback_data="guess_restart"),
        types.InlineKeyboardButton(text="🚪 Выход", callback_data="guess_exit")
    ])
    
    return keyboard

async def process_guess_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    logging.info(f"Обработка guess_callback для пользователя {user_id}, данные: {data}")
    
    if user_id not in game_sessions:
        game_sessions[user_id] = GuessNumberGame()
    
    game = game_sessions[user_id]
    
    current_data = await state.get_data()
    current_input = current_data.get("current_input", "")
    
    if data == "guess_restart":
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
    
    elif data == "guess_exit":
        await callback_query.message.edit_text(
            "Игра 'Угадай число' завершена. Спасибо за игру!",
            reply_markup=None
        )
        del game_sessions[user_id]
        await state.set_state(Form.waiting_for_message)
    
    elif data == "guess_backspace":
        if current_input:
            current_input = current_input[:-1]
            await state.update_data(current_input=current_input)
            
            message_text = (
                "🎮 Угадай число 🎮\n\n"
                f"Я загадал число от {game.min_number} до {game.max_number}.\n"
                f"У вас осталось попыток: {game.get_attempts_left()}\n\n"
                f"Введите ваше предположение: {current_input or '...'}"
            )
            
            if game.guesses:
                message_text += f"\n\nПредыдущие попытки: {game.get_previous_guesses()}"
            
            await callback_query.message.edit_text(
                message_text,
                reply_markup=get_input_keyboard()
            )
    
    elif data == "guess_submit":
        if current_input:
            try:
                guess = int(current_input)
                
                if guess < game.min_number or guess > game.max_number:
                    hint = f"Число должно быть от {game.min_number} до {game.max_number}!"
                    
                    message_text = (
                        "🎮 Угадай число 🎮\n\n"
                        f"❌ {hint}\n\n"
                        f"Введите ваше предположение: {current_input}"
                    )
                    
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_input_keyboard()
                    )
                else:
                    is_correct, hint = await game.async_make_guess(guess)
                    
                    await state.update_data(current_input="")
                    
                    if game.game_over:
                        if game.won:
                            message_text = (
                                "🎮 Угадай число 🎮\n\n"
                                "🎉 Поздравляю! Вы угадали число!\n"
                                f"Загаданное число: {game.secret_number}\n"
                                f"Количество попыток: {game.attempts}"
                            )
                        else:
                            message_text = (
                                "🎮 Угадай число 🎮\n\n"
                                "😔 К сожалению, вы исчерпали все попытки.\n"
                                f"Загаданное число: {game.secret_number}\n"
                                f"Ваши попытки: {game.get_previous_guesses()}"
                            )
                        
                        await state.set_state(Form.waiting_for_message)
                        
                        await callback_query.message.edit_text(
                            message_text,
                            reply_markup=get_game_keyboard()
                        )
                        return
                    
                    message_text = (
                        "🎮 Угадай число 🎮\n\n"
                        f"Я загадал число от {game.min_number} до {game.max_number}.\n"
                        f"У вас осталось попыток: {game.get_attempts_left()}\n\n"
                    )
                    
                    if hint:
                        message_text += f"Подсказка: загаданное число {hint} чем {guess}\n\n"
                    
                    message_text += "Введите ваше предположение: ..."
                    
                    if game.guesses:
                        message_text += f"\n\nПредыдущие попытки: {game.get_previous_guesses()}"
                    
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_input_keyboard()
                    )
            
            except ValueError:
                message_text = (
                    "🎮 Угадай число 🎮\n\n"
                    "❌ Пожалуйста, введите корректное число!\n\n"
                    f"Введите ваше предположение: {current_input}"
                )
                
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=get_input_keyboard()
                )
    
    elif data.startswith("guess_") and len(data) > 6:
        digit = data.split("_")[1]
        
        if len(current_input) < 3:
            current_input += digit
            await state.update_data(current_input=current_input)
        
        message_text = (
            "🎮 Угадай число 🎮\n\n"
            f"Я загадал число от {game.min_number} до {game.max_number}.\n"
            f"У вас осталось попыток: {game.get_attempts_left()}\n\n"
            f"Введите ваше предположение: {current_input}"
        )
        
        if game.guesses:
            message_text += f"\n\nПредыдущие попытки: {game.get_previous_guesses()}"
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=get_input_keyboard()
        )
    
    await callback_query.answer() 