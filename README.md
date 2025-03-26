# Telegram AI Bot

## Описание

Этот Telegram-бот представляет собой многофункционального ассистента для работы с различными ИИ-моделями. Он позволяет:

- Генерировать текстовые ответы с помощью интеграций с такими провайдерами, как g4f, Gemini, GLHF(pollinations) и OpenAI.
- Обрабатывать изображения: распознавание и генерация картинок по заданным ключевым словам.
- Выполнять транскрипцию аудио с использованием модели Whisper.
- Осуществлять веб-поиск по запросам пользователя.
- Накапливать длинные сообщения для последующей обработки.
- Работать с различными типами документов и файлов.

Дополнительно бот поддерживает команды администратора для управления пользователями и моделями, что позволяет:

- Добавлять/удалять пользователей.
- Добавлять/удалять модели (как текстовые, так и для генерации/распознавания изображений).
- Рассылать сообщения всем пользователям или отдельным пользователям.

Благодаря гибкой архитектуре и использованию библиотеки aiogram бот легко масштабируется и настраивается, а также поддерживает работу с персонифицированными клиентами для каждого пользователя.

## Основные возможности

- **/start** — Запуск бота и вывод приветственного сообщения с меню команд.
- **/help** или клавиша "ℹ️ Помощь" — Отображение списка основных команд.
- **/settings** или клавиша "⚙️ Настройки" — Открытие меню настроек, где можно выбрать модели, режимы работы и параметры обработки.
- **/clear** или клавиша "🗑️ Очистить" — Сброс контекста беседы, сохраняя настройки.
- **/generate_image** или клавиша "🎨 Сгенерировать" — Генерация изображения по заданному запросу.
- **/audio** или клавиша "🎤 Аудио" — Прием аудиофайла для транскрипции.
- **/search** или клавиша "🌐 Поиск" — Выполнение веб-поиска.
- **/meme** — Получение случайного мема.
- **/long_message** или клавиша "📝 Длинное сообщение" — Режим накопления сообщений перед отправкой модели.

Кроме того, доступны административные команды (выполняются только пользователями с администраторскими правами):

- **/add_user** и **/remove_user** — Управление списком разрешённых пользователей.
- **/add_model**, **/delete_model** — Управление моделями для генерации текста.
- **/add_image_gen_model**, **/delete_image_gen_model** — Управление моделями для генерации изображений.
- **/add_image_rec_model**, **/delete_image_rec_model** — Управление моделями для распознавания изображений.
- **/send_to_all** и **/send_to_user** — Рассылка сообщений пользователям.

## Установка и запуск

### 1. Локальный запуск

#### Шаг 1. Клонирование репозитория

```bash
git clone <URL вашего репозитория>
cd <название репозитория>
```

#### Шаг 2. Создание виртуального окружения (рекомендуется)

```bash
python -m venv venv
```

- Для активации на Linux/macOS:
  ```bash
  source venv/bin/activate
  ```
- Для активации на Windows:
  ```bash
  venv\Scripts\activate
  ```

#### Шаг 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Шаг 4. Настройка переменных окружения

Создайте файл **.env** в корне проекта и настройте его следующим образом:

