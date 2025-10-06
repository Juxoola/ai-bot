import logging

logging.basicConfig(level=logging.INFO, force=True)

from dotenv import load_dotenv

load_dotenv()
import asyncio
import os

import aiohttp
import config
from aiogram import Bot
from aiogram.webhook.aiohttp_server import (SimpleRequestHandler,
                                            setup_application)
from aiohttp import web
from config import bot, dp, init_enhance_prompt_client
from database import (clear_all_user_contexts, db_pool, init_all_user_clients,
                      initialize_database, update_all_external_models)
from g4f.cookies import set_cookies_dir, read_cookie_files
from handlers.check import ensure_initial_state


import handlers

WEBHOOK_PATH = f"/bot/{bot.token}"

async def on_startup(bot: Bot):
    logging.info("Запуск бота...")

    config.http_session = aiohttp.ClientSession()

    await initialize_database()
    logging.info("База данных инициализирована.")

    logging.info("Обновление всех внешних моделей...")
    await update_all_external_models(config.http_session)
    logging.info("Внешние модели обновлены.")

    if os.getenv("USE_WEBHOOK") == "1":
        WEBHOOK_URL = os.getenv("WEBHOOK_URL")
        if not WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL не установлен в переменных окружения.")

        logging.info(f"Запуск в режиме вебхука. URL: {WEBHOOK_URL}")

        await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
        logging.info("Вебхук установлен.")
    else:
        logging.info("Запуск в режиме опроса (polling).")
        await bot.delete_webhook()
        logging.info("Существующий вебхук удален.")

async def on_shutdown(bot: Bot):
    logging.info("Остановка бота...")

    if os.getenv("USE_WEBHOOK") == "1":
        await bot.delete_webhook()
        logging.info("Вебхук удален.")

    if config.http_session:
        await config.http_session.close()
        logging.info("Сессия AIOHTTP ClientSession закрыта.")

    await db_pool.close_all()
    logging.info("Пул соединений с базой данных закрыт.")

async def main():

    try:
        await on_startup(bot)
        await clear_all_user_contexts()
        await init_all_user_clients()
        await init_enhance_prompt_client()

        cookies_dir = os.path.join(os.path.dirname(__file__), "har_and_cookies")
        set_cookies_dir(cookies_dir)
        read_cookie_files(cookies_dir)

        logging.info("Бот запущен и клиенты для всех пользователей инициализированы.")
        logging.info("Система контроля состояний операций инициализирована.")

        if os.getenv("USE_WEBHOOK") == "1":
            app = web.Application()
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
            )
            webhook_requests_handler.register(app, path=WEBHOOK_PATH)
            setup_application(app, dp, bot=bot)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', 8000)
            await site.start()
            logging.info("Веб-сервер запущен на localhost:8000")

            await asyncio.Event().wait()
        else:
            await dp.start_polling(bot, skip_updates=True)

    except Exception as e:
        logging.error(f"Ошибка во время выполнения бота: {e}", exc_info=True)
    finally:
        await on_shutdown(bot)

if __name__ == "__main__":
    asyncio.run(main())
