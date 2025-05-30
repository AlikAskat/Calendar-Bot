"""
Calendar Bot
Version: 1.0.21
Last Updated: 2025-05-30
Author: AlikAskat
"""

import os
import json
import logging
from datetime import datetime, timedelta
import calendar
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.api_core import retry
import googleapiclient.errors
import asyncio

# Версия бота
__version__ = '1.0.21'
logger = logging.getLogger(__name__)

# Настройка логирования с информацией о версии
logging.basicConfig(
    format="%(asctime)s - [v" + __version__ + "] - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

# Глобальные переменные
SCOPES = ['https://www.googleapis.com/auth/calendar'] 
TIMEZONE = 'Asia/Yekaterinburg'
user_states = {}
user_data = {}

# Лог состояния запуска
logger.info(f"Запуск Calendar Bot v{__version__}")

# Убедитесь, что переменные окружения правильные
if not os.getenv("RENDER_EXTERNAL_URL"):
    logger.error("RENDER_EXTERNAL_URL не установлен. Бот не сможет работать через вебхуки.")

async def main_async():
    """Асинхронная основная функция"""
    logger.info(f"Запуск Calendar Bot v{__version__}")

    # Создаем приложение 
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Удаляем старый вебхук
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

    # Получаем домен Render
    domain = os.getenv("RENDER_EXTERNAL_URL")
    if not domain:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return

    # Настройки для вебхука
    port = int(os.getenv("PORT", 10000))  # Стандартный порт Render
    webhook_url = f"{domain}/webhook/{TOKEN}"

    logger.info(f"Настройка вебхука: {webhook_url}")
    
    # Запускаем вебхук
    await application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"/webhook/{TOKEN}",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

def main():
    """Основная функция"""
    try:
        asyncio.run(main_async())
    except RuntimeError as e:
        logger.error(f"Ошибка событийного цикла: {e}")
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        asyncio.run(main_async())

if __name__ == "__main__":
    main()