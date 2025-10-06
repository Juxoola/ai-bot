import logging
logging.basicConfig(level=logging.INFO, force=True)

from dotenv import load_dotenv 

load_dotenv()
import aiohttp

from aiogram import Bot, Dispatcher, F

import os
import asyncio
from pyngrok import ngrok
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


WEBHOOK_PATH = f"/bot/{bot.token}"
WEBHOOK_URL = ""

async def on_startup(bot: Bot):
    logging.info("Bot is starting up...")

    config.http_session = aiohttp.ClientSession()

    await initialize_database()
    logging.info("Database initialized.")
    logging.info("Updating all external models...")
    await update_all_external_models(config.http_session)
    logging.info("External models updated.")

    if os.getenv("USE_WEBHOOK") == "1":
        logging.info("Starting in webhook mode.")
        # Set up ngrok
        ngrok_token = os.getenv("NGROK_AUTHTOKEN")
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
        
        http_tunnel = ngrok.connect(8000, "http")
        global WEBHOOK_URL
        WEBHOOK_URL = http_tunnel.public_url
        logging.info(f"ngrok tunnel created: {WEBHOOK_URL}")

        await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
        logging.info("Webhook has been set.")
    else:
        logging.info("Starting in polling mode.")
        await bot.delete_webhook()
        logging.info("Any existing webhook has been deleted.")

async def on_shutdown(bot: Bot):
    logging.info("Bot is shutting down...")
    
    if os.getenv("USE_WEBHOOK") == "1":
        await bot.delete_webhook()
        logging.info("Webhook has been deleted.")

        # Disconnect ngrok
        tunnels = ngrok.get_tunnels()
        for tunnel in tunnels:
            ngrok.disconnect(tunnel.public_url)
        logging.info("ngrok tunnels disconnected.")

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
        
        #cookies_dir = os.path.join(os.path.dirname(__file__), "har_and_cookies")
        #set_cookies_dir(cookies_dir)
        #read_cookie_files(cookies_dir)
        print("Бот запущен и клиенты для всех пользователей инициализированы.")
        
        print("Система контроля состояний операций инициализирована.")
        
        if os.getenv("USE_WEBHOOK") == "1":
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            from aiohttp import web

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
            
            # Keep the bot running
            await asyncio.Event().wait()
        else:
            await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        print(f"Error during bot execution: {e}")
    finally:
        await on_shutdown(bot)

if __name__ == "__main__":
    asyncio.run(main())