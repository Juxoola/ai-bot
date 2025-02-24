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

# Передаём дефолтные значения переменных окружения (их можно будет переопределить через docker-compose или docker run)
ENV BOT_TOKEN="default_bot_token"
ENV GLHF_API_KEY="default_glhf_api_key"
ENV GEMINI_API_KEY="default_gemini_api_key"
ENV GROQ_API_KEY="default_groq_api_key"
ENV ALLOWED_USER_IDS="123,456"
ENV ADMIN_USER_ID="123"
ENV DATABASE_FILE="/data/bot_data.db"

# Задаём команду для запуска приложения (изменено, так как main.py теперь находится в корне)
CMD ["python", "main.py"]