"""
Calendar Bot
Version: 1.0.5
Last Updated: 2025-05-28 18:23
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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
from googleapiclient.errors import HttpError

# Версия бота
__version__ = '1.0.5'
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

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

def run_health_check_server():
    port = int(os.environ.get("HEALTH_CHECK_PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def signal_handler(signum, frame):
    logger.info(f'Получен сигнал: {signum}')
    sys.exit(0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Привет! Я Calendar Bot v{__version__}")

async def setup_webhook(app: Application, webhook_url: str) -> bool:
    """
    Настройка webhook с обработкой ошибок и повторными попытками
    """
    for _ in range(3):  # Попытка до 3 раз
        try:
            await app.bot.set_webhook(webhook_url)
            logger.info(f"Webhook успешно установлен на {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке webhook: {e}")
    return False

async def run_application():
    """
    Запуск приложения
    """
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем базовый обработчик
    application.add_handler(CommandHandler("start", start))

    # Настройки для webhook
    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return
    
    webhook_url = f"{app_url}/webhook/{TOKEN}"
    
    # Настройка webhook
    if not await setup_webhook(application, webhook_url):
        return
    
    # Запуск webhook
    async with application:
        await application.start()
        try:
            await application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=f"webhook/{TOKEN}",
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            await application.stop()

def main():
    """
    Основная функция
    """
    logger.info(f"Запуск Calendar Bot v{__version__}")
    
    # Установка обработчиков сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Запуск сервера проверки здоровья
    health_thread = threading.Thread(target=run_health_check_server)
    health_thread.daemon = True
    health_thread.start()
    
    # Запуск приложения
    try:
        asyncio.run(run_application())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()