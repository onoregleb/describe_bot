"""
Script to manually set up the Telegram webhook.
Run this script to update the webhook URL for your bot.
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

async def setup_webhook():
    try:
        logger.info(f"Setting webhook to URL: {WEBHOOK_URL}")
        response = await TelegramClient.set_webhook()
        logger.info(f"Webhook setup response: {response}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

async def delete_webhook():
    try:
        logger.info("Deleting existing webhook")
        response = await TelegramClient.delete_webhook()
        logger.info(f"Webhook deletion response: {response}")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "delete":
        # Delete the webhook
        asyncio.run(delete_webhook())
    else:
        # Set the webhook
        asyncio.run(setup_webhook()) 