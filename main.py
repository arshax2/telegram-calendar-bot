import os
import time
import pytz
import requests
from datetime import datetime
from persiantools.jdatetime import JalaliDate
from keep_alive import keep_alive

# ─── CONFIG ───
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_IDS = ["@as1signal", "@armandoviz", "@WWForex2008"]
POST_HOUR = 11
POST_MINUTE = 59
TIMEZONE = pytz.timezone("Europe/Istanbul")

# ─── Build today's formatted message ───
def get_today_info():
    now = datetime.now(TIMEZONE)
    miladi = now.strftime("%-d %B %Y")

    shamsi = JalaliDate(now)
    weekday_str = shamsi.strftime('%A')
    shamsi_str = f"{shamsi.day} {shamsi.strftime('%B')} {shamsi.year}"
    shamsi_key = f"{shamsi.year}-{shamsi.month:02d}-{shamsi.day:02d}"

    hejri = requests.get(f"https://api.keybit.ir/convert/date?date={shamsi_key}").json()
    hejri_str = hejri["result"]["hijri"]["date"]

    message = f"""📆 **تاریخ امروز – {weekday_str}**

☀️ **شمسی:** `{shamsi_str}`
📅 **میلادی:** `{miladi}`
🌙 **قمری:** `{hejri_str}`"""

    try:
        response = requests.get(f"https://api.keybit.ir/date?date={shamsi_key}")
        if response.status_code == 200:
            result = response.json().get("result", {})
            desc = result.get("description")
            is_holiday = result.get("holiday", False)

            if desc:
                message += f"\n\n🎉 **مناسبت:** {desc}"
            if is_holiday:
                message += f"\n⛱ تعطیل رسمی است"
    except Exception as e:
        print(f"⚠️ Error fetching calendar: {e}")

    return message

# ─── Send to all channels ───
def send_to_telegram(text):
    for chat_id in CHANNEL_IDS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(url, json=payload)
            print(f"✅ Sent to {chat_id}: {r.status_code}")
        except Exception as e:
            print(f"❌ Failed to send to {chat_id}: {e}")

# ─── Start web server ───
keep_alive()

# ─── Daily Loop ───
while True:
    now = datetime.now(TIMEZONE)
    if now.hour == POST_HOUR and now.minute == POST_MINUTE:
        print("📤 Posting today's date...")
        msg = get_today_info()
        send_to_telegram(msg)
        time.sleep(60)
    else:
        time.sleep(30)
