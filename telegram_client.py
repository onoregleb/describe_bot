import httpx
import logging
from typing import Optional, Dict, Any, List
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

class TelegramClient:
    API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    # Для хранения последнего полученного update_id
    last_update_id = 0
    
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
    
    @classmethod
    async def get_updates(cls, timeout: int = 30) -> List[Dict[str, Any]]:
        """Get updates from Telegram API using long polling
        
        Args:
            timeout: Timeout in seconds for long polling
            
        Returns:
            List of update objects
        """
        url = f"{cls.API_URL}/getUpdates"
        
        params = {
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        
        # Если у нас уже есть last_update_id, запрашиваем только новые сообщения
        if cls.last_update_id > 0:
            params["offset"] = cls.last_update_id + 1
        
        try:
            async with httpx.AsyncClient(timeout=timeout+10) as client:
                response = await client.get(url, params=params)
                result = response.json()
                
                if result.get("ok") and result.get("result"):
                    updates = result["result"]
                    
                    # Обновляем last_update_id
                    if updates:
                        cls.last_update_id = max(update["update_id"] for update in updates)
                    
                    return updates
                return []
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []