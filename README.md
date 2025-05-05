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

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following variables:
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

Start the FastAPI server:

```bash
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Using the Bot

1. Start a chat with your bot on Telegram
2. Send `/start` to get started
3. Send a URL in one of these formats:
   - `/start example.com`
   - `example.com`
   - `https://example.com`
   - `example.com query words`
4. The bot will fetch information about the website and generate an AI description

## Development with Ngrok

For local development, you can use ngrok to expose your local server:

```bash
ngrok http 8000
```

Then update your `WEBHOOK_URL` in the `.env` file with the ngrok URL.

## License

[MIT License](LICENSE) 