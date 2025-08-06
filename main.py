"""
Telegram Calendar Bot
• Sends today’s Shamsi / Miladi / Hijri date (and holidays) to a list of channels
• Stays alive on Fly.io by exposing a tiny Flask web-server on PORT (8080 by default)
"""

import os
import threading
import time
from datetime import datetime

import pytz
import requests
from flask import Flask
from persiantools.jdatetime import JalaliDate

# ────────────────────────────
# CONFIG
# ────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")              # set with: fly secrets set BOT_TOKEN=123:ABC…
CHANNEL_IDS = ["@as1signal", "@armandoviz", "@WWForex2008"]

POST_HOUR   = 12                                  # Istanbul time
POST_MINUTE = 15
TIMEZONE    = pytz.timezone("Europe/Istanbul")

PORT        = int(os.getenv("PORT", 8080))        # Fly.io sets $PORT automatically

# ────────────────────────────
# FLASK “keep-alive” ENDPOINT
# ────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Telegram-calendar-bot is running"

# ────────────────────────────
# MESSAGE BUILDERS
# ────────────────────────────
def build_today_message() -> str:
    now      = datetime.now(TIMEZONE)
    miladi   = now.strftime("%-d %B %Y")

    shamsi   = JalaliDate(now)
    weekday  = shamsi.strftime('%A')
    shamsi_s = f"{shamsi.day} {shamsi.strftime('%B')} {shamsi.year}"
    shamsi_key = f"{shamsi.year}-{shamsi.month:02d}-{shamsi.day:02d}"

    hejri    = requests.get(f"https://api.keybit.ir/convert/date?date={shamsi_key}").json()
    hejri_s  = hejri["result"]["hijri"]["date"]

    msg = (
        f"📆 **تاریخ امروز – {weekday}**\n\n"
        f"☀️ **شمسی:** `{shamsi_s}`\n"
        f"📅 **میلادی:** `{miladi}`\n"
        f"🌙 **قمری:** `{hejri_s}`"
    )

    # check for official holidays / descriptions
    try:
        r = requests.get(f"https://api.keybit.ir/date?date={shamsi_key}")
        if r.ok:
            res        = r.json().get("result", {})
            desc       = res.get("description")
            is_holiday = res.get("holiday", False)
            if desc:
                msg += f"\n\n🎉 **مناسبت:** {desc}"
            if is_holiday:
                msg += "\n⛱ تعطیل رسمی است"
    except Exception as err:
        print("⚠️  Calendar API error:", err)

    return msg

def broadcast(text: str):
    for chat_id in CHANNEL_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r   = requests.post(url, json={"chat_id": chat_id,
                                           "text": text,
                                           "parse_mode": "Markdown"})
            print(f"→ {chat_id}: {r.status_code}")
        except Exception as err:
            print(f"✖️  Couldn’t send to {chat_id}: {err}")

# ────────────────────────────
# SCHEDULER THREAD
# ────────────────────────────
def poster_loop():
    while True:
        now = datetime.now(TIMEZONE)
        if now.hour == POST_HOUR and now.minute == POST_MINUTE:
            print("📤 Posting today’s calendar …")
            broadcast(build_today_message())
            time.sleep(60)          # wait a minute so we don’t double-post
        else:
            time.sleep(20)

# ────────────────────────────
# ENTRY-POINT
# ────────────────────────────
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable not set!")

    # start the poster thread
    threading.Thread(target=poster_loop, daemon=True).start()

    # run Flask in the main thread (health-checks succeed -> no restarts)
    app.run(host="0.0.0.0", port=PORT)
