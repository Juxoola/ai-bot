# Используем официальный slim-образ Python
FROM python:3.11-slim

# Обновляем список пакетов и устанавливаем необходимые системные пакеты
RUN apt-get update && apt-get install -y build-essential

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

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