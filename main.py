"""
Telegram Calendar Bot
Posts today’s Shamsi / Miladi / Hijri date (plus holiday info) to TG channels.
Robust against API failures, keeps scheduler alive, and friendly to Fly.io.
"""

import os
import threading
import time
from datetime import datetime

import pytz
import requests
from flask import Flask
from persiantools.jdatetime import JalaliDate

# ───────────────────────────
# CONFIGURATION
# ───────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")          # fly secrets set BOT_TOKEN=123:ABC…
CHANNEL_IDS = ["@as1signal", "@armandoviz", "@WWForex2008"]

POST_HOUR   = 12                              # Europe/Istanbul time
POST_MINUTE = 45
TZ          = pytz.timezone("Europe/Istanbul")

PORT        = int(os.getenv("PORT", 8080))    # Fly injects $PORT
HTTP_TIMEOUT = 6                              # seconds

# ───────────────────────────
# FLASK health-check
# ───────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Telegram-calendar-bot is running"

# ───────────────────────────
# UTILITIES
# ───────────────────────────
def safe_get_json(url: str):
    """GET url ➜ json or None (never raises)."""
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        return r.json() if r.ok else None
    except Exception as e:
        print(f"⚠️  GET {url} failed:", e)
        return None

def build_today_message() -> str:
    now = datetime.now(TZ)
    miladi = now.strftime("%-d %B %Y")

    shamsi      = JalaliDate(now)
    weekday_fa  = shamsi.strftime('%A')
    shamsi_s    = f"{shamsi.day} {shamsi.strftime('%B')} {shamsi.year}"
    key         = f"{shamsi.year}-{shamsi.month:02d}-{shamsi.day:02d}"

    hejri_s = "نامشخص"
    hijri_api = safe_get_json(f"https://api.keybit.ir/convert/date?date={key}")
    if hijri_api and hijri_api.get("result"):
        hejri_s = hijri_api["result"]["hijri"]["date"]

    msg = (
        f"📆 **تاریخ امروز – {weekday_fa}**\n\n"
        f"☀️ **شمسی:** `{shamsi_s}`\n"
        f"📅 **میلادی:** `{miladi}`\n"
        f"🌙 **قمری:** `{hejri_s}`"
    )

    # Optional holiday info
    info_api = safe_get_json(f"https://api.keybit.ir/date?date={key}")
    if info_api and info_api.get("result"):
        res = info_api["result"]
        if res.get("description"):
            msg += f"\n\n🎉 **مناسبت:** {res['description']}"
        if res.get("holiday"):
            msg += "\n⛱ امروز تعطیل رسمی است"

    return msg

def broadcast(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chat_id in CHANNEL_IDS:
        try:
            r = requests.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=HTTP_TIMEOUT
            )
            if r.status_code != 200:
                print(f"✖️  TG error {r.status_code} for {chat_id}: {r.text[:120]}")
            else:
                print(f"→ Sent to {chat_id}")
        except Exception as e:
            print(f"✖️  Couldn’t send to {chat_id}: {e}")

# ───────────────────────────
# SCHEDULER (never dies)
# ───────────────────────────
def poster_loop():
    while True:
        try:
            now = datetime.now(TZ)
            if now.hour == POST_HOUR and now.minute == POST_MINUTE:
                print("📤 Posting today’s calendar …")
                broadcast(build_today_message())
                time.sleep(60)      # avoid duplicates
            else:
                time.sleep(20)
        except Exception as e:
            # Log and keep looping
            print("💥 Scheduler crash:", e)

# ───────────────────────────
# MAIN
# ───────────────────────────
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN secret missing!")

    threading.Thread(target=poster_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
