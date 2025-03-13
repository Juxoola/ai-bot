import os

# Получаем ключи из переменных окружения. Если ключ не найден, можно задать значение по умолчанию или выбросить ошибку.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "default_bot_token")
DDC_API_KEY = os.environ.get("DDC_API_KEY", "default_ddc_api_key")
OPEN_ROUTER_KEY = os.environ.get("OPEN_ROUTER_KEY", "default_open_router_key")
GLHF_API_KEY = os.environ.get("GLHF_API_KEY", "default_glhf_api_key")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "default_gemini_api_key")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "default_groq_api_key")
FRESED_API_KEY = os.environ.get("FRESED_API_KEY", "default_fresed_api_key")

# Allowed user IDs
allowed_users_env = os.environ.get("ALLOWED_USER_IDS")
ALLOWED_USER_IDS = [int(user.strip()) for user in allowed_users_env.split(",") if user.strip()]

# Получаем идентификатор администратора из переменной окружения
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))