```env
# Основные настройки
BOT_TOKEN=<Ваш Telegram Bot Token>
ALLOWED_USER_IDS=123,456  # список разрешенных ID пользователей через запятую
ADMIN_USER_ID=123         # ID администратора
DATABASE_FILE=bot_data.db

# API ключи для различных провайдеров
GEMINI_API_KEY=<Ваш GEMINI_API_KEY>
GROQ_API_KEY=<Ваш GROQ_API_KEY>

# Настройки провайдеров
CHAT_PROVIDERS=DDG,Blackbox,CablyAI,Glider,HuggingSpace,PerplexityLabs,TeachAnything,PollinationsAI,OIVSCode,DeepInfraChat,ImageLabs
IMAGE_PROVIDERS=Blackbox,DeepInfraChat,PollinationsAI,OIVSCode

# Доступные модели для каждого провайдера
PROVIDER_MODELS={"Blackbox": "gpt-4o,gemini-1.5-flash,llama-3.3-70b,mixtral-7b,deepseek-chat,dbrx-instruct,qwq-32b,hermes-2-dpo,flux,deepseek-r1,deepseek-v3,blackboxai-pro,llama-3.1-8b,llama-3.1-70b,llama-3.1-405b,blackboxai,gemini-2.0-flash,o3-mini", "Glider": "llama-3.1-70b,llama-3.1-8b,llama-3.2-3b,deepseek-r1", "DeepInfraChat": "llama-3.1-8b,llama-3.2-90b,llama-3.3-70b,deepseek-v3,mixtral-small-28b,deepseek-r1,phi-4,wizardlm-2-8x22b,qwen-2.5-72b,llama-3.2-90b,minicpm-2.5", "HuggingSpace": "qvq-72b,qwen-2-72b,command-r,command-r-plus,command-r7b,flux-dev,flux-schnell,sd-3.5", "DDG": "gpt-4o-mini,claude-3-haiku,llama-3.3-70b,mixtral-small-24b,o3-mini", "PollinationsAI": "gpt-4o-mini,gpt-4,gpt-4o,qwen-2.5-72b,qwen-2.5-coder-32b,llama-3.3-70b,mistral-nemo,deepseek-chat,llama-3.1-8b,gpt-4o-vision,gpt-4o-mini-vision,deepseek-r1,gemini-2.0-flash,gemini-2.0-flash-thinking,sdxl-turbo,flux", "OIVSCode": "gpt-4o-mini", "ImageLabs": "sdxl-turbo", "TeachAnything": "llama-3.1-70b", "PerplexityLabs": "sonar,sonar-pro,sonar-reasoning,sonar-reasoning-pro,r1-1776", "CablyAI": "o3-mini-low,gpt-4o-mini,deepseek-r1,deepseek-v3"}

# Модели для распознавания изображений
PROVIDER_IMAGE_RECOGNITION_MODELS={"Blackbox": ["blackboxai", "gpt-4o", "o1", "o3-mini", "gemini-1.5-pro", "gemini-1.5-flash", "llama-3.1-8b", "llama-3.1-70b", "llama-3.1-405b", "gemini-2.0-flash", "deepseek-v3"], "PollinationsAI": ["gpt-4o", "gpt-4o-mini", "o1-mini"], "OIVSCode": ["gpt-4o-mini"], "DeepInfraChat": ["llama-3.2-90b", "minicpm-2.5"]}

# Настройки OpenAI-совместимых провайдеров
OPENAI_PROVIDERS='{
  "poli": {"api_key": "YOUR_KEY", "base_url": "https://text.pollinations.ai/openai"},
  "openrouter": {"api_key": "YOUR_KEY", "base_url": "https://openrouter.ai/api/v1"},
}'

# Приоритет API и таймауты
PRIORITY_API_ORDER=gemini,g4f,poli,openrouter
TIMEOUT_CONFIG='{
  "models": {
    "gemini": ["gemini-2.0-flash-thinking-exp-01-21"],
    "g4f": ["deepseek-r1", "o3-mini", "r1-1776", "sonar-reasoning", "sonar-reasoning-pro", "qwq-32b"],
    "poli": ["deepseek-r1", "gemini-thinking", "deepseek-reasoner", "deepseek-r1-llama"],
    "openrouter": ["deepseek/deepseek-r1-distill-llama-70b:free", "deepseek/deepseek-r1:free", "qwen/qwq-32b:free", "deepseek/deepseek-r1-zero:free"],
  }
}'
```

#### Шаг 5. Запуск бота

```bash
python main.py
```

### 2. Запуск с использованием Docker

#### Шаг 1. Сборка Docker-образа

```bash
docker build -t telegram-ai-bot .
```

#### Шаг 2. Запуск контейнера

