import httpx
from typing import Optional, Dict, Any
from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL

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
    async def set_webhook(cls) -> Dict[str, Any]:
        """Set the webhook for the Telegram bot"""
        url = f"{cls.API_URL}/setWebhook"
        
        data = {
            "url": WEBHOOK_URL,
            "allowed_updates": ["message"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            return response.json()
    
    @classmethod
    async def delete_webhook(cls) -> Dict[str, Any]:
        """Delete the webhook for the Telegram bot"""
        url = f"{cls.API_URL}/deleteWebhook"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url)
            return response.json() 