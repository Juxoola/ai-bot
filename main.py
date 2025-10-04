import logging
logging.basicConfig(level=logging.INFO, force=True)

from dotenv import load_dotenv 

load_dotenv()
import aiohttp

from aiogram import Bot, Dispatcher, F

import os.path
import asyncio
from g4f.cookies import set_cookies_dir, read_cookie_files
import config 

from config import (
    bot, dp, init_enhance_prompt_client 
)
from database import (
    initialize_database, clear_all_user_contexts, 
    init_all_user_clients, db_pool, update_all_external_models
)
from handlers.check import ensure_initial_state

import handlers


async def on_startup(bot: Bot):
    logging.info("Bot is starting up...")

    config.http_session = aiohttp.ClientSession()

    await initialize_database()
    logging.info("Database initialized.")
    logging.info("Updating all external models...")
    await update_all_external_models(config.http_session)
    logging.info("External models updated.")

async def on_shutdown(bot: Bot):
    logging.info("Bot is shutting down...")
    
    if config.http_session:
        await config.http_session.close()
        logging.info("AIOHTTP ClientSession closed.")

    await db_pool.close_all()
    logging.info("Database connection pool closed.")

async def main():
    try:
        await on_startup(bot)
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
        await on_shutdown(bot)

if __name__ == "__main__":
    asyncio.run(main())