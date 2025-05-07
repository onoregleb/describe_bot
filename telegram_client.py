import httpx
import logging
from typing import Optional, Dict, Any
from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL

logger = logging.getLogger(__name__)

class TelegramClient:
    API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    @classmethod
    async def send_message(cls, chat_id: int, text: str) -> Dict[str, Any]:
        """Send a message to a chat via Telegram API"""
        url = f"{cls.API_URL}/sendMessage"
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            return response.json()
    
    @classmethod
    async def get_webhook_info(cls) -> Dict[str, Any]:
        """Get information about the current webhook"""
        url = f"{cls.API_URL}/getWebhookInfo"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()
    
    @classmethod
    async def set_webhook(cls) -> Dict[str, Any]:
        """Set the webhook for the Telegram bot"""
        url = f"{cls.API_URL}/setWebhook"
        
        # Логируем точный URL для отладки
        webhook_url = WEBHOOK_URL.strip()
        logger.debug(f"Setting webhook with URL: '{webhook_url}'")
        logger.debug(f"WEBHOOK_URL from env: '{WEBHOOK_URL}'")
        logger.debug(f"Environment type: {type(WEBHOOK_URL)}")
        
        data = {
            "url": webhook_url,
            "allowed_updates": ["message"]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Sending webhook config: {data}")
                response = await client.post(url, json=data)
                result = response.json()
                logger.debug(f"Webhook response: {result}")
                return result
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            raise
    
    @classmethod
    async def delete_webhook(cls) -> Dict[str, Any]:
        """Delete the webhook for the Telegram bot"""
        url = f"{cls.API_URL}/deleteWebhook"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url)
            return response.json()