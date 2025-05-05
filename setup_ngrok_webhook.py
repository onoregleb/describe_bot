#!/usr/bin/env python3
import os
import json
import subprocess
import requests
import time
import signal
import sys
from config import TELEGRAM_BOT_TOKEN
import re

# Port where your FastAPI app is running
PORT = 8000

def get_ngrok_url():
    """Get the public URL from ngrok"""
    try:
        # Get the ngrok tunnel information
        response = requests.get("http://localhost:4040/api/tunnels")
        data = response.json()
        
        # Find the HTTPS tunnel
        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
                
        print("No HTTPS tunnel found")
        return None
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        return None

def set_telegram_webhook(url):
    """Set the Telegram webhook to the given URL"""
    webhook_url = f"{url}/webhook"
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    response = requests.post(api_url, json={"url": webhook_url})
    return response.json()

def start_ngrok():
    """Start ngrok in a subprocess"""
    try:
        # Start ngrok in a subprocess
        print(f"Starting ngrok on port {PORT}...")
        process = subprocess.Popen(
            ["ngrok", "http", str(PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for ngrok to start and get its URL
        print("Waiting for ngrok to start...")
        time.sleep(3)
        
        # Get the public URL
        public_url = get_ngrok_url()
        if not public_url:
            print("Failed to get ngrok URL")
            process.terminate()
            return None, None
            
        print(f"ngrok is running at: {public_url}")
        
        # Set the Telegram webhook
        webhook_response = set_telegram_webhook(public_url)
        print(f"Webhook setup response: {webhook_response}")
        
        if webhook_response.get("ok"):
            print(f"Webhook successfully set to: {public_url}/webhook")
            
            # Update the config.py file with the new webhook URL
            with open("config.py", "r") as f:
                config_content = f.read()
                
            # Find the WEBHOOK_URL line and replace it
            webhook_pattern = r'WEBHOOK_URL = os.getenv\("WEBHOOK_URL", ".*?"\)'
            config_content = re.sub(
                webhook_pattern,
                f'WEBHOOK_URL = os.getenv("WEBHOOK_URL", "{public_url}/webhook")',
                config_content
            )
            
            with open("config.py", "w") as f:
                f.write(config_content)
                
            print("Updated config.py with new webhook URL")
        else:
            print("Failed to set webhook")
            
        return process, public_url
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        return None, None

def signal_handler(sig, frame):
    """Handle Ctrl+C to clean up"""
    print("\nShutting down...")
    
    # Delete the webhook
    delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    response = requests.post(delete_url)
    print(f"Webhook deletion response: {response.json()}")
    
    # Exit
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check if ngrok is authenticated
    result = subprocess.run(["ngrok", "config", "check"], capture_output=True, text=True)
    if "error" in result.stdout.lower() or "authtoken" in result.stdout.lower():
        print("You need to authenticate ngrok with an authtoken.")
        print("Visit https://dashboard.ngrok.com/get-started/your-authtoken to get your token.")
        print("Then run: ngrok config add-authtoken YOUR_TOKEN")
        sys.exit(1)
    
    # Start ngrok and keep it running
    ngrok_process, public_url = start_ngrok()
    
    if ngrok_process and public_url:
        print("\nNgrok is running and webhook is set up.")
        print("Press Ctrl+C to stop ngrok and delete the webhook.")
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)
    else:
        print("Failed to start ngrok or set up webhook.") 