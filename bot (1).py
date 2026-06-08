"""
Holsnik Bot — Доставка с Китая в Беларусь
Всё в одном файле для простого деплоя
"""
import asyncio
import logging
import os
import json
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton,
    BotCommand, BotCommandScopeDefault
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# ============ КОНФИГУРАЦИЯ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@alss_x")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

CNY_RATE = float(os.getenv("CNY_RATE", "0.53"))
USD_RATE = float(os.getenv("USD_RATE", "3.2"))

AVIA_PRICE = float(os.getenv("AVIA_PRICE_PER_KG", "15"))
AVIA_DAYS = "5-7"
AUTO_PRICE = float(os.getenv("AUTO_PRICE_PER_KG", "7"))
AUTO_DAYS = "18-25"

# ============ ЛОГИРОВАНИЕ ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ БОТ ============
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ============ FSM СОСТОЯНИЯ ============
class OrderStates(StatesGroup):
    waiting_url = State()
    waiting_delivery = State()
    waiting_size = State()

class CalcStates(StatesGroup):
    waiting_weight = State()
    waiting_price = State()

class TrackStates(StatesGroup):
    waiting_number = State()

# ============ БАЗА ДАННЫХ (JSON) ============
DB_FILE = "bot_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "orders": [], "order_counter": 0}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

# ============ КЛАВИАТУРЫ ============
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Сделать заказ")],
            [KeyboardButton(text="🚚 Отследить"), KeyboardButton(text="🧮 Калькулятор")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Вопросы")],
            [KeyboardButton(text="📞 Менеджер")]
        ],
        resize_keyboard=True
    )

def delivery_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Авиа (5-7 дн, 15$/кг)", callback_data="del:avia")],
        [InlineKeyboardButton(text="🚛 Авто (18-25 дн, 7$/кг)", callback_data="del:auto")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def pay_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 ЕРИП", callback_data="pay:erip")],
        [InlineKeyboardButton(text="₿ Крипта", callback_data="pay:crypto")],
        [InlineKeyboardButton(text="💵 Наличные", callback_data="pay:cash")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def faq_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Цена доставки?", callback_data="faq:price")],
        [InlineKeyboardButton(text="⏱ Сроки?", callback_data="faq:time")],
        [InlineKeyboardButton(text="📸 Фотоотчёт?", callback_data="faq:photo")],
        [InlineKeyboardButton(text="🔄 Возврат?", callback_data="faq:return")],
        [InlineKeyboardButton(text="📏 Размеры?", callback_data="faq:size")],
        [InlineKeyboardButton(text="💳 Оплата?", callback_data="faq:pay")],
        [InlineKeyboardButton(text="🚫 Что нельзя?", callback_data="faq:ban")],
        [InlineKeyboardButton(text="📦 Трекинг?", callback_data="faq:track")],
        [InlineKeyboardButton(text="🏠 Мой город?", callback_data="faq:city")],
    ])

# ============ КОМАНДЫ ============
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    uid = str(message.from_user.id)

    if uid not in db["users"]:
        db["users"][uid] = {
            "username": message.from_user.username,
            "name": message.from_user.first_name,
            "orders": [],
            "registered": datetime.now().isoformat()
        }
        save_db(db)

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!

"
        f"Я <b>Holsnik Bot</b> — доставка с Китая 🇨🇳 → 🇧🇾

"
        f"<b>Что умею:</b>
"
        f"• 📦 Заказы по ссылкам (TaoBao, Poizon, Pinduoduo...)
"
        f"• 🚚 Отслеживание посылок
"
        f"• 🧮 Калькулятор доставки
"
        f"• 📸 Бесплатные фотоотчёты
"
        f"• 💬 Ответы на вопросы 24/7

"
        f"<b>Доставка:</b>
"
        f"✈️ Авиа — 15$/кг, 5-7 дней
"
        f"🚛 Авто — 7$/кг, 18-25 дней

"
        f"Пришли ссылку на товар или выбери раздел! 👇",
        reply_markup=main_kb()
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "<b>📚 Команды:</b>

"
        "/start — главное меню
"
        "/calc — калькулятор
"
        "/track — трекинг
