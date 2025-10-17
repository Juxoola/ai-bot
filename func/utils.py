
import asyncio
import logging
from datetime import timedelta, datetime
import time
from aiogram import types

# Константы, которые были в messages.py
DEFAULT_API_TIMEOUT = 60
AUDIO_API_TIMEOUT = 120
EXTENDED_API_TIMEOUT = 240

async def async_run_with_timeout(func, timeout, *args, **kwargs):
    try:
        if asyncio.iscoroutinefunction(func):
            task = asyncio.create_task(func(*args, **kwargs))
            try:
                return await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
        else:
            loop = asyncio.get_running_loop()
            
            future = loop.run_in_executor(None, lambda: func(*args, **kwargs))
            try:
                return await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                future.cancel()
                try:
                    await future
                except asyncio.CancelledError:
                    pass
                raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")
            
    except asyncio.TimeoutError:
        raise TimeoutError(f"Вызов функции превысил таймаут {timeout} сек.")

async def calculate_and_show_processing_time(message: types.Message, user_context, start_time):
    end_time = time.time()
    processing_time = end_time - start_time
    formatted_processing_time = str(timedelta(seconds=int(processing_time)))
    
    service_info = f"⏳ Время обработки запроса: {formatted_processing_time}"
    
    if user_context.get("show_processing_time", True):
        await message.answer(service_info)
    
    logging.info(f"Общее время обработки сообщения: {processing_time:.5f} секунд")
    
    return formatted_processing_time

def get_current_date_russian():
    """Получает текущую дату в русском формате"""
    now = datetime.now()
    
    # Месяцы в родительном падеже
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    
    # Дни недели
    weekdays = [
        "понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"
    ]
    
    day = now.day
    month = months[now.month - 1]
    year = now.year
    weekday = weekdays[now.weekday()]
    
    return f"{day} {month} {year} года ({weekday})"