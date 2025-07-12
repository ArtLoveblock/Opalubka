def main():
    """Запуск бота"""
    TOKEN = os.environ.get('7736990857:AAHEocRVYal13QDxM-HFaQA8b7llWJC_z6g')  # Более строгая проверка
    if not TOKEN:
        logger.error("Токен бота не найден! Проверьте:")
        logger.error("1. Переменную окружения TELEGRAM_TOKEN")
        logger.error("2. Что она добавлена в настройках Render")
        logger.error("3. Что название переменной написано точно")
        sys.exit(1)# Фикс для отсутствующих модулей в Python 3.13
import sys
import types
sys.modules['imghdr'] = types.ModuleType('imghdr')
sys.modules['imghdr'].what = lambda x: None

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    CallbackContext,
    ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
(STONE_WIDTH, STRUCTURE_LENGTH, 
 STRUCTURE_HEIGHT, FINAL_CALCULATION, 
 CONTACT_INFO) = range(5)

# Данные о камнях (в метрах)
stone_data = {
    '20': {'width': 0.20, 'volume': 0.016, 'price': 190, 'work_price': 300},
    '30': {'width': 0.30, 'volume': 0.024, 'price': 205, 'work_price': 300},
    '40': {'width': 0.40, 'volume': 0.032, 'price': 240, 'work_price': 300}
}

def start(update: Update, context: CallbackContext) -> int:
    """Обработка команды /start"""
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("20 см", callback_data='20')],
        [InlineKeyboardButton("30 см", callback_data='30')],
        [InlineKeyboardButton("40 см", callback_data='40')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        '🔨 Калькулятор строительных блоков\n'
        'Размер блока: 60 см (длина) × 20 см (высота)\n'
        'Выберите ширину камня:',
        reply_markup=reply_markup
    )
    return STONE_WIDTH

def stone_width(update: Update, context: CallbackContext) -> int:
    """Обработка выбора ширины камня"""
    query = update.callback_query
    query.answer()
    
    context.user_data['stone_width'] = query.data
    query.edit_message_text(text=f"✅ Ширина камня: {query.data} см")
    query.message.reply_text('📏 Введите ДЛИНУ строения в МЕТРАХ:')
    return STRUCTURE_LENGTH

def structure_length(update: Update, context: CallbackContext) -> int:
    """Обработка ввода длины строения"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0:
            raise ValueError
        context.user_data['structure_length'] = length
        update.message.reply_text('📐 Введите ВЫСОТУ строения в МЕТРАХ:')
        return STRUCTURE_HEIGHT
    except ValueError:
        update.message.reply_text('❌ Ошибка! Введите число больше 0 (например: 5.2):')
        return STRUCTURE_LENGTH

def structure_height(update: Update, context: CallbackContext) -> int:
    """Расчет и вывод результатов"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0:
            raise ValueError
            
        stone = stone_data[context.user_data['stone_width']]
        length_m = context.user_data['structure_length']
        height_m = height
        
        # Параметры блока (60x20 см)
        block_length = 0.60  # 60 см
        block_height = 0.20   # 20 см
        
        # Расчет количества блоков
        blocks_per_row = length_m / block_length
        rows = height_m / block_height
        total_blocks = blocks_per_row * rows
        
        # Расчет стоимости опалубки
        formwork_cost = total_blocks * stone['price']
        work_cost = total_blocks * stone['work_price']
        
        # Расчет арматуры (через каждый ряд)
        rebar_rows = int((rows + 1) // 2)  # Каждый нечетный ряд
        rebar_length = length_m * 2  # Две арматуры на ряд
        total_rebar = rebar_rows * rebar_length
        
        # Формируем результат
        result = (
            f"📊 Результаты расчета:\n"
            f"▪ Размер блока: 60x20 см\n"
            f"▪ Ширина кладки: {stone['width']*100:.0f} см\n"
            f"▪ Длина строения: {length_m:.2f} м\n"
            f"▪ Высота строения: {height_m:.2f} м\n\n"
            f"🧱 Количество блоков: {total_blocks:.1f} шт\n"
            f"🏗️ Объем бетона: {total_blocks * stone['volume']:.3f} м³\n"
            f"💰 Стоимость опалубки: {formwork_cost:.2f} ₽\n"
            f"👷 Стоимость работы: {work_cost:.2f} ₽\n"
            f"🔩 Арматура: {total_rebar:.1f} м\n\n"
            f"Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📞 Консультация", callback_data='consult')],
            [InlineKeyboardButton("🔄 Новый расчет", callback_data='restart')]
        ]
        update.message.reply_text(
            result,
            reply_markup=InlineKeyboardMarkup(keyboard))
        return FINAL_CALCULATION
        
    except ValueError:
        update.message.reply_text('❌ Ошибка! Введите число больше 0 (например: 2.5):')
        return STRUCTURE_HEIGHT

def final_calculation(update: Update, context: CallbackContext) -> int:
    """Обработка выбора после расчета"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'consult':
        query.edit_message_text(text="✍️ Введите ваше имя и телефон:\n(Например: Иван +79123456789)")
        return CONTACT_INFO
    elif query.data == 'restart':
        context.user_data.clear()
        context.bot.send_message(
            chat_id=query.message.chat.id,
            text="🔄 Начинаем новый расчет! Нажмите /start"
        )
        return ConversationHandler.END

def contact_info(update: Update, context: CallbackContext) -> int:
    """Сохранение контактных данных"""
    logger.info(f"Новая заявка: {update.message.text}\n{context.user_data}")
    update.message.reply_text(
        "✅ Спасибо! Мы вам перезвоним.\n"
        "Для нового расчета нажмите /start"
    )
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Отмена диалога"""
    update.message.reply_text('❌ Расчет отменен. Для начала нажмите /start')
    return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext):
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        update.message.reply_text('⚠️ Произошла ошибка. Пожалуйста, нажмите /start')

def main():
    """Запуск бота"""
    TOKEN = os.getenv('7736990857:AAHEocRVYal13QDxM-HFaQA8b7llWJC_z6g')
    if not TOKEN:
        logger.error("Токен бота не найден! Проверьте переменную окружения TELEGRAM_TOKEN")
        sys.exit(1)
    
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STONE_WIDTH: [CallbackQueryHandler(stone_width)],
            STRUCTURE_LENGTH: [MessageHandler(Filters.text & ~Filters.command, structure_length)],
            STRUCTURE_HEIGHT: [MessageHandler(Filters.text & ~Filters.command, structure_height)],
            FINAL_CALCULATION: [CallbackQueryHandler(final_calculation)],
            CONTACT_INFO: [MessageHandler(Filters.text & ~Filters.command, contact_info)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(error_handler)

    # Режим работы
    if os.getenv('RENDER'):
        # Webhook для Render
        PORT = int(os.environ.get('PORT', 8443))
        app_name = os.getenv('RENDER_APP_NAME', 'your-app-name')
        webhook_url = f"https://{app_name}.onrender.com/{TOKEN}"
        
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=webhook_url
        )
        logger.info(f"Бот запущен в webhook режиме: {webhook_url}")
    else:
        # Локальный polling
        updater.start_polling()
        logger.info("Бот запущен в polling режиме")

    updater.idle()

if __name__ == '__main__':
    main()
