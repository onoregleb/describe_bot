import asyncio
import logging
import re
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
from typing import Dict, Any

from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL
from database import get_db, create_tables
from telegram_client import TelegramClient
from services import (
    parse_url_from_message,
    save_url_to_db,
    get_latest_url,
    generate_ai_description,
    generate_ai_question_answer
)

# Configure root logger for INFO level only
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Make sure other loggers don't show DEBUG messages
for logger_name in ['__main__', 'services', 'telegram_client']:
    module_logger = logging.getLogger(logger_name)
    module_logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="URL Description Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # Создаем таблицы при запуске
    create_tables()
    
    # Настраиваем webhook при запуске
    try:
        # Проверяем текущий webhook
        webhook_info = await TelegramClient.get_webhook_info()
        current_url = webhook_info.get('result', {}).get('url', '')
        env_url = WEBHOOK_URL
        
        # Если URL в настройках отличается от URL в .env или webhook не настроен
        if current_url != env_url:
            # Сначала удаляем старый webhook (если есть)
            if current_url:
                await TelegramClient.delete_webhook()
                logger.info(f"Deleted previous webhook: {current_url}")
            
            # Устанавливаем новый webhook из .env
            webhook_response = await TelegramClient.set_webhook()
            logger.info(f"Webhook setup: {webhook_response}")
        else:
            logger.info(f"Webhook already set to correct URL: {env_url}")
    except Exception as e:
        logger.error(f"Webhook error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        await TelegramClient.delete_webhook()
    except Exception as e:
        logger.error(f"Webhook delete error: {e}")


async def process_message(chat_id: int, parsed_data: Dict[str, Any], db: Session):
    try:
        logger.info(f"Processing message: {parsed_data}")
        
        # Handle empty /start command
        if parsed_data.get("type") == "start_empty":
            logger.info("Handling empty /start command")
            await TelegramClient.send_message(
                chat_id,
                "Пожалуйста, предоставьте ссылку на сайт компании в формате:\n"
                "/start example.com\n\n"
                "Вы также можете отправить ссылку в одном из этих форматов:\n"
                "- example.com\n"
                "- https://example.com\n"
                "- example.com дополнительный запрос"
            )
            return
            
        elif "site" in parsed_data:
            # Process new URL from /start command or direct URL message
            site = parsed_data["site"]
            logger.info(f"Processing site: {site}")
            
            # Basic URL validation
            if not (site.startswith('http://') or site.startswith('https://')):
                site = 'https://' + site
                logger.info(f"Updated URL with scheme: {site}")
                
            # Send a waiting message while processing the website
            await TelegramClient.send_message(chat_id, "Анализирую сайт компании... Это может занять несколько секунд.")
            
            logger.info("Calling save_url_to_db to fetch data from Yandex API...")
            # Save URL to database and fetch company info using Yandex API
            await save_url_to_db(db, chat_id, site)

            url_record = await get_latest_url(db, chat_id)
            if not url_record or not url_record.cleaned_content:
                await TelegramClient.send_message(chat_id, "Не удалось обработать сайт. Пожалуйста, проверьте URL и попробуйте снова.")
                return

            try:
                # Generate AI description with company information
                description = await generate_ai_description(url_record.cleaned_content)
                await TelegramClient.send_message(chat_id, description)
                
                # If the original message included a query after the URL, process it as a question
                if "query" in parsed_data and parsed_data["query"]:
                    query = parsed_data["query"]
                    try:
                        answer = await generate_ai_question_answer(
                            url_record.cleaned_content,
                            query
                        )
                        await TelegramClient.send_message(chat_id, answer)
                    except Exception as e:
                        logger.error(f"Initial query error: {e}")
                
            except Exception as e:
                logger.error(f"Description error: {e}")
                await TelegramClient.send_message(chat_id, "Ошибка генерации описания компании. Пожалуйста, попробуйте позже.")

        else:
            # Process question about the company
            url_record = await get_latest_url(db, chat_id)
            if not url_record:
                await TelegramClient.send_message(
                    chat_id, 
                    "Пожалуйста, сначала отправьте ссылку на сайт компании.\n"
                    "Вы можете отправить её в формате:\n"
                    "- /start example.com\n"
                    "- example.com\n"
                    "- https://example.com"
                )
                return

            query = parsed_data.get("query", "").strip()
            if not query:
                await TelegramClient.send_message(chat_id, "Пожалуйста, задайте ваш вопрос о компании")
                return

            try:
                answer = await generate_ai_question_answer(
                    url_record.cleaned_content,
                    query
                )
                await TelegramClient.send_message(chat_id, answer)
            except Exception as e:
                logger.error(f"Answer error: {e}")
                # More detailed error message
                await TelegramClient.send_message(
                    chat_id, 
                    "Произошла ошибка при ответе на ваш вопрос. Возможно, информация о компании не была правильно загружена. "
                    "Пожалуйста, попробуйте заново отправить ссылку через /start example.com"
                )

    except Exception as e:
        logger.error(f"Process error: {e}")
        await TelegramClient.send_message(chat_id, "Возникла внутренняя ошибка. Пожалуйста, попробуйте позже.")


@app.post("/webhook")
async def telegram_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    try:
        # Логирование всех заголовков запроса
        headers = dict(request.headers.items())
        logger.info(f"Received webhook request with headers: {headers}")
        
        # Получаем тело запроса
        try:
            body = await request.body()
            logger.info(f"Raw request body: {body}")
            update = await request.json()
            logger.info(f"Parsed update: {update}")
        except Exception as e:
            logger.error(f"Error parsing request: {e}")
            return {"status": "error", "error": f"Could not parse JSON: {e}"}
            
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")

        if not chat_id:
            logger.warning("No chat_id found in the update")
            return {"status": "error", "error": "No chat_id found"}

        text = message.get("text", "").strip()
        logger.info(f"Received message: {text} from chat_id: {chat_id}")

        # Process the message through our parsing function first
        # This handles all link formats and empty /start commands
        try:
            parsed_data = await parse_url_from_message(text, chat_id)
            background_tasks.add_task(process_message, chat_id, parsed_data, db)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Parse error: {e}")
            await TelegramClient.send_message(
                chat_id,
                "Возникла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте снова."
            )
            return {"status": "error"}

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)