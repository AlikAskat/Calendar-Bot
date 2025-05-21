import logging
from telegram.ext import Application

logger = logging.getLogger(__name__)

async def main():
    # Создайте приложение Telegram
    application = Application.builder().token("ВАШ_ТОКЕН").build()

    # Удаление вебхука (корректно через await)
    try:
        await application.bot.delete_webhook()
        logger.info("Вебхук успешно удален")
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

    # Ваши дальнейшие настройки и запуск бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # или start_webhook() если нужен webhook
    await application.updater.idle()

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())