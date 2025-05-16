# URL Description Bot

Telegram бот для генерации AI описаний сайтов на основе URL, предоставленного пользователем. Использует механизм polling для получения обновлений от Telegram API.

## Features

- Получает сообщения через Telegram API с использованием polling
- Извлекает URLs и необязательные запросы от пользователей
- Сохраняет URLs в базу данных PostgreSQL
- Ищет информацию о URL с помощью Yandex Search API
- Получает веб-содержимое и обрабатывает его
- Генерирует AI описания с помощью OpenAI's GPT-4o-mini model
- Отправляет ответы пользователю
- Работает без необходимости публичного URL или ngrok

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Telegram Bot Token
- OpenAI API Key
- Yandex Search API Key and Folder ID

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

# Database configuration
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# OpenAI configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_ORGANIZATION=your_openai_organization

# Yandex Search API
YANDEX_FOLDERID=your_yandex_folderid
YANDEX_API_KEY=your_yandex_api_key
```

### Database Setup

Приложение автоматически создаст необходимые таблицы при запуске. Убедитесь, что ваш сервер PostgreSQL запущен и база данных существует.

## Running the Application

Запустите бота:

```bash
python main.py
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

## Преимущества Polling режима

- Не требуется публичный URL или SSL-сертификат
- Простая настройка и запуск без дополнительных инструментов
- Возможность локальной разработки и тестирования без настройки веб-сервера
- Задержка между запросами настроена на 1 секунду, что обеспечивает быстрый отклик бота
