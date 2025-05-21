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
user_states = {}
user_data = {}

# Клавиатуры
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("🔄 Перезапуск"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_calendar_keyboard(year: int, month: int):
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
    keyboard = []
    for hour in range(8, 21):
        row = []
        for minute in ['00', '30']:
            time = f"{hour:02d}:{minute}"
            row.append(InlineKeyboardButton(time, callback_data=f"time_{time}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять задачами в календаре.\n"
        "Нажмите '➕ Добавить задачу' чтобы начать, или '❓ Помощь' для получения справки.",
        reply_markup=get_main_keyboard()
    )
    user_states[user.id] = "main_menu"

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

# Обработчики сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        user_data[user_id] = {"date": {"year": int(year), "month": int(month), "day": int(day)}}
        
        await query.message.reply_text(
            f"Дата: {selected_date}\n"
            "Выберите время:",
            reply_markup=create_time_keyboard()
        )
        user_states[user_id] = "awaiting_time"
        
    elif query.data.startswith("time_"):
        time = query.data.split("_")[1]
        if not user_data.get(user_id):
            user_data[user_id] = {}
        user_data[user_id]["time"] = time
        
        await query.message.reply_text(
            f"Выбрано время: {time}\n"
            "Задача создана!",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "main_menu"
        
    elif query.data == "cancel":
        await query.message.reply_text(
            "Действие отменено. Используйте кнопки меню:",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "main_menu"

def main() -> None:
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