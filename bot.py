"""
Calendar Bot
Version: 1.0.15
Last Updated: 2025-05-30 19:00
Author: AlikAskat
"""

import os
import logging
import threading
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

__version__ = '1.0.15'
logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s - [v" + __version__ + "] - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

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
    await update.message.reply_text(f"Привет! Я Calendar Bot v{__version__}")

def main():
    logger.info(f"Запуск Calendar Bot v{__version__}")

    # Обработчики сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Health-check server
    health_thread = threading.Thread(target=run_health_check_server)
    health_thread.daemon = True
    health_thread.start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        sys.exit(1)
    webhook_url = f"{app_url}/webhook/{TOKEN}"

    # Webhook-запуск, без asyncio.run!
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()