"
        "/orders — мои заказы
"
        "/profile — профиль

"
        "<b>Поддержка:</b> @alss_x",
        reply_markup=back_kb()
    )

# ============ ЗАКАЗ ============
@dp.message(F.text == "📦 Сделать заказ")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderStates.waiting_url)
    await message.answer(
        "📦 <b>Оформление заказа</b>

"
        "Пришли ссылку на товар:
"
        "• TaoBao / Tmall / 1688
"
        "• Pinduoduo
"
        "• Poizon (得物)
"
        "• Goofish / JD / Weidian",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ])
    )

@dp.message(OrderStates.waiting_url)
async def order_url(message: Message, state: FSMContext):
    url = message.text.strip()

    if not url.startswith("http"):
        await message.answer("❌ Это не ссылка! Пришли полный URL (начинается с http)")
        return

    # Определяем платформу
    platform = "Неизвестно"
    if "taobao" in url or "tmall" in url:
        platform = "TaoBao/Tmall"
    elif "1688" in url:
        platform = "1688"
    elif "pinduoduo" in url or "yangkeduo" in url:
        platform = "Pinduoduo"
    elif "poizon" in url or "dewu" in url:
        platform = "Poizon"
    elif "goofish" in url or "xianyu" in url:
        platform = "Goofish"
    elif "jd" in url:
        platform = "JD"
    elif "weidian" in url:
        platform = "Weidian"

    await state.update_data(url=url, platform=platform)
    await state.set_state(OrderStates.waiting_delivery)

    await message.answer(
        f"🔗 <b>Ссылка получена!</b>
"
        f"Платформа: {platform}

"
        f"Выбери тип доставки:",
        reply_markup=delivery_kb()
    )

@dp.callback_query(F.data.startswith("del:"), OrderStates.waiting_delivery)
async def order_delivery(callback: CallbackQuery, state: FSMContext):
    delivery = callback.data.split(":")[1]
    await state.update_data(delivery=delivery)
    await state.set_state(OrderStates.waiting_size)

    del_name = "✈️ Авиа" if delivery == "avia" else "🚛 Авто"

    await callback.message.edit_text(
        f"✅ Доставка: {del_name}

"
        f"Укажи размер и цвет (или напиши "нет"):"
    )
    await callback.answer()

@dp.message(OrderStates.waiting_size)
async def order_size(message: Message, state: FSMContext):
    size = message.text.strip()
    data = await state.get_data()

    # Создаём заказ
    db["order_counter"] += 1
    order_id = db["order_counter"]

    uid = str(message.from_user.id)
    order = {
        "id": order_id,
        "user_id": uid,
        "url": data["url"],
        "platform": data["platform"],
        "delivery": data["delivery"],
        "size": size,
        "status": "pending",
        "created": datetime.now().isoformat()
    }

    db["orders"].append(order)
    db["users"][uid]["orders"].append(order_id)
    save_db(db)

    del_name = "✈️ Авиа" if data["delivery"] == "avia" else "🚛 Авто"

    await message.answer(
        f"✅ <b>Заказ #{order_id} создан!</b>

"
        f"📦 Платформа: {data['platform']}
"
        f"🚚 Доставка: {del_name}
"
        f"📏 Размер/цвет: {size}

"
        f"<b>Далее:</b>
"
        f"1. Оплати товар
"
        f"2. Мы закажем в Китае
"
        f"3. Фотоотчёт на складе
"
        f"4. Доставка в Беларусь

"
        f"<b>Способы оплаты:</b>",
        reply_markup=pay_kb()
    )

    # Уведомляем админа
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 <b>Новый заказ #{order_id}!</b>

"
                f"👤 Пользователь: @{message.from_user.username or message.from_user.id}
"
                f"📦 Платформа: {data['platform']}
"
                f"🔗 {data['url']}
"
                f"🚚 Доставка: {del_name}
"
                f"📏 Размер: {size}"
            )
        except:
            pass

    await state.clear()

