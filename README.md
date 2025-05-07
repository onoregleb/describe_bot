# URL Description Bot

FastAPI приложение, которое реализует Telegram бота для генерации AI описаний сайтов, на основе URL, предоставленного пользователем.

## Features

- Принимает сообщения через Telegram webhook
- Извлекает URLs и необязательные запросы от пользователей
- Сохраняет URLs в базу данных PostgreSQL
- Ищет информацию о URL с помощью Yandex Search API
- Получает веб-содержимое и обрабатывает его
- Генерирует AI описания с помощью OpenAI's GPT-4o-mini model
- Отправляет ответы пользователю

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Telegram Bot Token
- OpenAI API Key
- Yandex Search API Key and Folder ID
- Public URL for webhook (can use ngrok for development)

### Installation

1. Склонируйте репозиторий [https://github.com/onoregleb/describe_bot](github):
```bash
git clone https://github.com/onoregleb/describe_bot
cd describe_bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` в корневой директории с переменными окружения:
```
# Bot configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=https://your-domain.com/webhook

# Database configuration
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# OpenAI configuration
OPENAI_API_KEY=your_openai_api_key

# Yandex Search API
YANDEX_FOLDERID=your_yandex_folderid
YANDEX_API_KEY=your_yandex_api_key
```

### Database Setup

Приложение автоматически создаст необходимые таблицы при запуске. Убедитесь, что ваш сервер PostgreSQL запущен и база данных существует.

## Running the Application

Запустите FastAPI сервер:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Using the Bot

1. Начните чат с ботом на Telegram
2. Отправьте `/start` чтобы начать
3. Отправьте URL в одном из этих форматов:
   - `/start example.com`
   - `example.com`
   - `https://example.com`
   - `example.com query words`
4. Бот получит информацию о сайте и сгенерирует AI описание

## Development with Ngrok

Для локальной разработки вы можете использовать ngrok для выставления вашего локального сервера:

```bash
ngrok http 8000
```

Затем обновите `WEBHOOK_URL` в файле `.env` с ngrok URL и запустите (пункт Running the Application)
