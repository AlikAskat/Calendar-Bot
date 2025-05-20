import os
import pickle
import locale
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
import calendar
import logging
import asyncio

load_dotenv()

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    pass

# Русские названия месяцев
RU_MONTHS = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
]

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Правильный список прав (SCOPES)
SCOPES = ['https://www.googleapis.com/auth/calendar ']

user_data = {}

def get_calendar_service():
    logger.info("Запрос сервиса Google Calendar")
    token_path = "token.pickle"
    
    if not os.path.exists(token_path):
        raise FileNotFoundError("Токен не найден. Выполните авторизацию.")

    with open(token_path, 'rb') as token_file:
        creds = pickle.load(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Обновление токена")
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Ошибка при обновлении токена: {e}")
                raise
        else:
            logger.warning("Нет действительного токена.")
            raise FileNotFoundError("Нет действительного токена.")

    return build('calendar', 'v3', credentials=creds)

def add_event_to_calendar(summary, start_time, end_time):
    logger.info("Добавление события в календарь")
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Yekaterinburg'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Yekaterinburg'}
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return created_event.get('htmlLink')
    except Exception as e:
        logger.error(f"Ошибка при добавлении события: {e}")
        raise

async def start(update: Update, context) -> None:
    keyboard = [["Добавить задачу", "Помощь", "Перезапустить"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        'Привет! Выберите действие:',
        reply_markup=reply_markup
    )

async def restart(update: Update, context) -> None:
    chat_id = update.effective_chat.id
    user_data[chat_id] = {}
    await start(update, context)

async def help_command(update: Update, context) -> None:
    await update.message.reply_text("Чтобы добавить задачу, выберите \"Добавить задачу\" и следуйте инструкциям.")

def build_calendar(year, month):
    markup = []
    cal = calendar.Calendar()
    
    # Дни недели
    markup.append([InlineKeyboardButton(day, callback_data="ignore") for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])

    # Дни месяца
    for week in cal.monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"day:{year}-{month}-{day}"))
        markup.append(row)

    # Навигация
    month_name = RU_MONTHS[month - 1].capitalize()
    markup.append([
        InlineKeyboardButton("⬅️", callback_data=f"prev:{year}:{month}"),
        InlineKeyboardButton(f"{month_name} {year}", callback_data="ignore"),
        InlineKeyboardButton("➡️", callback_data=f"next:{year}:{month}")
    ])
    return InlineKeyboardMarkup(markup)

def build_hour_keyboard():
    markup = []
    for i in range(0, 24, 8):  # 3x8 сетка
        row = [InlineKeyboardButton(f"{h:02d}", callback_data=f"hour:{h}") for h in range(i, min(i+8, 24))]
        markup.append(row)
    return InlineKeyboardMarkup(markup)

def build_minute_keyboard():
    markup = []
    for i in range(0, 60, 20):  # 3x4 сетка
        row = [InlineKeyboardButton(f"{m:02d}", callback_data=f"minute:{m}") for m in range(i, i+20, 5)]
        markup.append(row)
    return InlineKeyboardMarkup(markup)

async def show_calendar(chat_id: int, year: int, month: int, context):
    markup = build_calendar(year, month)
    month_name = RU_MONTHS[month - 1].capitalize()
    message_text = f"📅 Календарь:\nВыберите дату:\n\n{month_name} {year}"

    if 'calendar_message_id' in user_data.get(chat_id, {}):
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=user_data[chat_id]['calendar_message_id'],
            text=message_text,
            reply_markup=markup
        )
    else:
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=markup
        )
        user_data[chat_id]['calendar_message_id'] = message.message_id

async def show_hour_keyboard(chat_id: int, context):
    markup = build_hour_keyboard()
    await context.bot.send_message(chat_id=chat_id, text="🕒 Выберите час:", reply_markup=markup)

async def show_minute_keyboard(chat_id: int, context):
    markup = build_minute_keyboard()
    await context.bot.send_message(chat_id=chat_id, text="🕒 Выберите минуты:", reply_markup=markup)

async def handle_message(update: Update, context) -> None:
    text = update.message.text.strip().lower()
    chat_id = update.effective_chat.id

    if text == "добавить задачу":
        user_data[chat_id] = {'state': 'awaiting_task'}
        await update.message.reply_text("Введите название задачи:")
    elif user_data.get(chat_id, {}).get('state') == 'awaiting_task':
        user_data[chat_id]['task'] = text
        user_data[chat_id]['state'] = 'selecting_date'
        today = datetime.today()
        user_data[chat_id]['year'] = today.year
        user_data[chat_id]['month'] = today.month
        await show_calendar(chat_id, today.year, today.month, context)
    elif text == "помощь":
        await help_command(update, context)
    elif text == "перезапустить":
        await restart(update, context)
    else:
        await update.message.reply_text("❌ Неизвестная команда. Используйте кнопки меню.")

async def handle_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("day:"):
        _, date_str = data.split(":")
        y, m, d = map(int, date_str.split("-"))
        selected_date = datetime(y, m, d)
        user_data[chat_id]['date'] = selected_date
        user_data[chat_id]['state'] = 'selecting_hour'
        await show_hour_keyboard(chat_id, context)
    elif data.startswith("hour:"):
        hour = int(data.split(":")[1])
        user_data[chat_id]['hour'] = hour
        user_data[chat_id]['state'] = 'selecting_minute'
        await show_minute_keyboard(chat_id, context)
    elif data.startswith("minute:"):
        minute = int(data.split(":")[1])
        user_data[chat_id]['minute'] = minute
        selected_date = user_data[chat_id]['date']
        task = user_data[chat_id]['task']
        start_datetime = selected_date.replace(hour=user_data[chat_id]['hour'], minute=minute)
        end_datetime = start_datetime + timedelta(minutes=30)
        event_link = add_event_to_calendar(task, start_datetime, end_datetime)
        await query.message.reply_text(f"✅ Задача добавлена! Ссылка: {event_link}")
        user_data.pop(chat_id)
    elif data.startswith("prev:") or data.startswith("next:"):
        _, y, m = data.split(":")
        year, month = int(y), int(m)
        if data.startswith("prev:"):
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        else:
            month += 1
            if month > 12:
                month = 1
                year += 1
        user_data[chat_id]['year'] = year
        user_data[chat_id]['month'] = month
        await show_calendar(chat_id, year, month, context)

# Асинхронная функция для удаления вебхука
async def delete_webhook(application):
    await application.bot.delete_webhook()

async def main():
    logger.info("Запуск бота")
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("Переменная TELEGRAM_TOKEN не найдена в .env")
        return

    application = Application.builder().token(token).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Удаляем старый вебхук (если существует)
    try:
        await delete_webhook(application)
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

    # Получаем домен Render
    domain = os.getenv("RENDER_EXTERNAL_URL")
    if not domain:
        domain = "http://localhost:8000"

    # Запускаем вебхук
    await application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        url_path=token,
        webhook_url=f"{domain}/{token}"
    )

if __name__ == '__main__':
    asyncio.run(main())