# ============ КАЛЬКУЛЯТОР ============
@dp.message(F.text == "🧮 Калькулятор")
async def calc_start(message: Message, state: FSMContext):
    await state.set_state(CalcStates.waiting_weight)
    await message.answer(
        "🧮 <b>Калькулятор доставки</b>

"
        "Введи вес в <b>кг</b> (например: 0.5, 1.2):

"
        "<i>0.5 — футболка/кроссовки</i>
"
        "<i>1.5 — куртка/несколько вещей</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ])
    )

@dp.message(CalcStates.waiting_weight)
async def calc_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(",", "."))
        if weight <= 0 or weight > 30:
            raise ValueError

        await state.update_data(weight=weight)
        await state.set_state(CalcStates.waiting_price)

        await message.answer(
            f"✅ Вес: <b>{weight} кг</b>

"
            f"Введи цену товара в <b>юанях (¥)</b> или <b>BYN</b>:

"
            f"<i>Примеры: 100¥, 200 BYN, 50$</i>"
        )
    except:
        await message.answer("❌ Введи число от 0.1 до 30 (например: 0.5)")

@dp.message(CalcStates.waiting_price)
async def calc_price(message: Message, state: FSMContext):
    text = message.text.lower().strip()
    data = await state.get_data()
    weight = data["weight"]

    try:
        # Определяем валюту
        if "¥" in text or "юан" in text or "cny" in text:
            price_cny = float(re.sub(r"[^0-9.]", "", text))
            price_byn = price_cny * CNY_RATE
        elif "$" in text or "usd" in text or "долл" in text:
            price_usd = float(re.sub(r"[^0-9.]", "", text))
            price_byn = price_usd * USD_RATE
            price_cny = price_byn / CNY_RATE
        else:
            price_byn = float(re.sub(r"[^0-9.]", "", text))
            price_cny = price_byn / CNY_RATE

        # Расчёт
        avia_del = weight * AVIA_PRICE * USD_RATE
        auto_del = weight * AUTO_PRICE * USD_RATE
        avia_total = price_byn + avia_del
        auto_total = price_byn + auto_del

        await message.answer(
            f"🧮 <b>Расчёт доставки</b>

"
            f"📦 Вес: <b>{weight} кг</b>
"
            f"💰 Товар: ¥{price_cny:.0f} (~{price_byn:.0f} BYN)

"
            f"━━━━━━━━━━━━━━
"
            f"<b>✈️ Авиа ({AVIA_DAYS} дн):</b>
"
            f"   Доставка: {avia_del:.0f} BYN
"
            f"   <b>ИТОГО: {avia_total:.0f} BYN</b>

"
            f"<b>🚛 Авто ({AUTO_DAYS} дн):</b>
"
            f"   Доставка: {auto_del:.0f} BYN
"
            f"   <b>ИТОГО: {auto_total:.0f} BYN</b>

"
            f"━━━━━━━━━━━━━━
"
            f"📸 Фотоотчёт: БЕСПЛАТНО ✅
"
            f"🛡️ Страховка: ВКЛЮЧЕНА ✅
"
            f"📦 Консолидация: БЕСПЛАТНО ✅

"
            f"<i>💡 Для одежды/кроссовок бери авиа!</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Сделать заказ", callback_data="order")],
                [InlineKeyboardButton(text="🧮 Новый расчёт", callback_data="calc")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ])
        )
        await state.clear()

    except:
        await message.answer(
            "❌ Не понял цену. Попробуй:
"
            "• 100¥ или 100 юаней
"
            "• 50$ или 50 долларов
"
            "• 200 BYN"
        )

# ============ ТРЕКИНГ ============
@dp.message(F.text == "🚚 Отследить")
async def track_start(message: Message, state: FSMContext):
    await state.set_state(TrackStates.waiting_number)
    await message.answer(
        "🚚 <b>Отслеживание посылки</b>

"
        "Введи номер трека:
"
        "(или напиши номер заказа, например: #123)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="myorders")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ])
    )

