import os
import requests

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram_message(text: str, parse_mode: str = "Markdown"):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("[WARN] Telegram env not set, skip sending.")
        return

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print("[WARN] Telegram send failed:", resp.text)
        else:
            print("[INFO] Telegram sent.")
    except Exception as e:
        print("[WARN] Telegram exception:", e)
