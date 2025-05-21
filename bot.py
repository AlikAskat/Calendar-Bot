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

def get_google_calendar_service():
    """Получение сервиса Google Calendar"""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)

def create_calendar_keyboard(year, month):
    """Создает клавиатуру-календарь"""
    keyboard = []
    
    # Добавляем заголовок с месяцем и годом
    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    keyboard.append([InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="ignore")])
    
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
    
    # Создаем кнопки для часов (с 8 до 20)
    for hour in range(8, 21):
        row = []
        for minute in ['00', '30']:
            time = f"{hour:02d}:{minute}"
            row.append(InlineKeyboardButton(time, callback_data=f"time_{time}"))
        keyboard.append(row)
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("📝 Название задачи")],
        [KeyboardButton("📋 Мои задачи"), KeyboardButton("🔍 Поиск задач")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("🔄 Перезапуск")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def add_event_to_calendar(title, start_time, user_id):
    """Добавляет событие в Google Calendar"""
    service = get_google_calendar_service()
    
    event = {
        'summary': title,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Almaty',
        },
        'end': {
            'dateTime': (start_time + timedelta(hours=1)).isoformat(),
            'timeZone': 'Asia/Almaty',
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    return f"https://calendar.google.com/calendar/event?eid={event['id']}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять задачами в календаре. "
        "Для начала введите название задачи:",
        reply_markup=get_main_keyboard()
    )
    user_states[user.id] = "awaiting_title"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    state = user_states.get(user_id, "awaiting_title")
    
    if text == "🔄 Перезапуск":
        await start(update, context)
        return

    if state == "awaiting_title":
        user_data[user_id] = {"title": text}
        now = datetime.now()
        await update.message.reply_text(
            f"Задача: {text}\n"
            "Теперь выберите дату в календаре:",
            reply_markup=create_calendar_keyboard(now.year, now.month)
        )
        user_states[user_id] = "awaiting_date"
    
    elif text == "📋 Мои задачи":
        # Здесь можно добавить получение списка задач из Google Calendar
        await update.message.reply_text("Функция просмотра задач в разработке")
    
    elif text == "⚙️ Настройки":
        await update.message.reply_text("Настройки временно недоступны")

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
        user_data[user_id]["date"] = {"year": int(year), "month": int(month), "day": int(day)}
        
        await query.message.reply_text(
            f"Дата: {selected_date}\n"
            "Выберите время:",
            reply_markup=create_time_keyboard()
        )
        user_states[user_id] = "awaiting_time"
        
    elif query.data.startswith("time_"):
        time = query.data.split("_")[1]
        user_data[user_id]["time"] = time
        
        # Создаем событие в календаре
        title = user_data[user_id]["title"]
        date = user_data[user_id]["date"]
        hour, minute = map(int, time.split(":"))
        
        start_time = datetime(
            date["year"], date["month"], date["day"],
            hour, minute
        )
        
        try:
            calendar_url = await add_event_to_calendar(title, start_time, user_id)
            await query.message.reply_text(
                f"✅ Задача успешно добавлена!\n\n"
                f"📝 {title}\n"
                f"📅 {start_time.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🔗 Посмотреть в календаре: {calendar_url}"
            )
        except Exception as e:
            logger.error(f"Error adding event to calendar: {e}")
            await query.message.reply_text(
                "❌ Произошла ошибка при добавлении задачи в календарь."
            )
        
        user_states[user_id] = "awaiting_title"
        user_data[user_id] = {}
        
    elif query.data == "cancel":
        await query.message.reply_text(
            "Действие отменено. Введите название новой задачи:",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "awaiting_title"
        user_data[user_id] = {}

def main():
    """Основная функция"""
    logger.info("Запуск бота")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
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