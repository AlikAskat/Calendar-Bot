import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

async def start(update, context):
    await update.message.reply_text("Привет! Я ваш календарный бот.")

async def echo(update, context):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

async def main():
    application = Application.builder().token(TOKEN).build()

    # Удаляем старый вебхук
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук успешно удалён")
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    port = int(os.environ.get("PORT", 10000))
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        logger.error("RENDER_EXTERNAL_URL не установлен. Проверьте настройки Render.")
        return

    webhook_url = f"{url}/webhook/{TOKEN}"
    logger.info(f"Устанавливаю вебхук: {webhook_url}")

    await application.bot.set_webhook(webhook_url)
    await application.initialize()  # <-- добавлена строка
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url,
    )
    logger.info("Бот запущен на Render через Webhook.")
    await application.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())