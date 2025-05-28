"""
Calendar Bot
Version: 1.0.1
Last Updated: 2025-05-28 17:40
Author: AlikAskat
"""

import os
import json
import logging
import signal
import sys
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
import calendar
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.api_core import retry
import googleapiclient.errors

# Версия бота
__version__ = '1.0.1'
logger = logging.getLogger(__name__)

# Настройка логирования с информацией о версии
logging.basicConfig(
    format="%(asctime)s - [v" + __version__ + "] - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

# Глобальные переменные
SCOPES = ['https://www.googleapis.com/auth/calendar']
TIMEZONE = 'Asia/Almaty'

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            response = f"OK - Calendar Bot v{__version__}"
            self.wfile.write(response.encode('utf-8'))

def run_health_check_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    server.serve_forever()

def signal_handler(signum, frame):
    logger.info(f'Получен сигнал: {signum}')
    sys.exit(0)

async def main():
    """Основная функция"""
    logger.info(f"Запуск Calendar Bot v{__version__}")
    
    # Установка обработчиков сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Запуск сервера проверки здоровья
    health_thread = threading.Thread(target=run_health_check_server)
    health_thread.daemon = True
    health_thread.start()
    
    # Инициализация приложения
    application = Application.builder().token(TOKEN).build()

    # Настройки для webhook
    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return
    
    webhook_url = f"{app_url}/webhook/{TOKEN}"
    logger.info(f"Setting webhook URL: {webhook_url}")
    
    try:
        # Запускаем webhook
        await application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=f"webhook/{TOKEN}",
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске webhook: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)