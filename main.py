import asyncio
import logging
import re
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from config import TELEGRAM_BOT_TOKEN
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


async def init_bot():
    """Инициализация бота при запуске"""
    # Создаем таблицы при запуске
    create_tables()
    
    # Удаляем webhook, если он был настроен ранее
    try:
        webhook_info = await TelegramClient.get_webhook_info()
        current_url = webhook_info.get('result', {}).get('url', '')
        
        if current_url:
            await TelegramClient.delete_webhook()
            logger.info(f"Deleted previous webhook: {current_url}")
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        
    logger.info("Bot initialized for polling mode")


async def process_updates():
    """Обработка обновлений через polling"""
    db = next(get_db())
    
    try:
        # Получаем обновления через polling
        updates = await TelegramClient.get_updates(timeout=10)
        
        for update in updates:
            # Создаем задачу для обработки каждого обновления
            asyncio.create_task(handle_update(update, db))
    except Exception as e:
        logger.error(f"Error processing updates: {e}")
    finally:
        db.close()


async def handle_update(update: Dict[str, Any], db: Session):
    """Обработка одного обновления"""
    try:
        message = update.get("message", {})
        if not message:
            return
            
        chat_id = message.get("chat", {}).get("id")
        if not chat_id:
            return
            
        # Обрабатываем сообщение
        parsed_data = await parse_message(message)
        await process_message(chat_id, parsed_data, db)
    except Exception as e:
        logger.error(f"Error handling update: {e}")


async def parse_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Парсинг сообщения от пользователя"""
    result = {}
    
    if "text" not in message:
        return result
        
    text = message["text"]
    chat_id = message.get("chat", {}).get("id")
    
    if not chat_id:
        return result
    
    # Обрабатываем команду /start
    if text.startswith("/start"):
        if len(text) <= 6:
            # Пустая команда /start
            result["type"] = "start_empty"
        else:
            # Команда /start с параметрами
            url_data = await parse_url_from_message(text[7:], chat_id)
            if url_data:
                result.update(url_data)
    else:
        # Обычное сообщение
        url_data = await parse_url_from_message(text, chat_id)
        if url_data:
            result.update(url_data)
        else:
            # Вопрос о компании
            result["query"] = text
    
    return result


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


async def main():
    """Основная функция запуска бота"""
    # Инициализируем бота
    await init_bot()
    
    logger.info("Starting bot in polling mode with 1 second delay")
    
    # Бесконечный цикл polling
    while True:
        try:
            # Обрабатываем обновления
            await process_updates()
            
            # Задержка 1 секунда между запросами
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            # В случае ошибки делаем небольшую паузу
            await asyncio.sleep(5)


if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())