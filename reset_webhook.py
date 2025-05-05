#!/usr/bin/env python3
"""
Script to reset the Telegram webhook with the correct path.
This will delete the existing webhook and set it again with the /webhook path included.
"""

import asyncio
import logging
from telegram_client import TelegramClient
from config import WEBHOOK_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def reset_webhook():
    try:
        # First delete the existing webhook
        logger.info("Deleting existing webhook")
        delete_response = await TelegramClient.delete_webhook()
        logger.info(f"Webhook deletion response: {delete_response}")
        
        # Then set the new webhook with the correct path
        logger.info(f"Setting webhook to URL: {WEBHOOK_URL}")
        set_response = await TelegramClient.set_webhook()
        logger.info(f"Webhook setup response: {set_response}")
        
        if set_response.get("ok"):
            logger.info("Webhook successfully reset with the correct path")
        else:
            logger.error(f"Failed to set webhook: {set_response}")
    except Exception as e:
        logger.error(f"Error resetting webhook: {e}")

if __name__ == "__main__":
    asyncio.run(reset_webhook()) 