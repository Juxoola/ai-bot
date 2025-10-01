import logging
logging.basicConfig(level=logging.INFO, force=True)

from dotenv import load_dotenv 

load_dotenv()

import os.path
import asyncio
from g4f.cookies import set_cookies_dir, read_cookie_files
from config import (
    bot, dp, init_enhance_prompt_client,
    openai_clients, DEFAULT_SYSTEM_PROMPTS
)
from database import (
    initialize_database, clear_all_user_contexts, 
    initialize_models, init_all_user_clients, db_pool
)
from handlers.check import ensure_initial_state

import handlers

async def shutdown():
    try:
        await db_pool.close_all()
        print("Database connections closed successfully")
    except Exception as e:
        print(f"Error closing database connections: {e}")

async def main():
    try:
        await initialize_database()
        await initialize_models()
        await clear_all_user_contexts()
        await init_all_user_clients()
        await init_enhance_prompt_client()
        
        cookies_dir = os.path.join(os.path.dirname(__file__), "har_and_cookies")
        set_cookies_dir(cookies_dir)
        read_cookie_files(cookies_dir)
        print("Бот запущен и клиенты для всех пользователей инициализированы.")
        
        print("Система контроля состояний операций инициализирована.")
        
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        print(f"Error during bot execution: {e}")
    finally:
        await shutdown()

if __name__ == "__main__":
    asyncio.run(main())