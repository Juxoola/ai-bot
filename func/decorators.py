from aiogram import types
from aiogram.fsm.context import FSMContext
from functools import wraps
import asyncio
import time
from database import is_admin, is_allowed
from aiogram.enums import ParseMode

def admin_required(func):
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    async def wrapper(message_or_callback, *args, **kwargs):
        # Определяем, является ли аргумент сообщением или callback_query
        user_id = message_or_callback.from_user.id
        
        if not is_admin(user_id):
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.reply("Извините, у вас нет прав для выполнения этого действия.")
            elif isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer("Извините, у вас нет прав для выполнения этого действия.")
            return
        
        return await func(message_or_callback, *args, **kwargs)
    
    return wrapper

def access_required(func):
    """Декоратор для проверки общего доступа к боту"""
    @wraps(func)
    async def wrapper(message_or_callback, *args, **kwargs):
        user_id = message_or_callback.from_user.id
        
        if not is_allowed(user_id):
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.reply(
                    "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer("У вас нет доступа к этому боту")
            return
        
        return await func(message_or_callback, *args, **kwargs)
    
    return wrapper

class RateLimiter:
    """Класс для ограничения частоты запросов пользователей"""
    def __init__(self, rate_limit=5, per_seconds=60):
        self.rate_limit = rate_limit
        self.per_seconds = per_seconds
        self.user_requests = {}
        self.lock = asyncio.Lock()
    
    async def can_process(self, user_id):
        async with self.lock:
            current_time = time.time()
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
            
            # Удалить устаревшие записи
            self.user_requests[user_id] = [
                ts for ts in self.user_requests[user_id]
                if current_time - ts < self.per_seconds
            ]
            
            if len(self.user_requests[user_id]) >= self.rate_limit:
                return False
                
            self.user_requests[user_id].append(current_time)
            return True

# Создаем глобальный экземпляр RateLimiter
rate_limiter = RateLimiter(rate_limit=5, per_seconds=60)

def rate_limit(func):
    """Декоратор для ограничения частоты запросов"""
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if is_admin(user_id):
            # Администраторы не ограничиваются лимитом запросов
            return await func(message, *args, **kwargs)
        
        can_process = await rate_limiter.can_process(user_id)
        if not can_process:
            await message.reply("⚠️ Слишком много запросов. Пожалуйста, подождите")
            return
        
        return await func(message, *args, **kwargs)
    
    return wrapper