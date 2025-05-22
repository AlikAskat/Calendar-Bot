"""
Calendar Bot
Version: v25
Last update: 2025-05-22
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
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.api_core import retry
import googleapiclient.errors

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
            json.loads(credentials_json), scopes=SCOPES)
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Ошибка при получении сервиса календаря: {e}")
        return None

def create_calendar_keyboard(year: int, month: int):
    """Создает клавиатуру-календарь"""
    keyboard = []
    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    
    keyboard.append([InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="ignore")])
    keyboard.append([InlineKeyboardButton(d, callback_data="ignore") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])
    
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(row)
    
    nav_row = []
    prev_month = month - 1 if month > 1 else 12
    next_month = month + 1 if month < 12 else 1
    prev_year = year if month > 1 else year - 1
    next_year = year if month < 12 else year + 1
    
    nav_row.append(InlineKeyboardButton("<<", callback_data=f"calendar_{prev_year}_{prev_month}"))
    nav_row.append(InlineKeyboardButton("Отмена", callback_data="cancel"))
    nav_row.append(InlineKeyboardButton(">>", callback_data=f"calendar_{next_year}_{next_month}"))
    keyboard.append(nav_row)
    
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
    keyboard = [
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("🔄 Перезапуск"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
    except googleapiclient.errors.HttpError as e:
        logger.error(f"Ошибка Google Calendar API: {e}")
        return ""
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        return ""

def start(update: Update, context) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_states[user.id] = "main_menu"
    update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять задачами в календаре.\n"
        "Нажмите '➕ Добавить задачу' чтобы начать, или '❓ Помощь' для получения справки.",
        reply_markup=get_main_keyboard()
    )

def show_help(update: Update, context) -> None:
    """Показывает справку по командам"""
    help_text = (
        "📝 *Справка по командам:*\n\n"
        "➕ *Добавить задачу* - создание новой задачи:\n"
        "   1. Введите название задачи\n"
        "   2. Выберите дату в календаре\n"
        "   3. Выберите время\n"
        "   4. Получите ссылку на событие в Google Calendar\n\n"
        "🔄 *Перезапуск* - очистка чата и перезапуск бота\n\n"
        "❓ *Помощь* - показать это сообщение\n\n"
        "Чтобы начать, нажмите '➕ Добавить задачу'"
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def restart(update: Update, context) -> None:
    """Очищает чат и перезапускает бота"""
    user_id = update.effective_user.id
    user_states[user_id] = "main_menu"
    user_data[user_id] = {}
    
    update.message.reply_text(
        "🔄 Бот перезапущен!\n"
        "Все данные очищены. Можно начать заново:",
        reply_markup=get_main_keyboard()
    )

def handle_text(update: Update, context) -> None:
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    state = user_states.get(user_id, "main_menu")
    
    if text == "🔄 Перезапуск":
        restart(update, context)
        return
        
    elif text == "❓ Помощь":
        show_help(update, context)
        return
        
    elif text == "➕ Добавить задачу":
        update.message.reply_text(
            "Введите название задачи:"
        )
        user_states[user_id] = "awaiting_title"
        return

    if state == "awaiting_title":
        user_data[user_id] = {"title": text}
        now = datetime.now()
        update.message.reply_text(
            f"Задача: {text}\n"
            "Теперь выберите дату в календаре:",
            reply_markup=create_calendar_keyboard(now.year, now.month)
        )
        user_states[user_id] = "awaiting_date"
    else:
        update.message.reply_text(
            "Используйте кнопки меню для навигации или нажмите '❓ Помощь' для получения справки:",
            reply_markup=get_main_keyboard()
        )

def handle_callback(update: Update, context) -> None:
    """Обработчик callback запросов"""
    query = update.callback_query
    user_id = query.from_user.id
    
    query.answer()

    if query.data.startswith("calendar_"):
        _, year, month = query.data.split("_")
        query.edit_message_reply_markup(
            reply_markup=create_calendar_keyboard(int(year), int(month))
        )
        
    elif query.data.startswith("date_"):
        _, year, month, day = query.data.split("_")
        selected_date = f"{day}.{month}.{year}"
        if user_id not in user_data:
            user_data[user_id] = {"title": "Новая задача"}
        user_data[user_id]["date"] = {"year": int(year), "month": int(month), "day": int(day)}
        
        query.message.reply_text(
            f"Дата: {selected_date}\n"
            "Выберите время:",
            reply_markup=create_time_keyboard()
        )
        user_states[user_id] = "awaiting_time"
    
    elif query.data.startswith("time_"):
        _, hour, minute = query.data.split("_")
        if user_id not in user_data:
            query.message.reply_text(
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
            query.message.reply_text(
                f"✅ Задача успешно добавлена!\n\n"
                f"📝 {title}\n"
                f"📅 {start_time.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🔗 Посмотреть в календаре: {calendar_url}",
                reply_markup=get_main_keyboard()
            )
        else:
            query.message.reply_text(
                "❌ Произошла ошибка при добавлении задачи в календарь.\n"
                "Попробуйте еще раз:",
                reply_markup=get_main_keyboard()
            )
        
        user_states[user_id] = "main_menu"
        user_data[user_id] = {}
    
    elif query.data == "cancel":
        query.message.reply_text(
            "Действие отменено. Используйте кнопки меню:",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "main_menu"
        user_data[user_id] = {}

def error_handler(update: Update, context) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже или нажмите '🔄 Перезапуск'.",
            reply_markup=get_main_keyboard()
        )

def main() -> None:
    """Основная функция"""
    logger.info("Запуск бота")
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Добавляем обработчики
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", show_help))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    dp.add_error_handler(error_handler)

    # Настройки для webhook
    port = int(os.environ.get("PORT", "8443"))
    app_name = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_name:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return

    # Запускаем webhook
    updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{app_name}/{TOKEN}"
    )
    
    logger.info(f"Бот запущен и слушает на порту {port}")
    
    # Держим бота активным
    updater.idle()

if __name__ == "__main__":
    main()