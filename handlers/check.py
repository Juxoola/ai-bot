from aiogram.fsm.context import FSMContext
from aiogram import types
from config import Form

async def check_in_progress(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        await state.set_state(Form.waiting_for_message)
        
    current_state = await state.get_state()
    
    if current_state in [Form.playing_tictactoe, Form.playing_guess_number]:
        if message.content_type == 'text' and message.text:
            allowed_commands = ['/cancel']
            if any(message.text.startswith(cmd) for cmd in allowed_commands):
                return True
        
        await message.answer("🎮 Вы сейчас в игре. Пожалуйста, закончите текущую игру или используйте /cancel для выхода.")
        return False
    
    if current_state == Form.in_progress:
        if message.content_type == 'text' and message.text:
            allowed_commands = ['/start', '/help', '/settings', '/cancel']
            if any(message.text.startswith(cmd) for cmd in allowed_commands):
                return True
        
        await message.answer("⏳ Выполняется операция. Пожалуйста, дождитесь её завершения или используйте /cancel для отмены.")
        return False
    
    return True

async def set_in_progress(state: FSMContext):
    current_state = await state.get_state()
    if current_state not in [Form.playing_tictactoe, Form.playing_guess_number]:
        await state.set_state(Form.in_progress)

async def clear_in_progress(state: FSMContext):
    current_state = await state.get_state()
    # Special states that should be preserved instead of being reset
    special_states = [
        Form.playing_tictactoe, 
        Form.playing_guess_number,
        Form.waiting_for_image_and_prompt,
        Form.waiting_for_image_and_prompt_openai,
        Form.waiting_for_custom_image_prompt,
        Form.waiting_for_custom_image_prompt_openai,
        Form.waiting_for_custom_image_recognition_prompt,
        Form.waiting_for_image_recognition_prompt,
        Form.waiting_for_long_message,
    ]
    
    if current_state not in special_states:
        await state.set_state(Form.waiting_for_message)

async def exit_game(state: FSMContext):
    await state.set_state(Form.waiting_for_message)

async def ensure_initial_state(state: FSMContext):
    if await state.get_state() is None:
        await state.set_state(Form.waiting_for_message)