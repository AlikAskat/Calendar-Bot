import os
import logging
from datetime import datetime, timedelta
import calendar
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

# Глобальные переменные
SCOPES = ['https://www.googleapis.com/auth/calendar']
user_states = {}
user_data = {}

def create_calendar_keyboard(year, month):
    """Создает клавиатуру-календарь"""
    keyboard = []
    
    # Добавляем заголовок с месяцем и годом
    month_name = calendar.month_name[month]
    keyboard.append([InlineKeyboardButton(f"{month_name} {year}", callback_data="ignore")])
    
    # Добавляем дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(day, callback_data="ignore") for day in week_days])
    
    # Получаем календарь на месяц
    cal = calendar.monthcalendar(year, month)
    
    # Добавляем дни
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(row)
    
    # Добавляем кнопки навигации
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
    hours = [f"{i:02d}:00" for i in range(8, 21)]  # с 8:00 до 20:00
    
    # Группируем по 3 кнопки в ряд
    for i in range(0, len(hours), 3):
        row = [InlineKeyboardButton(time, callback_data=f"time_{time}") 
               for time in hours[i:i+3]]
        keyboard.append(row)
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("📅 Добавить задачу")],
        [KeyboardButton("📋 Мои задачи"), KeyboardButton("🔍 Поиск задач")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("🔄 Перезапуск")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять вашими задачами и встречами в календаре. "
        "Используйте кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )
    user_states[user.id] = "main_menu"

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды перезапуска"""
    await start(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🔄 Перезапуск":
        await restart(update, context)
        return

    if text == "📅 Добавить задачу":
        now = datetime.now()
        await update.message.reply_text(
            "Выберите дату:",
            reply_markup=create_calendar_keyboard(now.year, now.month)
        )
        user_states[user_id] = "awaiting_date"
        
    # ... (остальные обработчики текста остаются без изменений)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback запросов"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()

    if query.data.startswith("calendar_"):
        # Обработка навигации по календарю
        _, year, month = query.data.split("_")
        await query.message.edit_reply_markup(
            reply_markup=create_calendar_keyboard(int(year), int(month))
        )
        
    elif query.data.startswith("date_"):
        # Обработка выбора даты
        _, year, month, day = query.data.split("_")
        selected_date = f"{day}.{month}.{year}"
        user_data[user_id] = {"date": selected_date}
        
        await query.message.reply_text(
            f"Выбрана дата: {selected_date}\n"
            "Теперь выберите время:",
            reply_markup=create_time_keyboard()
        )
        user_states[user_id] = "awaiting_time"
        
    elif query.data.startswith("time_"):
        # Обработка выбора времени
        time = query.data.split("_")[1]
        user_data[user_id]["time"] = time
        
        await query.message.reply_text(
            f"Выбрано время: {time}\n"
            "Теперь введите описание задачи:"
        )
        user_states[user_id] = "awaiting_task_description"
        
    # ... (остальные обработчики callback остаются без изменений)

def main():
    """Основная функция"""
    logger.info("Запуск бота")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Настройки для webhook
    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return
    
    webhook_url = f"{app_url}/webhook/{TOKEN}"
    logger.info(f"Setting webhook URL: {webhook_url}")
    
    # Запускаем webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()