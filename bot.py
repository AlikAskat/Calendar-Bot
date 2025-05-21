# ... (предыдущий импорт и настройки остаются без изменений)

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("🔄 Перезапуск"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по командам"""
    help_text = (
        "📝 *Справка по командам:*\n\n"
        "➕ *Добавить задачу* - создание новой задачи:\n"
        "   1. Введите название задачи\n"
        "   2. Выберите дату в календаре\n"
        "   3. Выберите время\n"
        "   4. Получите ссылку на событие в Google Calendar\n\n"
        "🔄 *Перезапуск* - очистка чата и перезапуск бота\n\n"
        "❓ *Помощь* - показать это сообщение\n\n"
        "Чтобы начать, нажмите '➕ Добавить задачу'"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу вам управлять задачами в календаре.\n"
        "Нажмите '➕ Добавить задачу' чтобы начать, или '❓ Помощь' для получения справки.",
        reply_markup=get_main_keyboard()
    )
    user_states[user.id] = "main_menu"

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает чат и перезапускает бота"""
    # Очищаем данные пользователя
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text(
        "🔄 Бот перезапущен!\n"
        "Все данные очищены. Можно начать заново:",
        reply_markup=get_main_keyboard()
    )
    user_states[user_id] = "main_menu"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    state = user_states.get(user_id, "main_menu")
    
    if text == "🔄 Перезапуск":
        await restart(update, context)
        return
        
    elif text == "❓ Помощь":
        await show_help(update, context)
        return
        
    elif text == "➕ Добавить задачу":
        await update.message.reply_text(
            "Введите название задачи:"
        )
        user_states[user_id] = "awaiting_title"
        return

    if state == "awaiting_title":
        user_data[user_id] = {"title": text}
        now = datetime.now()
        await update.message.reply_text(
            f"Задача: {text}\n"
            "Теперь выберите дату в календаре:",
            reply_markup=create_calendar_keyboard(now.year, now.month)
        )
        user_states[user_id] = "awaiting_date"
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации или нажмите '❓ Помощь' для получения справки:",
            reply_markup=get_main_keyboard()
        )

def main():
    """Основная функция"""
    logger.info("Запуск бота")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
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