```bash
docker run -d --name telegram-ai-bot \
  -e BOT_TOKEN=<Ваш Telegram Bot Token> \
  -e ALLOWED_USER_IDS="123,456" \
  -e ADMIN_USER_ID=123 \
  -e DATABASE_FILE=/data/bot_data.db \
  -e GEMINI_API_KEY=<Ваш GEMINI_API_KEY> \
  -e CHAT_PROVIDERS="DDG,Blackbox,CablyAI,Glider,HuggingSpace,PerplexityLabs,TeachAnything,PollinationsAI,OIVSCode,DeepInfraChat,ImageLabs" \
  -e IMAGE_PROVIDERS="Blackbox,DeepInfraChat,PollinationsAI,OIVSCode" \
  -e WEB_SEARCH_PROVIDERS="Blackbox" \
  -e PROVIDER_MODELS='{"Blackbox": "gpt-4o,gemini-1.5-flash,llama-3.3-70b","DeepInfraChat": "llama-3.1-8b,llama-3.2-90b"}' \
  -e PROVIDER_IMAGE_RECOGNITION_MODELS='{"Blackbox": ["blackboxai", "gpt-4o"], "PollinationsAI": ["gpt-4o", "gpt-4o-mini"]}' \
  -e OPENAI_PROVIDERS='{"poli": {"api_key": "YOUR_KEY", "base_url": "https://text.pollinations.ai/openai"}}' \
  -e PRIORITY_API_ORDER="gemini,g4f,poli,openrouter" \
  -v $(pwd)/data:/data \
  telegram-ai-bot
```

### 3. Запуск с использованием Docker Compose

Создайте файл **docker-compose.yml** в корне проекта:

```yaml
version: '3'

services:
  telegram-ai-bot:
    build: .
    container_name: telegram-ai-bot
    restart: unless-stopped
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      GROQ_API_KEY: ${GROQ_API_KEY}
      ALLOWED_USER_IDS: ${ALLOWED_USER_IDS}
      ADMIN_USER_ID: ${ADMIN_USER_ID}
      DATABASE_FILE: ${DATABASE_FILE}
      CHAT_PROVIDERS: ${CHAT_PROVIDERS}
      IMAGE_PROVIDERS: ${IMAGE_PROVIDERS}
      PROVIDER_MODELS: ${PROVIDER_MODELS}
      PROVIDER_IMAGE_RECOGNITION_MODELS: ${PROVIDER_IMAGE_RECOGNITION_MODELS}
      OPENAI_PROVIDERS: ${OPENAI_PROVIDERS}
      PRIORITY_API_ORDER: ${PRIORITY_API_ORDER}
      TIMEOUT_CONFIG: ${TIMEOUT_CONFIG}
      COMPOSE_BAKE: ${COMPOSE_BAKE}
    volumes:
      - ./data:/data
```

Запустите контейнер:

```bash
docker-compose up -d
```

## Структура проекта

- **main.py** — Основной файл запуска бота.
- **config.py** — Конфигурация, настройка провайдеров и определение состояний FSM.
- **database.py** — Подключение и работа с базой данных, управление контекстами пользователей.
- **key.py** — Генерация и проверка ключей для авторизации.
- **keyboards.py** — Определение клавиатур и кнопок для взаимодействия с пользователем.
- **settings.py** — Настройки бота и управление параметрами.
- **func/** — Директория с функциональными модулями:
  - **audio.py** — Обработка аудиофайлов и транскрипция.
  - **admin.py** — Административные функции (добавление/удаление пользователей, моделей).
  - **messages.py** — Обработка сообщений и форматирование.
  - **image.py** — Функции для работы с изображениями.
- **handlers/** — Обработчики команд и сообщений:
  - **audio.py** — Обработка аудиокоманд.
  - **base.py** — Базовые команды (start, help, clear).
  - **games.py** — Игровые функции, включая команду meme.
  - **image.py** — Обработка изображений.
  - **message_handler.py** — Основной обработчик сообщений.
  - **search.py** — Веб-поиск.
  - **settings_callbacks.py** — Обработка настроек.
- **Dockerfile** — Инструкция для создания Docker-образа.
- **docker-compose.yml** — Конфигурация для Docker Compose.
- **requirements.txt** — Список зависимостей проекта.

## Поддерживаемые типы файлов

Бот может обрабатывать различные типы файлов:

- **Текстовые форматы**: TXT, MD, XML, JSON, JS, PY, PHP, CSS, и др.
- **Документы**: PDF, DOCX, DOC
- **Таблицы**: XLSX, XLS, CSV
- **Изображения**: JPEG, PNG
- **Аудио**: MP3, M4A, OGG, WAV
- **Видеосообщения**

## Дополнительная информация

- Бот использует библиотеку [aiogram](https://docs.aiogram.dev/) для работы с Telegram API.
- Для взаимодействия с различными ИИ-моделями применяются сторонние библиотеки и API (g4f, Gemini, OpenAI и др.).
- Полный список команд и инструкций можно получить в самом боте, выполнив команду **/help**.

Наслаждайтесь использованием бота и расширением его функциональности!
