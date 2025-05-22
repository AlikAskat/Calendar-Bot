"""
Calendar Bot
Version: v1
Last update: 2025-05-22 11:18:14
Author: AlikAskat
"""

import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)
from telegram import Update

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nЯ ваш календарный бот."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    await update.message.reply_text(
        f"Вы написали: {update.message.text}"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )

async def main() -> None:
    """Основная функция"""
    logger.info("Запуск бота")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_error_handler(error_handler)

    # Получаем настройки для webhook
    port = int(os.environ.get("PORT", "8443"))
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not webhook_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return

    # Настраиваем webhook
    webhook_path = f"webhook/{TOKEN}"
    webhook_url = f"{webhook_url}/{webhook_path}"
    
    logger.info(f"Настройка webhook: {webhook_url}")
    
    # Запускаем webhook
    await application.bot.set_webhook(webhook_url)
    
    # Запускаем приложение
    await application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())