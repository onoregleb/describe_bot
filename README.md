# URL Description Bot

A FastAPI application that implements a Telegram bot for generating AI descriptions of websites, based on a URL provided by the user.

## Features

- Receives messages via Telegram webhook
- Extracts URLs and optional queries from user messages
- Saves URLs to PostgreSQL database
- Searches for information about the URL using Yandex Search API
- Fetches web content and processes it
- Generates AI descriptions using OpenAI's GPT-4o-mini model
- Sends responses back to the user

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

The application will automatically create the required tables on startup. Ensure your PostgreSQL server is running and the database exists.

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
