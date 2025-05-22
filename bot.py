"""
Calendar Bot
Version: v24
Last update: 2025-05-22
Author: AlikAskat
"""

# ... (весь предыдущий код остается тем же самым до функции main)

def main() -> None:
    """Основная функция"""
    logger.info("Запуск бота")
    
    # Инициализация приложения
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Настройки для webhook
    port = int(os.environ.get("PORT", "8443"))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return
    
    webhook_path = f"webhook/{TOKEN}"
    webhook_url = f"{app_url}/{webhook_path}"
    logger.info(f"Setting webhook URL: {webhook_url}")

    try:
        # Простой запуск webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=webhook_path,
            webhook_url=webhook_url
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске webhook: {e}")
        # Попробуем альтернативный способ запуска
        try:
            application.start_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=webhook_path,
                webhook_url=webhook_url
            )
            application.idle()
        except Exception as e2:
            logger.error(f"Ошибка при альтернативном запуске webhook: {e2}")
            return

if __name__ == "__main__":
    main()