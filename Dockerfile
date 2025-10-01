# Этап сборки (builder)
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends antiword \
    libreoffice-writer libmagic-dev ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data && chmod 777 /data

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

# Передаём дефолтные значения переменных окружения
ENV BOT_TOKEN="default_bot_token"
ENV GLHF_API_KEY="default_glhf_api_key"
ENV DDC_API_KEY="default_ddc_api_key"
ENV OPEN_ROUTER_KEY="default_open_router_key"
ENV GEMINI_API_KEY="default_gemini_api_key"
ENV FRESED_API_KEY="default_fresed_api_key"
ENV GROQ_API_KEY="default_groq_api_key"
ENV ALLOWED_USER_IDS="123,456"
ENV ADMIN_USER_ID="123"
ENV DATABASE_FILE="/data/bot_data.db"
ENV CHAT_PROVIDERS=""
ENV IMAGE_PROVIDERS=""
ENV PROVIDER_IMAGE_RECOGNITION_MODELS=""
ENV PRIORITY_API_ORDER=""
ENV TIMEOUT_CONFIG =""
ENV OPENAI_PROVIDERS =""
ENV ANTHROPIC_PROVIDERS =""
ENV PROVIDER_MODELS=""

CMD ["python", "main.py"]