import asyncio
import logging
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
from typing import Dict, Any, Optional

from config import TELEGRAM_BOT_TOKEN
from database import get_db, create_tables
from telegram_client import TelegramClient
from services import (
    parse_url_from_message,
    save_url_to_db,
    get_latest_url,
    search_yandex,
    extract_first_url,
    fetch_webpage_content,
    clean_html_content,
    generate_ai_description
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="URL Description Bot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    # Set webhook on startup
    try:
        webhook_response = await TelegramClient.set_webhook()
        logger.info(f"Webhook setup response: {webhook_response}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

# Remove webhook on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    try:
        webhook_response = await TelegramClient.delete_webhook()
        logger.info(f"Webhook deletion response: {webhook_response}")
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")

# Background task to process the message and generate response
async def process_message(chat_id: int, parsed_data: Dict[str, Any], db: Session):
    try:
        # If URL is provided, save it to DB
        if "site" in parsed_data:
            site = parsed_data["site"]
            try:
                await save_url_to_db(db, chat_id, site)
            except Exception as e:
                logger.error(f"Error saving URL to DB: {e}")
                # Continue processing even if DB save fails
            
        # If no URL or just a query, get the latest URL from DB
        if "site" not in parsed_data or parsed_data.get("type") == "queryOnly":
            # Get the latest URL from database
            latest_url = await get_latest_url(db, chat_id)
            
            if not latest_url:
                await TelegramClient.send_message(
                    chat_id, 
                    "Пожалуйста, сначала укажите URL."
                )
                return
                
            parsed_data["formattedUrl"] = latest_url
        else:
            parsed_data["formattedUrl"] = parsed_data["site"]
        
        # Get query (if any)
        query = parsed_data.get("query", "")
        
        # Log the URL and query being searched
        logger.info(f"Searching for URL: {parsed_data['formattedUrl']}, Query: {query or 'None'}")
        
        # Search Yandex
        try:
            xml_response = await search_yandex(parsed_data["formattedUrl"], query)
        except Exception as e:
            logger.error(f"Error searching Yandex: {e}")
            await TelegramClient.send_message(
                chat_id, 
                "Произошла ошибка при поиске информации. Пожалуйста, проверьте URL и попробуйте снова."
            )
            return
        
        # Extract first URL from search results
        try:
            urls = await extract_first_url(xml_response)
        except Exception as e:
            logger.error(f"Error extracting URL: {e}")
            await TelegramClient.send_message(
                chat_id, 
                "Не удалось обработать результаты поиска. Возможно, проблема с доступом к сайту."
            )
            return
        
        if not urls:
            # Give a more informative error message
            await TelegramClient.send_message(
                chat_id, 
                f"Не удалось найти информацию по указанному URL: {parsed_data['formattedUrl']}. Пожалуйста, убедитесь, что сайт существует и доступен."
            )
            return
            
        # Log the URL we're going to fetch content from
        logger.info(f"Fetching content from URL: {urls[0]}")
        
        # Fetch content from the first URL
        try:
            content = await fetch_webpage_content(urls[0])
        except Exception as e:
            logger.error(f"Error fetching webpage: {e}")
            await TelegramClient.send_message(
                chat_id, 
                "Не удалось получить содержимое страницы. Возможно, сайт недоступен."
            )
            return
        
        # Clean HTML content
        try:
            cleaned_text = await clean_html_content(content)
        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            await TelegramClient.send_message(
                chat_id, 
                "Не удалось обработать содержимое страницы."
            )
            return
        
        if not cleaned_text:
            await TelegramClient.send_message(
                chat_id, 
                "Не удалось получить содержимое страницы."
            )
            return
            
        # Generate AI description
        try:
            description = await generate_ai_description(cleaned_text)
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            await TelegramClient.send_message(
                chat_id, 
                "Не удалось сгенерировать описание."
            )
            return
        
        # Send description to user
        await TelegramClient.send_message(chat_id, description)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await TelegramClient.send_message(
            chat_id, 
            "Произошла ошибка при обработке сообщения."
        )

# Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        update = await request.json()
        logger.info(f"Received update: {update}")
        
        # Process only messages
        if "message" not in update:
            return {"status": "ok", "message": "No message in update"}
            
        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        
        if not chat_id:
            return {"status": "error", "message": "No chat ID found"}
            
        # Check if message has text
        if "text" not in message:
            await TelegramClient.send_message(
                chat_id, 
                "Сообщение должно содержать исключительно текст"
            )
            return {"status": "ok", "message": "No text in message"}
            
        text = message["text"]
        
        # If it's a /start command
        if text == "/start":
            await TelegramClient.send_message(
                chat_id,
                "Привет, укажите url в одной строке с командой /start"
            )
            return {"status": "ok", "message": "Start command received"}
            
        # If it's a /start command with parameters
        if text.startswith("/start "):
            # Remove the /start part and process the rest
            text = text[7:].strip()
            
        # Parse URL and query from message
        try:
            parsed_data = await parse_url_from_message(text, chat_id)
            
            # Process the message in background
            background_tasks.add_task(
                process_message, 
                chat_id, 
                parsed_data, 
                db
            )
            
            return {"status": "ok", "message": "Processing message"}
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await TelegramClient.send_message(
                chat_id,
                "Произошла ошибка при обработке сообщения."
            )
            return {"status": "error", "message": str(e)}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"status": "error", "message": str(e)}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 