# -*- coding: utf-8 -*-
import os
import logging
import sys
import types
from threading import Thread
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# Фикс для Python 3.13+
sys.modules['imghdr'] = types.ModuleType('imghdr')
sys.modules['imghdr'].what = lambda x: None

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
ADMIN_CHAT_ID = "5559554783"  # Замените на ваш chat_id (получить через @userinfobot)
PING_INTERVAL = 300  # 5 минут

# Состояния диалога
(STONE_WIDTH, STRUCTURE_LENGTH, 
 STRUCTURE_HEIGHT, FINAL_CALCULATION, 
 CONTACT_INFO) = range(5)

# Данные о камнях
stone_data = {
    '20': {'width': 0.20, 'volume': 0.016, 'price': 190, 'work_price': 300},
    '30': {'width': 0.30, 'volume': 0.024, 'price': 205, 'work_price': 300},
    '40': {'width': 0.40, 'volume': 0.032, 'price': 240, 'work_price': 300}
}

def ping_server(app_name):
    """Поддержание активности приложения"""
    while True:
        try:
            requests.get(f"https://{app_name}.onrender.com/", timeout=10)
            logger.info("Пинг выполнен")
        except Exception as e:
            logger.error(f"Ошибка пинга: {str(e)}")
        finally:
            import time
            time.sleep(PING_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка команды /start"""
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("20 см", callback_data='20')],
        [InlineKeyboardButton("30 см", callback_data='30')],
        [InlineKeyboardButton("40 см", callback_data='40')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🔨 Калькулятор строительных блоков\n'
        'Размер блока: 60 см (длина) × 20 см (высота)\n'
        'Выберите ширину камня:',
        reply_markup=reply_markup
    )
    return STONE_WIDTH

async def stone_width(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора ширины камня"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['stone_width'] = query.data
    await query.edit_message_text(text=f"✅ Ширина камня: {query.data} см")
    await query.message.reply_text('📏 Введите ДЛИНУ строения в МЕТРАХ:')
    return STRUCTURE_LENGTH

async def structure_length(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода длины строения"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0:
            raise ValueError
        context.user_data['structure_length'] = length
        await update.message.reply_text('📐 Введите ВЫСОТУ строения в МЕТРАХ:')
        return STRUCTURE_HEIGHT
    except ValueError:
        await update.message.reply_text('❌ Ошибка! Введите число больше 0 (например: 5.2):')
        return STRUCTURE_LENGTH

async def structure_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Расчет и вывод результатов"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0:
            raise ValueError
            
        stone = stone_data[context.user_data['stone_width']]
        length_m = context.user_data['structure_length']
        height_m = height
        
        # Параметры блока (60x20 см)
        block_length = 0.60
        block_height = 0.20
        
        # Расчет количества блоков
        blocks_per_row = length_m / block_length
        rows = height_m / block_height
        total_blocks = blocks_per_row * rows
        
        # Расчет стоимости
        formwork_cost = total_blocks * stone['price']
        work_cost = total_blocks * stone['work_price']
        
        # Расчет арматуры
        rebar_rows = int((rows + 1) // 2)
        rebar_length = length_m * 2
        total_rebar = rebar_rows * rebar_length
        
        # Сохраняем данные для заявки
        context.user_data['calculation'] = {
            'width': stone['width']*100,
            'length': length_m,
            'height': height_m,
            'blocks': total_blocks,
            'concrete': total_blocks * stone['volume'],
            'formwork_cost': formwork_cost,
            'work_cost': work_cost,
            'rebar': total_rebar
        }
        
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
            [InlineKeyboardButton("📞 Оставить заявку", callback_data='consult')],
            [InlineKeyboardButton("🔄 Новый расчет", callback_data='restart')]
        ]
        await update.message.reply_text(
            result,
            reply_markup=InlineKeyboardMarkup(keyboard))
        return FINAL_CALCULATION
        
    except ValueError:
        await update.message.reply_text('❌ Ошибка! Введите число больше 0 (например: 2.5):')
        return STRUCTURE_HEIGHT

async def final_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора после расчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'consult':
        await query.edit_message_text(text="✍️ Введите ваше имя и телефон для связи:\n(Например: Иван +79123456789)")
        return CONTACT_INFO
    elif query.data == 'restart':
        context.user_data.clear()
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="🔄 Начинаем новый расчет! Нажмите /start"
        )
        return ConversationHandler.END

async def contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение контактных данных и отправка заявки"""
    user_data = update.message.text
    calculation = context.user_data.get('calculation', {})
    
    # Формируем заявку
    application = (
        "📌 Новая заявка:\n"
        f"👤 Клиент: {user_data}\n"
        f"📏 Параметры:\n"
        f"- Ширина: {calculation.get('width', 0)} см\n"
        f"- Длина: {calculation.get('length', 0)} м\n"
        f"- Высота: {calculation.get('height', 0)} м\n"
        f"🧮 Расчет:\n"
        f"- Блоки: {calculation.get('blocks', 0):.1f} шт\n"
        f"- Бетон: {calculation.get('concrete', 0):.3f} м³\n"
        f"- Арматура: {calculation.get('rebar', 0):.1f} м\n"
        f"💸 Общая стоимость: {calculation.get('formwork_cost', 0) + calculation.get('work_cost', 0):.2f} ₽"
    )
    
    # Отправляем клиенту
    await update.message.reply_text(
        "✅ Ваша заявка принята! Мы свяжемся с вами в ближайшее время.\n"
        "Для нового расчета нажмите /start"
    )
    
    # Отправляем администратору
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=application
    )
    
    logger.info(f"Новая заявка: {application}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    await update.message.reply_text('❌ Расчет отменен. Для начала нажмите /start')
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=True)
    if update and update.message:
        await update.message.reply_text('⚠️ Произошла ошибка. Пожалуйста, нажмите /start')

def main() -> None:
    """Запуск бота"""
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("Токен не найден!")
        sys.exit(1)

    # Создаем Application
    application = Application.builder().token(TOKEN).build()

    # Обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STONE_WIDTH: [CallbackQueryHandler(stone_width)],
            STRUCTURE_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, structure_length)],
            STRUCTURE_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, structure_height)],
            FINAL_CALCULATION: [CallbackQueryHandler(final_calculation)],
            CONTACT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_info)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    # Режим работы
    if os.getenv('RENDER'):
        PORT = int(os.environ.get('PORT', 8443))
        app_name = os.getenv('RENDER_APP_NAME', 'opalubka')
        
        # Запуск webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"https://{app_name}.onrender.com/",
            drop_pending_updates=True
        )
        logger.info(f"Webhook запущен: https://{app_name}.onrender.com/")
        
        # Запуск потока для пинга
        Thread(target=ping_server, args=(app_name,), daemon=True).start()
    else:
        application.run_polling()
        logger.info("Polling режим")

if __name__ == '__main__':
    main()
    main()
