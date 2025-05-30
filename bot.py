"""
Calendar Bot
Version: 1.0.18q
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
__version__ = '1.0.18q'
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

def get_google_calendar_service():
    """Получение сервиса Google Calendar с использованием Service Account"""
    try:
        if not GOOGLE_CREDENTIALS_JSON:
            logger.error("Переменная GOOGLE_CREDENTIALS не установлена")
            return None

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(GOOGLE_CREDENTIALS_JSON),
            scopes=SCOPES
        )
        # Делегируйте доступ к календарю пользователя
        credentials = credentials.with_subject("ваш-почтовый-адрес@example.com")  # Email владельца календаря
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Ошибка при получении сервиса календаря: {e}")
        return None

def create_calendar_keyboard(year: int, month: int):
    """Создает клавиатуру-календарь"""
    keyboard = []
    month_names = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 
                  'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
    keyboard.append([InlineKeyboardButton(f"{month_names[month-1].capitalize()} {year}", callback_data="ignore")])
    keyboard.append([InlineKeyboardButton(d, callback_data="ignore") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])
    for week in calendar.Calendar().monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"day:{year}-{month}-{day}"))
        keyboard.append(row)
    nav_row = []
    prev_month = month - 1 if month > 1 else 12
    next_month = month + 1 if month < 12 else 1
    prev_year = year if month > 1 else year - 1
    next_year = year if month < 12 else year + 1
    nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"prev:{prev_year}:{prev_month}"))
    nav_row.append(InlineKeyboardButton("Отмена", callback_data="cancel"))
    nav_row.append(InlineKeyboardButton("➡️", callback_data=f"next:{next_year}:{next_month}"))
    keyboard.append(nav_row)
    return InlineKeyboardMarkup(keyboard)

def create_time_keyboard():
    """Создает клавиатуру для выбора времени"""
    hours = [f"{h:02d}" for h in range(24)]
    minutes = [f"{m:02d}" for m in range(0, 60, 5)]

    hour_markup = []
    for i in range(0, 24, 8):  # 3x8 сетка
        hour_markup.append(
            [InlineKeyboardButton(h, callback_data=f"time_{h}") for h in hours[i:i+8]]
        )

    minute_markup = []
    for i in range(0, 60, 20):  # 3x4 сетка
        minute_markup.append(
            [InlineKeyboardButton(m, callback_data=f"time_{m}") for m in minutes[i:i+20]]
        )

    return InlineKeyboardMarkup(hour_markup + minute_markup)

def get_main_keyboard():
    """Создает основную клавиатуру"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("Добавить задачу")],
        [KeyboardButton("Помощь"), KeyboardButton("Перезапуск")]
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
    except googleapiclient.errors.HttpError as e:
        logger.error(f"Ошибка Google Calendar API: {e}")
        return ""
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
        "Нажмите 'Добавить задачу' чтобы начать, или 'Помощь' для получения справки.",
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
        "Чтобы начать, нажмите 'Добавить задачу'"
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

    if text == "Добавить задачу":
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
    elif state == "awaiting_time":
        try:
            hour, minute = map(int, text.split(":"))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                selected_date = user_data[user_id]["date"]
                start_time = selected_date.replace(hour=hour, minute=minute)
                calendar_url = add_event_to_calendar(user_data[user_id]["title"], start_time)

                if calendar_url:
                    await update.message.reply_text(
                        f"✅ Задача успешно добавлена!\n"
                        f"📝 {user_data[user_id]['title']}\n"
                        f"📅 {start_time.strftime('%d.%m.%Y %H:%M')}\n"
                        f"🔗 Посмотреть в календаре: {calendar_url}",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        "❌ Произошла ошибка при добавлении задачи в календарь.\n"
                        "Попробуйте еще раз:",
                        reply_markup=get_main_keyboard()
                    )
                user_states[user_id] = "main_menu"
                user_data[user_id] = {}
            else:
                await update.message.reply_text("🕒 Неверный формат времени. Введите в формате ЧЧ:ММ.")
        except ValueError:
            await update.message.reply_text("🕒 Неверный формат времени. Введите в формате ЧЧ:ММ.")
    elif text == "Помощь":
        await show_help(update, context)
    elif text == "Перезапуск":
        await restart(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации или нажмите 'Помощь' для получения справки:",
            reply_markup=get_main_keyboard()
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback запросов"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("day:"):
        data_parts = query.data.split(":")
        if len(data_parts) < 4:
            logger.error(f"Некорректный callback_data: {query.data}")
            return
        _, year, month, day = data_parts
        selected_date = datetime(int(year), int(month), int(day))
        user_data[user_id]["date"] = selected_date
        user_states[user_id] = "awaiting_time"
        await query.message.reply_text("🕒 Введите время в формате ЧЧ:ММ:")
    elif query.data.startswith("prev:") or query.data.startswith("next:"):
        data_parts = query.data.split(":")
        if len(data_parts) < 3:
            logger.error(f"Некорректный callback_data: {query.data}")
            return
        _, year, month = data_parts
        user_states[user_id] = "awaiting_date"
        user_data[user_id]["year"] = int(year)
        user_data[user_id]["month"] = int(month)
        await show_calendar(user_id, int(year), int(month), context)
    elif query.data == "cancel":
        await query.message.reply_text("Действие отменено. Используйте кнопки меню:", reply_markup=get_main_keyboard())
        user_states[user_id] = "main_menu"
        user_data[user_id] = {}

async def show_calendar(user_id: int, year: int, month: int, context):
    """Отображает календарь"""
    markup = create_calendar_keyboard(year, month)
    month_name = {1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь", 
                  7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"}[month]
    message_text = f"📅 Календарь:\nВыберите дату:\n\n{month_name} {year}"

    if 'calendar_message_id' in user_data.get(user_id, {}):
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=user_data[user_id]['calendar_message_id'],
            text=message_text,
            reply_markup=markup
        )
    else:
        message = await context.bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=markup
        )
        user_data[user_id]['calendar_message_id'] = message.message_id
        user_states[user_id] = "awaiting_date"

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже или нажмите 'Перезапуск'.",
            reply_markup=get_main_keyboard()
        )

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

    # Настройки для вебхука
    domain = os.getenv("RENDER_EXTERNAL_URL")
    if not domain:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return

    port = int(os.getenv("PORT", 10000))
    webhook_url = f"{domain}/webhook/{TOKEN}"

    logger.info(f"Настройка вебхука: {webhook_url}")
    
    # Запускаем вебхук
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="/webhook",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()