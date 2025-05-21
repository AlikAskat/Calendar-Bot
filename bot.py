import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена в .env файле!")

# Пример обработчика команды /start
async def start(update, context):
    await update.message.reply_text("Привет! Я ваш календарный бот.")

# Пример обработчика текстовых сообщений
async def echo(update, context):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

async def main():
    application = Application.builder().token(TOKEN).build()

    # Удаляем вебхук (если был установлен)
    try:
        await application.bot.delete_webhook()
        logger.info("Вебхук успешно удалён")
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запуск бота (режим Polling)
    await application.initialize()
    await application.start()
    logger.info("Бот запущен. Ожидаю сообщения...")
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())