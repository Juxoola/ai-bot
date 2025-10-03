import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "default_bot_token")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "default_gemini_api_key")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "default_groq_api_key")

allowed_users_env = os.environ.get("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [int(user.strip()) for user in allowed_users_env.split(",") if user.strip()]

ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

