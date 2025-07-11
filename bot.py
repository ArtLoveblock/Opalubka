
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
import asyncio

API_TOKEN = "7736990857:AAHEocRVYal13QDxM-HFaQA8b7llWJC_z6g"
ADMIN_ID = 5559554783

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
user_data = {}

def width_keyboard():
    kb = InlineKeyboardBuilder()
    for width in ["20", "30", "40"]:
        kb.button(text=f"{width} см", callback_data=f"width:{width}")
    return kb.as_markup()

def back_keyboard(step):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅ Назад", callback_data=f"back:{step}")
    return kb.as_markup()

@dp.message(F.text == "/start")
async def start(message: Message):
    user_data[message.from_user.id] = {}
    await message.answer("Выберите ширину блока:", reply_markup=width_keyboard())

@dp.callback_query(F.data.startswith("width:"))
async def get_width(callback: CallbackQuery):
    width = int(callback.data.split(":")[1])
    user_data[callback.from_user.id]["width"] = width
    await callback.message.edit_text("Введите длину строения (в метрах):", reply_markup=back_keyboard("start"))

@dp.message(F.text.regexp(r"^[\d.]+$"))
async def get_dimensions(message: Message):
    uid = message.from_user.id
    data = user_data.get(uid, {})
    if "length" not in data and "width" in data:
        data["length"] = float(message.text.replace(",", "."))
        await message.answer("Теперь введите высоту строения (в метрах):", reply_markup=back_keyboard("length"))
    elif "length" in data and "width" in data and "height" not in data:
        data["height"] = float(message.text.replace(",", "."))
        await calculate_and_send(message, data)
    else:
        await message.answer("Пожалуйста, начните сначала: /start")

async def calculate_and_send(message: Message, data: dict):
    uid = message.from_user.id
    width = data["width"]
    length = data["length"]
    height = data["height"]

    block_length_m = 0.6
    block_height_m = 0.2
    blocks_per_row = length / block_length_m
    rows = height / block_height_m
    total_blocks = blocks_per_row * rows

    concrete_per_block = {20: 0.016, 30: 0.024, 40: 0.032}[width]
    total_concrete = total_blocks * concrete_per_block
    price_per_block = {20: 190, 30: 205, 40: 240}[width]
    total_price_blocks = total_blocks * price_per_block

    rows_int = int(rows)
    rebar_runs = (rows_int // 2 + 1) * 2
    rebar_total_m = rebar_runs * length
    rebar_price = rebar_total_m * 25
    labor_price = total_blocks * 300
    total_price = total_price_blocks + rebar_price + labor_price

    text = (
        f"<b>📐 Расчёт:</b>\n"
        f"Блок: {width} см\n"
        f"Длина: {length} м\n"
        f"Высота: {height} м\n\n"
        f"🔹 Блоков нужно: <b>{total_blocks:.2f} шт</b>\n"
        f"🔹 Бетона: <b>{total_concrete:.2f} м³</b>\n"
        f"🔹 Арматура: <b>{rebar_total_m:.2f} м</b>\n\n"
        f"💰 Цена блоков: <b>{total_price_blocks:,.0f}₽</b>\n"
        f"💰 Арматура: <b>{rebar_price:,.0f}₽</b>\n"
        f"💰 Работа: <b>{labor_price:,.0f}₽</b>\n\n"
        f"🏗️ Всё под ключ: <b>{total_price:,.0f}₽</b>"
    )

    await message.answer(text, reply_markup=back_keyboard("height"))
    await bot.send_message(ADMIN_ID, f"Новый расчёт от @{message.from_user.username or message.from_user.full_name}:\n\n{text}")

@dp.callback_query(F.data.startswith("back:"))
async def go_back(callback: CallbackQuery):
    step = callback.data.split(":")[1]
    uid = callback.from_user.id
    if step == "start":
        user_data.pop(uid, None)
        await callback.message.edit_text("Выберите ширину блока:", reply_markup=width_keyboard())
    elif step == "length":
        await callback.message.edit_text("Введите длину строения (в метрах):", reply_markup=back_keyboard("start"))
        user_data[uid].pop("length", None)
    elif step == "height":
        await callback.message.edit_text("Введите высоту строения (в метрах):", reply_markup=back_keyboard("length"))
        user_data[uid].pop("height", None)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
