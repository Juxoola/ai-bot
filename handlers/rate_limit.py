import time

from aiogram import types

rate_limit_data = {}

MAX_REQUESTS_PER_MINUTE = 10

async def check_rate_limit(message: types.Message, action_type: str) -> bool:

    user_id = message.from_user.id
    current_time = time.time()
    
    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = {}
    
    if action_type not in rate_limit_data[user_id]:
        rate_limit_data[user_id][action_type] = []
    
    rate_limit_data[user_id][action_type] = [
        timestamp for timestamp in rate_limit_data[user_id][action_type]
        if current_time - timestamp < 60
    ]
    
    if len(rate_limit_data[user_id][action_type]) >= MAX_REQUESTS_PER_MINUTE:
        oldest_timestamp = rate_limit_data[user_id][action_type][0]
        wait_time = 60 - (current_time - oldest_timestamp)
        wait_time = max(1, int(wait_time))
        
        await message.reply(
            f"⏳ Слишком много запросов. Пожалуйста, подождите примерно {wait_time} секунд перед следующим запросом."
        )
        return False
    
    rate_limit_data[user_id][action_type].append(current_time)
    return True


async def check_callback_rate_limit(callback_query: types.CallbackQuery, action_type: str) -> bool:

    user_id = callback_query.from_user.id
    current_time = time.time()
    
    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = {}
    
    if action_type not in rate_limit_data[user_id]:
        rate_limit_data[user_id][action_type] = []
    
    rate_limit_data[user_id][action_type] = [
        timestamp for timestamp in rate_limit_data[user_id][action_type]
        if current_time - timestamp < 60
    ]
    
    if len(rate_limit_data[user_id][action_type]) >= MAX_REQUESTS_PER_MINUTE:
        oldest_timestamp = rate_limit_data[user_id][action_type][0]
        wait_time = 60 - (current_time - oldest_timestamp)
        wait_time = max(1, int(wait_time))
        
        await callback_query.answer(
            f"Слишком много запросов. Подождите {wait_time} сек.",
            show_alert=True
        )
        return False
    
    rate_limit_data[user_id][action_type].append(current_time)
    return True 