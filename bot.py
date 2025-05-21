import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

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

# Обработчики команд
async def start(update, context):
    await update.message.reply_text("Привет! Я ваш календарный бот.")

async def echo(update, context):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

async def run_webhook():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Удаляем старый вебхук
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Старый вебхук удален")

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Настройки для webhook
    port = int(os.environ.get("PORT", 10000))
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook/{TOKEN}"
    
    # Запускаем webhook
    await application.initialize()
    await application.start()
    await application.update.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url
    )
    
    logger.info(f"Бот запущен в режиме webhook на порту {port}")
    
    # Держим приложение запущенным
    await application.idle()

def main():
    logger.info("Запуск бота")
    
    # Создаем и запускаем event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_webhook())
    except KeyboardInterrupt:
        logger.info("Остановка бота")
    finally:
        loop.close()

if __name__ == "__main__":
    main()