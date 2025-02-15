# Telegram AI Bot

## Описание

Этот Telegram-бот представляет собой многофункционального ассистента для работы с различными ИИ-моделями. Он позволяет:

- Генерировать текстовые ответы с помощью интеграций с такими провайдерами, как g4f, Gemini, GLHF(pollinations) и OpenAI.
- Обрабатывать изображения: распознавание и генерация картинок по заданным ключевым словам.
- Выполнять транскрипцию аудио с использованием модели Whisper.
- Осуществлять веб-поиск по запросам пользователя.
- Аккумулировать длинные сообщения для последующей обработки.

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
BOT_TOKEN=<Ваш Telegram Bot Token>
GLHF_API_KEY=<Ваш GLHF_API_KEY>
GEMINI_API_KEY=<Ваш GEMINI_API_KEY>
GROQ_API_KEY=<Ваш GROQ_API_KEY>
ALLOWED_USER_IDS=123,456  # список разрешенных ID пользователей через запятую
ADMIN_USER_ID=123         # ID администратора
DATABASE_FILE=bot_data.db
```
Ключ для glhf ничего не делает, так как использует сервис Polinations
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
  -e GLHF_API_KEY=<Ваш GLHF_API_KEY> \
  -e GEMINI_API_KEY=<Ваш GEMINI_API_KEY> \
  -e GROQ_API_KEY=<Ваш GROQ_API_KEY> \
  -e ALLOWED_USER_IDS="123,456" \
  -e ADMIN_USER_ID=123 \
  -e DATABASE_FILE=/data/bot_data.db \
  telegram-ai-bot
```

## Структура проекта

- **main.py** — Основной файл запуска бота.
- **config.py** — Конфигурация, настройка провайдеров и определение состояний FSM.
- **database.py** — Подключение и работа с базой данных, управление контекстами пользователей.
- **func/** — Директория с функциональными модулями (работа с сообщениями, аудио, поиск, админ-команды и др.).
- **keyboards.py** — Определение клавиатур и кнопок для взаимодействия с пользователем.
- **Dockerfile** — Инструкция для создания Docker-образа.

## Дополнительная информация

- Бот использует библиотеку [aiogram](https://docs.aiogram.dev/) для работы с Telegram API.
- Для взаимодействия с различными ИИ-моделями применяются сторонние библиотеки и API (g4f, Gemini, OpenAI и др.).
- Полный список команд и инструкций можно получить в самом боте, выполнив команду **/help**.

Наслаждайтесь использованием бота и расширением его функциональности!