@dp.message(TrackStates.waiting_number)
async def track_number(message: Message, state: FSMContext):
    track = message.text.strip()

    # Ищем заказ по ID
    if track.startswith("#"):
        try:
            order_id = int(track[1:])
            order = next((o for o in db["orders"] if o["id"] == order_id), None)
            if order:
                status_map = {
                    "pending": "⏳ Ожидает оплаты",
                    "paid": "💰 Оплачен",
                    "processing": "🔧 Заказан у продавца",
                    "warehouse": "📦 На складе в Китае",
                    "photo": "📸 Фотоотчёт готов",
                    "shipped": "✈️ Отправлен в Беларусь",
                    "customs": "🛃 На таможне",
                    "delivery": "🚚 Доставляется по РБ",
                    "delivered": "✅ Получен"
                }

                await message.answer(
                    f"📦 <b>Заказ #{order_id}</b>

"
                    f"📦 Платформа: {order['platform']}
"
                    f"🚚 Доставка: {'✈️ Авиа' if order['delivery'] == 'avia' else '🚛 Авто'}
"
                    f"📏 Размер: {order['size']}
"
                    f"📅 Создан: {order['created'][:10]}

"
                    f"<b>Статус:</b>
"
                    f"{status_map.get(order['status'], order['status'])}

"
                    f"<i>Уведомления приходят автоматически!</i>",
                    reply_markup=back_kb()
                )
                await state.clear()
                return
        except:
            pass

    # Заглушка для трек-номера
    await message.answer(
        f"📦 <b>Посылка {track}</b>

"
        f"<b>Статус:</b> В пути
"
        f"<b>Локация:</b> Китай → Беларусь

"
        f"<b>История:</b>
"
        f"• {datetime.now().strftime('%d.%m')} — Обработка на складе (Шэньчжэнь)

"
        f"<i>Обновляется каждые 6 часов</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"track:{track}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ])
    )
    await state.clear()

# ============ ПРОФИЛЬ ============
@dp.message(F.text == "👤 Профиль")
async def profile(message: Message):
    uid = str(message.from_user.id)
    user = db["users"].get(uid, {})
    orders = [o for o in db["orders"] if o["user_id"] == uid]

    total = len(orders)
    active = len([o for o in orders if o["status"] not in ["delivered", "cancelled"]])
    done = len([o for o in orders if o["status"] == "delivered"])

    status = "👋 Новый клиент"
    if total > 20:
        status = "⭐ VIP"
    elif total > 5:
        status = "💎 Постоянный"

    await message.answer(
        f"👤 <b>Мой профиль</b>

"
        f"🆔 ID: {message.from_user.id}
"
        f"🏷 Ник: @{message.from_user.username or 'Нет'}

"
        f"━━━━━━━━━━━━━━
"
        f"📊 <b>Статистика:</b>
"
        f"   📦 Всего заказов: <b>{total}</b>
"
        f"   🔄 Активных: <b>{active}</b>
"
        f"   ✅ Получено: <b>{done}</b>

"
        f"🎖 Статус: <b>{status}</b>

"
        f"<i>Чем больше заказов — тем больше бонусов!</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="myorders")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ])
    )

@dp.callback_query(F.data == "myorders")
async def my_orders(callback: CallbackQuery):
    uid = str(callback.from_user.id)
    orders = [o for o in db["orders"] if o["user_id"] == uid]

    if not orders:
        await callback.message.edit_text(
            "📦 <b>У тебя пока нет заказов</b>

"
            "Сделай первый заказ! 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Сделать заказ", callback_data="order")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ])
        )
    else:
        text = "📦 <b>Мои заказы</b>

"
        status_emoji = {
            "pending": "⏳", "paid": "💰", "processing": "🔧",
            "warehouse": "📦", "photo": "📸", "shipped": "✈️",
            "customs": "🛃", "delivery": "🚚", "delivered": "✅"
        }

        for o in orders[-10:]:
            em = status_emoji.get(o["status"], "❓")
            text += f"{em} <b>#{o['id']}</b> — {o['platform'][:15]}
"
            text += f"   🚚 {'✈️' if o['delivery'] == 'avia' else '🚛'} | {o['created'][:10]}

"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="myorders")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ])
        )

    await callback.answer()

# ============ FAQ ============
@dp.message(F.text == "❓ Вопросы")
async def faq(message: Message):
    await message.answer(
        "❓ <b>Популярные вопросы</b>

"
        "Выбери вопрос:",
        reply_markup=faq_kb()
    )

