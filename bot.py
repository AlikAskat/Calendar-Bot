async def main() -> None:
    """Основная функция"""
    logger.info("Запуск бота")
    
    # Установка обработчиков сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Запуск сервера проверки здоровья
    health_thread = threading.Thread(target=run_health_check_server)
    health_thread.daemon = True
    health_thread.start()
    
    # Инициализация приложения
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Настройки для webhook
    port = int(os.environ.get("PORT", 10000))
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_url:
        logger.error("RENDER_EXTERNAL_URL не установлен")
        return
    
    webhook_url = f"{app_url}/webhook/{TOKEN}"
    logger.info(f"Setting webhook URL: {webhook_url}")
    
    # Настройка webhook
    if not await setup_webhook(application, webhook_url):
        logger.error("Failed to set up webhook")
        return
    
    # Запускаем webhook с обновленными параметрами
    await application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    asyncio.run(main())