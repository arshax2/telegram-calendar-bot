# main.py
import threading
import datetime
import requests
import os
import time
import logging
from flask import Flask

import telegram

# Telegram bot token and channel ID from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g., "@yourchannel" or channel ID as string
POST_HOUR = 11
POST_MINUTE = 15

# Logging
logging.basicConfig(level=logging.INFO)

# Flask app to keep Fly.io app alive
app = Flask(__name__)


@app.route("/")
def index():
    return "✅ Telegram bot is running."


def get_today_info():
    try:
        now = datetime.datetime.now()
        shamsi_key = now.strftime("%Y-%m-%d")

        logging.info(f"📡 Fetching Hijri date for {shamsi_key}")
        response = requests.get(f"https://api.keybit.ir/convert/date?date={shamsi_key}")

        if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("application/json"):
            hejri = response.json()
        else:
            logging.warning(f"⚠️ Unexpected API response: {response.status_code} - {response.text}")
            hejri = {"result": {"hijri": {"year": "?", "month": "?", "day": "?"}}}

    except Exception as e:
        logging.error(f"❌ Failed to fetch date from Keybit API: {e}")
        hejri = {"result": {"hijri": {"year": "?", "month": "?", "day": "?"}}}

    # Build message
    now = datetime.datetime.now()
    gregorian = now.strftime("%A, %d %B %Y")

    hijri = hejri["result"]["hijri"]
    hijri_str = f"{hijri['day']} {hijri['month']} {hijri['year']}"

    return f"📅 Today is {gregorian}\n🕌 Hijri: {hijri_str}"


def post_to_channel(text):
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        bot.send_message(chat_id=CHANNEL_ID, text=text)
        logging.info("✅ Message posted to Telegram channel.")
    except Exception as e:
        logging.error(f"❌ Failed to send message to Telegram: {e}")


def daily_poster():
    while True:
        now = datetime.datetime.now()
        if now.hour == POST_HOUR and now.minute == POST_MINUTE:
            logging.info("⏰ Time to post daily message.")
            msg = get_today_info()
            post_to_channel(msg)
            time.sleep(65)  # Wait to avoid double posting
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    # Start poster thread
    threading.Thread(target=daily_poster, daemon=True).start()

    # Run Flask app for Fly.io
    app.run(host="0.0.0.0", port=8080)
