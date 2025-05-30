"""
Calendar Bot
Version: 2.0.0
Last Updated: 2025-05-30
Author: AlikAskat
"""

import os
import logging
import signal
import sys
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from google.oauth2 import service_account
from googleapiclient.discovery import build

__version__ = '2.0.0'
logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s - [v" + __version__ + "] - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
TIMEZONE = 'Asia/Almaty'

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")
if not CALENDAR_ID:
    raise ValueError("Переменная GOOGLE_CALENDAR_ID не установлена!")

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_JSON, scopes=SCOPES)
    return build('calendar', 'v3', credentials=credentials)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            response = f"OK - Calendar Bot v{__version__}"
            self.wfile.write(response.encode('utf-8'))

def run_health_check_server():
    port = int(os.environ.get("HEALTH_CHECK_PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def signal_handler(signum, frame):
    logger.info(f'Получен сигнал: {signum}')
    sys.exit(0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Calendar Bot. Чтобы добавить задачу в Google Календарь, "
        "напиши команду:\n"
        "/addevent <название события> | <дата> | <время>\n"
        "Пример: /addevent Встреча с командой | 2025-06-01 | 15:00"
    )

async def addevent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = " ".join(context.args)
        if "|" not in text:
            await update.message.reply_text(
                "⚠️ Формат: /addevent <название> | <дата ГГГГ-ММ-ДД> | <время ЧЧ:ММ>\n"
                "Пример: /addevent Встреча | 2025-06-01 | 15:00"
            )
            return
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("⚠️ Ошибка: должно быть три параметра через |.")
            return
        summary, date_str, time_str = parts
        event_datetime = f"{date_str}T{time_str}:00"
        service = get_calendar_service()
        event = {
            'summary': summary,
            'start': {'dateTime': event_datetime, 'timeZone': TIMEZONE},
            'end': {'dateTime': event_datetime, 'timeZone': TIMEZONE},
        }
        created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        await update.message.reply_text(f"✅ Событие добавлено: {summary}\nhttps://calendar.google.com/calendar/u/0/r/eventedit/{created['id']}")
    except Exception as e:
        logger.error(f"Ошибка добавления события: {e}")
        await update.message.reply_text(f"Ошибка: {e}")

def main():
    logger.info(f"Запуск Calendar Bot v{__version__}")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    health_thread = threading.Thread(target=run_health_check_server)
    health_thread.daemon = True
    health_thread.start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addevent", addevent))

    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        sys.exit(1)
    webhook_url = f"{app_url}/webhook/{TOKEN}"

    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()