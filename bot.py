"""
Calendar Bot
Version: 1.0.10
Last Updated: 2025-05-28 19:20
Author: AlikAskat
"""

import os
import logging
import signal
import sys
import asyncio
import threading  # Импорт модуля threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Версия бота
__version__ = '1.0.10'
logger = logging.getLogger(__name__)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - [v" + __version__ + "] - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            response = f"OK - Calendar Bot v{__version__}"
            self.wfile.write(response.encode('utf-8'))

def run_health_check_server():
    port = int(os.environ.get("HEALTH_CHECK_PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def signal_handler(signum, frame):
    logger.info(f'Получен сигнал: {signum}')
    sys.exit(0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Привет! Я Calendar Bot v{__version__}")

async def setup_webhook(app: Application, webhook_url: str) -> bool:
    try:
        await app.bot.delete_webhook()  # Удаление старого вебхука
        await app.bot.set_webhook(webhook_url)
        logger.info(f"Webhook успешно установлен на {webhook_url}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке webhook: {e}")
        return False

async def run_application():
    """
    Запуск приложения с использованием asyncio.run()
    """
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))

    # Настройки вебхука
    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return
    webhook_url = f"{app_url}/webhook/{TOKEN}"

    if not await setup_webhook(application, webhook_url):
        return

    # Запуск webhook
    try:
        await application.initialize()
        await application.start()
        await application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=f"webhook/{TOKEN}",
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        # Гарантированное завершение приложения
        await application.stop()
        logger.info("Приложение остановлено корректно.")

def main():
    """
    Основная точка входа
    """
    logger.info(f"Запуск Calendar Bot v{__version__}")
    
    # Установка обработчиков сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Запуск сервера проверки здоровья
    health_thread = threading.Thread(target=run_health_check_server)
    health_thread.daemon = True
    health_thread.start()
    
    # Запуск приложения
    try:
        asyncio.run(run_application())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()