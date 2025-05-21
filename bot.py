import os
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
    filters,
    ContextTypes
)
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
TIMEZONE = 'Asia/Almaty'
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

def create_time_keyboard(selected_hour: int = 0, selected_minute: int = 0):
    """Создает клавиатуру для выбора времени с стрелками"""
    keyboard = []
    
    # Добавляем заголовок
    keyboard.append([
        InlineKeyboardButton("Часы", callback_data="ignore"),
        InlineKeyboardButton("Минуты", callback_data="ignore")
    ])
    
    # Стрелка вверх для часов и минут
    keyboard.append([
        InlineKeyboardButton("🔼", callback_data=f"hour_up_{selected_hour}"),
        InlineKeyboardButton("🔼", callback_data=f"min_up_{selected_minute}")
    ])
    
    # Текущие значения часов и минут
    keyboard.append([
        InlineKeyboardButton(f"{selected_hour:02d}", callback_data="ignore"),
        InlineKeyboardButton(f"{selected_minute:02d}", callback_data="ignore")
    ])
    
    # Стрелка вниз для часов и минут
    keyboard.append([
        InlineKeyboardButton("🔽", callback_data=f"hour_down_{selected_hour}"),
        InlineKeyboardButton("🔽", callback_data=f"min_down_{selected_minute}")
    ])
    
    # Кнопки подтверждения и отмены
    keyboard.append([
        InlineKeyboardButton("✅ Готово", callback_data=f"time_{selected_hour:02d}:{selected_minute:02d}"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("🔄 Перезапуск"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def add_event_to_calendar(title: str, start_time: datetime) -> str:
    """Добавляет событие в Google Calendar и возвращает ссылку на него"""
    try:
        service = get_google_calendar_service()
        
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
        logger.error(f"Error adding event to calendar: {e}")
        return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять задачами в календаре.\n"
        "Нажмите '➕ Добавить задачу' чтобы начать, или '❓ Помощь' для получения справки.",
        reply_markup=get_main_keyboard()
    )
    user_states[user.id] = "main_menu"

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очищает чат и перезапускает бота"""
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text(
        "🔄 Бот перезапущен!\n"
        "Все данные очищены. Можно начать заново:",
        reply_markup=get_main_keyboard()
    )
    user_states[user_id] = "main_menu"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    state = user_states.get(user_id, "main_menu")
    
    if text == "🔄 Перезапуск":
        await restart(update, context)
        return
        
    elif text == "❓ Помощь":
        await show_help(update, context)
        return
        
    elif text == "➕ Добавить задачу":
        await update.message.reply_text(
            "Введите название задачи:"
        )
        user_states[user_id] = "awaiting_title"
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
        await query.message.edit_reply_markup(
            reply_markup=create_calendar_keyboard(int(year), int(month))
        )
        
    elif query.data.startswith("date_"):
        _, year, month, day = query.data.split("_")
        selected_date = f"{day}.{month}.{year}"
        if "title" not in user_data.get(user_id, {}):
            user_data[user_id] = {"title": "Новая задача"}
        user_data[user_id]["date"] = {"year": int(year), "month": int(month), "day": int(day)}
        
        # Начинаем с 00:00
        await query.message.reply_text(
            f"Дата: {selected_date}\n"
            "Выберите время (используйте стрелки для выбора часов и минут):",
            reply_markup=create_time_keyboard(0, 0)
        )
        user_states[user_id] = "awaiting_time"
    
    elif query.data.startswith("hour_up_") or query.data.startswith("hour_down_"):
        _, direction, current = query.data.split("_")
        current_hour = int(current)
        
        if direction == "up":
            new_hour = current_hour + 1 if current_hour < 23 else 0
        else:
            new_hour = current_hour - 1 if current_hour > 0 else 23
            
        # Сохраняем текущие минуты из клавиатуры
        current_minutes = int(query.message.reply_markup.inline_keyboard[2][1].text)
        
        await query.message.edit_reply_markup(
            reply_markup=create_time_keyboard(new_hour, current_minutes)
        )
    
    elif query.data.startswith("min_up_") or query.data.startswith("min_down_"):
        _, direction, current = query.data.split("_")
        current_minute = int(current)
        
        minutes_steps = [0, 15, 30, 45]  # Шаги для минут
        current_index = minutes_steps.index(current_minute)
        
        if direction == "up":
            new_index = (current_index + 1) % len(minutes_steps)
        else:
            new_index = (current_index - 1) % len(minutes_steps)
            
        new_minute = minutes_steps[new_index]
            
        # Сохраняем текущие часы из клавиатуры
        current_hours = int(query.message.reply_markup.inline_keyboard[2][0].text)
        
        await query.message.edit_reply_markup(
            reply_markup=create_time_keyboard(current_hours, new_minute)
        )
    
    elif query.data.startswith("time_"):
        time = query.data.split("_")[1]
        if not user_data.get(user_id):
            await query.message.reply_text(
                "Произошла ошибка. Начните сначала:",
                reply_markup=get_main_keyboard()
            )
            return
            
        user_data[user_id]["time"] = time
        title = user_data[user_id].get("title", "Новая задача")
        date = user_data[user_id]["date"]
        hour, minute = map(int, time.split(":"))
        
        start_time = datetime(
            date["year"], date["month"], date["day"],
            hour, minute
        )
        
        # Добавляем событие в календарь
        calendar_url = await add_event_to_calendar(title, start_time)
        
        if calendar_url:
            await query.message.reply_text(
                f"✅ Задача успешно добавлена!\n\n"
                f"📝 {title}\n"
                f"📅 {start_time.strftime('%d.%m.%Y %H:%M')}\n\n"
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

def main() -> None:
    """Основная функция"""
    logger.info("Запуск бота")
    
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
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