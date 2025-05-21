import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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

# Глобальный словарь для хранения состояний пользователей
user_states = {}

# Клавиатура главного меню
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📅 Добавить задачу")],
        [KeyboardButton("📋 Мои задачи"), KeyboardButton("🔍 Поиск задач")],
        [KeyboardButton("⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Инлайн клавиатура для выбора даты
def get_date_keyboard():
    now = datetime.now()
    keyboard = [
        [
            InlineKeyboardButton("Сегодня", callback_data=f"date_today"),
            InlineKeyboardButton("Завтра", callback_data=f"date_tomorrow")
        ],
        [
            InlineKeyboardButton("Выбрать дату", callback_data="choose_date"),
            InlineKeyboardButton("Отмена", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять вашими задачами и встречами. "
        "Используйте кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )
    user_states[user.id] = "main_menu"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📅 Добавить задачу":
        await update.message.reply_text(
            "Выберите дату для задачи:",
            reply_markup=get_date_keyboard()
        )
        user_states[user_id] = "awaiting_date"
        
    elif text == "📋 Мои задачи":
        await update.message.reply_text(
            "У вас пока нет задач. Нажмите '📅 Добавить задачу' чтобы создать новую."
        )
        
    elif text == "🔍 Поиск задач":
        await update.message.reply_text(
            "Введите ключевое слово для поиска задач:"
        )
        user_states[user_id] = "awaiting_search"
        
    elif text == "⚙️ Настройки":
        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications")],
            [InlineKeyboardButton("🌍 Часовой пояс", callback_data="settings_timezone")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
        ]
        await update.message.reply_text(
            "⚙️ Настройки:\n\nВыберите, что хотите настроить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Обработка текста в зависимости от состояния пользователя
        state = user_states.get(user_id, "main_menu")
        
        if state == "awaiting_task_description":
            await update.message.reply_text(
                f"Задача '{text}' добавлена в календарь!\n\n"
                "Что делаем дальше?",
                reply_markup=get_main_keyboard()
            )
            user_states[user_id] = "main_menu"
            
        elif state == "awaiting_search":
            await update.message.reply_text(
                f"🔍 Результаты поиска по запросу '{text}':\n\n"
                "Задачи не найдены.",
                reply_markup=get_main_keyboard()
            )
            user_states[user_id] = "main_menu"
        else:
            await update.message.reply_text(
                "Используйте кнопки меню для навигации:",
                reply_markup=get_main_keyboard()
            )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback запросов от инлайн кнопок"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()  # Отвечаем на callback query

    if query.data.startswith("date_"):
        date_type = query.data.split("_")[1]
        if date_type == "today":
            date_text = "сегодня"
        elif date_type == "tomorrow":
            date_text = "завтра"
        
        await query.message.reply_text(
            f"Вы выбрали дату: {date_text}\n"
            "Теперь введите описание задачи:"
        )
        user_states[user_id] = "awaiting_task_description"
        
    elif query.data == "choose_date":
        await query.message.reply_text(
            "Введите дату в формате ДД.ММ.ГГГГ:"
        )
        user_states[user_id] = "awaiting_custom_date"
        
    elif query.data == "cancel":
        await query.message.reply_text(
            "Действие отменено. Что делаем дальше?",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "main_menu"
        
    elif query.data.startswith("settings_"):
        setting = query.data.split("_")[1]
        if setting == "notifications":
            await query.message.edit_text(
                "🔔 Настройки уведомлений\n\n"
                "В разработке..."
            )
        elif setting == "timezone":
            await query.message.edit_text(
                "🌍 Настройка часового пояса\n\n"
                "В разработке..."
            )
            
    elif query.data == "back_to_main":
        await query.message.reply_text(
            "Вернулись в главное меню:",
            reply_markup=get_main_keyboard()
        )
        user_states[user_id] = "main_menu"

def main():
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