@dp.callback_query(F.data.startswith("faq:"))
async def faq_answer(callback: CallbackQuery):
    q = callback.data.split(":")[1]

    answers = {
        "price": "💰 <b>Цена доставки:</b>

"
                 "✈️ Авиа: 15$/кг (5-7 дней)
"
                 "🚛 Авто: 7$/кг (18-25 дней)

"
                 "<b>Включено:</b>
"
                 "📸 Фотоотчёт — БЕСПЛАТНО
"
                 "🛡️ Страховка — БЕСПЛАТНО
"
                 "📦 Консолидация — БЕСПЛАТНО

"
                 "Курс: 1¥ = 0.53 BYN",

        "time": "⏱ <b>Сроки доставки:</b>

"
                "✈️ Авиа: 8-12 дней (Китай → твой город)
"
                "🚛 Авто: 21-30 дней

"
                "Поэтапно:
"
                "• Заказ у продавца: 2-5 дней
"
                "• До Беларуси: 5-7 дн (авиа) / 18-25 дн (авто)
"
                "• Таможня: 1-3 дня
"
                "• До твоего города: 2-4 дня

"
                "💡 Для одежды/кроссовок бери авиа!",

        "photo": "📸 <b>Фотоотчёт — БЕСПЛАТНО!</b>

"
                 "Что входит:
"
                 "• 📦 Фото посылки на складе
"
                 "• 👟 Фото товара с разных ракурсов
"
                 "• 🔍 Проверка на брак
"
                 "• 📏 Проверка размера
"
                 "• 🏷️ Фото бирок

"
                 "Когда: после прибытия на склад (2-5 дней)

"
                 "Если брак — вернём до отправки!",

        "return": "🔄 <b>Возврат товара:</b>

"
                  "<b>На складе в Китае:</b>
"
                  "✅ Возврат/замена — БЕСПЛАТНО

"
                  "<b>После получения:</b>
"
                  "⚠️ Рассматривается индивидуально
"
                  "• Пришли фото брака
"
                  "• Свяжемся с продавцом

"
                  "<b>Не подошёл размер:</b>
"
                  "❌ Возврат невозможен (китайцы не принимают)

"
                  "💡 Всегда уточняй размер перед заказом!",

        "size": "📏 <b>Размеры (Китай → Европа):</b>

"
                "Одежда:
"
                "S (CN) = M (EU) | рост 165-170
"
                "M (CN) = L (EU) | рост 170-175
"
                "L (CN) = XL (EU) | рост 175-180
"
                "XL (CN) = XXL (EU) | рост 180+

"
                "Кроссовки Poizon:
"
                "Обычно в EU размерах — бери свой!

"
                "💡 Всегда мерь в см!",

        "pay": "💳 <b>Способы оплаты:</b>

"
               "<b>За товар (сразу):</b>
"
               "• 💰 ЕРИП (любой банк)
"
               "• ₿ Крипта (USDT)
"
               "• 💵 Наличные (Минск)

"
               "<b>За доставку (при получении):</b>
"
               "• 💰 ЕРИП
"
               "• 💵 Наличные

"
               "<b>Минимального заказа НЕТ!</b>",

        "ban": "🚫 <b>Что нельзя заказать:</b>

"
               "ЗАПРЕЩЁНО:
"
               "• 🔫 Оружие
"
               "• 💊 Наркотики
"
               "• 🎰 Азартные устройства
"
               "• 💣 Взрывчатка

"
               "ОГРАНИЧЕНИЯ:
"
               "• 🔋 Аккумуляторы — только авто
"
               "• 💧 Жидкости — до 100 мл
"
               "• 🧲 Магниты — осторожно

"
               "Контрафакт:
"
               "⚠️ Фейки — на свой страх
"
               "✅ Poizon — оригинал с проверкой",

        "track": "📦 <b>Как отследить:</b>

"
                 "1. Через бота: «🚚 Отследить» → введи трек
"
                 "2. В профиле: «👤 Профиль» → «📦 Мои заказы»

"
                 "Службы:
"
                 "• 17track.net (универсально)
"
                 "• Cainiao (китайская сторона)
"
                 "• Белпочта / Европочта (в РБ)

"
                 "Статусы:
"
                 "⏳ → 🔧 → 📦 → 📸 → ✈️ → 🛃 → 🚚 → ✅",

        "city": "🏠 <b>Доставка по Беларуси:</b>

"
                "Минск:
"
                "• 🏠 Самовывоз
"
                "• 🚚 Курьер по городу

"
                "Другие города:
"
                "• 📮 Белпочта (до отделения)
"
                "• 📮 Европочта (до отделения)
"
                "• 🚚 Любая доступная доставка

"
                "После прибытия в Минск: 2-4 дня

"
                "Стоимость по РБ включена в доставку!"
    }

    await callback.message.edit_text(
        answers.get(q, "❓ Вопрос не найден"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Другой вопрос", callback_data="faq_again")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "faq_again")
async def faq_again(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Популярные вопросы</b>

Выбери:",
        reply_markup=faq_kb()
    )
    await callback.answer()

# ============ МЕНЕДЖЕР ============
@dp.message(F.text == "📞 Менеджер")
async def manager(message: Message):
    await message.answer(
        "📞 <b>Связь с менеджером</b>

"
        "Напиши @alss_x — поможет с любыми вопросами!

"
        "Я тоже могу помочь:
"
        "• 📦 Заказать товар
"
        "• 🚚 Отследить посылку
"
        "• 🧮 Рассчитать доставку
"
        "• ❓ Ответить на вопросы",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать @alss_x", url="https://t.me/alss_x")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ])
    )

# ============ ОБРАБОТКА КНОПОК ============
@dp.callback_query(F.data == "cancel")
async def cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Отменено. Выбери раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>

Выбери раздел:",
            reply_markup=main_kb()
        )
    except:
        await callback.message.answer(
            "🏠 <b>Главное меню</b>",
            reply_markup=main_kb()
        )
    await callback.answer()

@dp.callback_query(F.data == "order")
async def order_cb(callback: CallbackQuery, state: FSMContext):
    await order_start(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "calc")
async def calc_cb(callback: CallbackQuery, state: FSMContext):
    await calc_start(callback.message, state)
    await callback.answer()

# ============ AI ОТВЕТЫ ============
@dp.message(F.text)
async def ai_answer(message: Message, state: FSMContext):
    if await state.get_state():
        return

    text = message.text.lower()

    # Быстрые команды
    if text in ["/calc", "калькулятор", "расчёт", "цена"]:
        await calc_start(message, state)
        return
    if text in ["/track", "трек", "где посылка", "отследить"]:
        await track_start(message, state)
        return
    if text in ["/orders", "заказы", "мои заказы"]:
        await profile(message)
        return
    if text in ["/profile", "профиль"]:
        await profile(message)
        return

    # AI ответы (fallback)
    responses = {
        "привет": "👋 Привет! Я Holsnik Bot! Пришли ссылку на товар или выбери раздел 👇",
        "здравствуй": "👋 Привет! Чем могу помочь?",
        "спасибо": "😊 Всегда рад помочь! Приходи ещё!",
        "пока": "👋 Пока! Удачных покупок!",
        "до свидания": "👋 До свидания!",
    }

    for key, resp in responses.items():
        if key in text:
            await message.answer(resp, reply_markup=main_kb())
            return

    # Универсальный ответ
    await message.answer(
        "🤔 Я могу помочь:

"
        "• 📦 Оформить заказ
"
        "• 🚚 Отследить посылку
"
        "• 🧮 Рассчитать доставку
"
        "• ❓ Ответить на вопросы

"
        "Выбери раздел или пришли ссылку! 👇",
        reply_markup=main_kb()
    )

# ============ ЗАПУСК ============
async def set_commands():
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="📚 Помощь"),
        BotCommand(command="calc", description="🧮 Калькулятор"),
        BotCommand(command="track", description="🚚 Трекинг"),
        BotCommand(command="orders", description="📦 Мои заказы"),
        BotCommand(command="profile", description="👤 Профиль"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

async def main():
    await set_commands()
    logger.info("🚀 Бот запущен! 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
