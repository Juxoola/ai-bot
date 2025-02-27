# Этап сборки (builder)
FROM python:3.12-slim AS builder

# Устанавливаем необходимые для сборки системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости в отдельный префикс, чтобы потом их скопировать
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# Финальный этап (final)
FROM python:3.12-slim

# Создаём директорию для базы данных и устанавливаем права доступа
RUN mkdir -p /data && chmod 777 /data

WORKDIR /app

# Копируем установленные пакеты из builder-этапа
COPY --from=builder /install /usr/local

# Копируем весь исходный код проекта в контейнер
COPY . .

# Передаём дефолтные значения переменных окружения
ENV BOT_TOKEN="default_bot_token"
ENV GLHF_API_KEY="default_glhf_api_key"
ENV GEMINI_API_KEY="default_gemini_api_key"
ENV GROQ_API_KEY="default_groq_api_key"
ENV ALLOWED_USER_IDS="123,456"
ENV ADMIN_USER_ID="123"
ENV DATABASE_FILE="/data/bot_data.db"
ENV CHAT_PROVIDERS="DDG,Blackbox,CablyAI,Glider,HuggingSpace,PerplexityLabs,TeachAnything,PollinationsAI,OIVSCode,DeepInfraChat,ImageLabs"
ENV IMAGE_PROVIDERS="Blackbox,DeepInfraChat,PollinationsAI,OIVSCode"
ENV WEB_SEARCH_PROVIDERS="Blackbox"
ENV PROVIDER_MODELS='{"Blackbox": "gpt-4o,gemini-1.5-flash,llama-3.3-70b,mixtral-7b,deepseek-chat,dbrx-instruct,qwq-32b,hermes-2-dpo,flux,deepseek-r1,deepseek-v3,blackboxai-pro,llama-3.1-8b,llama-3.1-70b,llama-3.1-405b,blackboxai,gemini-2.0-flash,o3-mini","Glider": "llama-3.1-70b,llama-3.1-8b,llama-3.2-3b,deepseek-r1", "DeepInfraChat": "llama-3.1-8b,llama-3.2-90b,llama-3.3-70b,deepseek-v3,mixtral-small-28b,deepseek-r1,phi-4,wizardlm-2-8x22b,qwen-2.5-72b,llama-3.2-90b,minicpm-2.5", "HuggingSpace": "qvq-72b,qwen-2-72b,command-r,command-r-plus,command-r7b,flux-dev,flux-schnell,sd-3.5", "DDG": "gpt-4o-mini,claude-3-haiku,llama-3.3-70b,mixtral-small-24b,o3-mini", "PollinationsAI": "gpt-4o-mini,gpt-4,gpt-4o,qwen-2.5-72b,qwen-2.5-coder-32b,llama-3.3-70b,mistral-nemo,deepseek-chat,llama-3.1-8b,gpt-4o-vision,gpt-4o-mini-vision,deepseek-r1,gemini-2.0-flash,gemini-2.0-flash-thinking,sdxl-turbo,flux", "OIVSCode": "gpt-4o-mini", "ImageLabs": "sdxl-turbo", "TeachAnything": "llama-3.1-70b", "PerplexityLabs": "sonar,sonar-pro,sonar-reasoning,sonar-reasoning-pro,r1-1776", "CablyAI": "o3-mini-low,gpt-4o-mini,deepseek-r1,deepseek-v3"}'

# Задаём команду для запуска приложения (например, main.py теперь находится в корне)
CMD ["python", "main.py"]