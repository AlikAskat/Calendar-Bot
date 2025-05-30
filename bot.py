"""
Calendar Bot
Version: 1.0.19
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
__version__ = '1.0.19'
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

# Основной код продолжает...