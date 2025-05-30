"""
Calendar Bot
Version: 1.0.15q
Last Updated: 2025-05-30 16:01
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
import signal
import sys

# Версия бота
__version__ = '1.0.15q'
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

# Состояния пользователей и их данные
user_states = {}
user_data = {}

def get_google_calendar_service():
    """Получение сервиса Google Calendar с использованием Service Account"""
    try:
        credentials_json = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json:
            logger.error("Переменная GOOGLE_CREDENTIALS не установлена")
            return None

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json), scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Ошибка при получении сервиса календаря: {e}")
        return None

def create_calendar_keyboard(year, month):
    """Создает клавиатуру-календарь"""
    month_names = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    keyboard = [
        [InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="ignore")]
    ]
    # Дни недели
    keyboard.append([InlineKeyboardButton(d, callback_data="ignore") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])
    # Календарь
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(row)
    # Навигация
    prev_month = month - 1 if month > 1 else 12
    next_month = month + 1 if month < 12 else 1
    prev_year = year if month > 1 else year - 1
    next_year = year if month < 12 else year + 1

    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f"calendar_{prev_year}_{prev_month}"),
        InlineKeyboardButton("Отмена", callback_data="cancel"),
        InlineKeyboardButton(">>", callback_data=f"calendar_{next_year}_{next_month}")
    ])
    return InlineKeyboardMarkup(keyboard)

def create_time_keyboard():
    """Создает клавиатуру для выбора времени"""
    keyboard = []
    for hour in range(0, 24, 4):
        row = []
        for h in range(hour, min(hour + 4, 24)):
            row.append(InlineKeyboardButton(f"{h:02d}:00", callback_data=f"time_{h:02d}_00"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    """Создает основную клавиатуру"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("🔄 Перезапуск"), KeyboardButton("❓ Помощь")]
    ], resize_keyboard=True)

@retry.Retry(predicate=retry.if_transient_error)
def add_event_to_calendar(title: str, start_time: datetime) -> str:
    """Добавляет событие в Google Calendar с поддержкой повторных попыток"""
    try:
        service = get_google_calendar_service()
        if not service:
            return ""
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': (start_time + timedelta(hours=1)).isoformat(),
                'timeZone': TIMEZONE,
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"https://calendar.google.com/calendar/event?eid={event['id']}"
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_states[user.id] = "main_menu"
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n"
        "Я помогу вам управлять задачами в календаре.\n"
        "Нажмите '➕ Добавить задачу' чтобы начать, или '❓ Помощь' для получения справки.",
        reply_markup=get_main_keyboard()
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по командам"""
    help_text = (
        "📝 *Справка по командам:*\n"
        "➕ *Добавить задачу* - создание новой задачи:\n"
        "   1. Введите название задачи\n"
        "   2. Выберите дату в календаре\n"
        "   3. Выберите время\n"
        "   4. Получите ссылку на событие в Google Calendar\n"
        "🔄 *Перезапуск* - очистка чата и перезапуск бота\n"
        "❓ *Помощь* - показать это сообщение\n"
        "Чтобы начать, нажмите '➕ Добавить задачу'"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очищает чат и перезапускает бота"""
    user_id = update.effective_user.id
    user_states[user_id] = "main_menu"
    user_data[user_id] = {}
    await update.message.reply_text(
        "🔄 Бот перезапущен!\n"
        "Все данные очищены. Можно начать заново:",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    state = user_states.get(user_id, "main_menu")

    if text == "➕ Добавить задачу":
        user_states[user_id] = "awaiting_title"
        await update.message.reply_text("Введите название задачи:")
        return
    elif state == "awaiting_title":
        user_data[user_id] = {"title": text}
        now = datetime.now()
        user_states[user_id] = "awaiting_date"
        await update.message.reply_text(
            f"Задача: {text}\nТеперь выберите дату в календаре:",
            reply_markup=create_calendar_keyboard(now.year, now.month)
        )
    elif text == "❓ Помощь":
        await show_help(update, context)
    elif text == "🔄 Перезапуск":
        await restart(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации или нажмите '❓ Помощь' для получения справки:",
            reply_markup=get_main_keyboard()
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback запросов"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("calendar_"):
        _, year, month = query.data.split("_")
        await query.message.reply_text("Выберите дату:", reply_markup=create_calendar_keyboard(int(year), int(month)))
    elif query.data.startswith("date_"):
        _, year, month, day = query.data.split("_")
        selected_date = f"{day}.{month}.{year}"
        if user_id not in user_data:
            user_data[user_id] = {"title": "Новая задача"}
        user_data[user_id]["date"] = {"year": int(year), "month": int(month), "day": int(day)}
        await query.message.reply_text(
            f"Дата: {selected_date}\nВыберите время:",
            reply_markup=create_time_keyboard()
        )
        user_states[user_id] = "awaiting_time"
    elif query.data.startswith("time_"):
        _, hour, minute = query.data.split("_")
        if user_id not in user_data:
            await query.message.reply_text(
                "Произошла ошибка. Начните сначала:",
                reply_markup=get_main_keyboard()
            )
            return
        user_data[user_id]["time"] = f"{hour}:{minute}"
        title = user_data[user_id].get("title", "Новая задача")
        date = user_data[user_id]["date"]
        start_time = datetime(
            date["year"], date["month"], date["day"],
            int(hour), int(minute)
        )
        calendar_url = add_event_to_calendar(title, start_time)
        if calendar_url:
            await query.message.reply_text(
                f"✅ Задача успешно добавлена!\n"
                f"📝 {title}\n"
                f"📅 {start_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"🔗 Посмотреть в календаре: {calendar_url}",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.message.reply_text(
                "❌ Произошла ошибка при добавлении задачи в календарь.\n"
                "Попробуйте еще раз:",
                reply_markup=get_main_keyboard()
            )
        user_states[user_id] = "main_menu"
        user_data[user_id] = {}
    elif query.data == "cancel":
        await query.message.reply_text(
            "Действие отменено. Используйте кнопки меню:",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "main_menu"
        user_data[user_id] = {}

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже или нажмите '🔄 Перезапуск'.",
            reply_markup=get_main_keyboard()
        )

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"Получен сигнал: {signum}")
    sys.exit(0)

def main() -> None:
    """Основная функция"""
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
        asyncio.run(application.bot.delete_webhook(drop_pending_updates=True))
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
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

# --- Установка обработчиков сигналов --- #
if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Запускаем бота
    main()