import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from sqlalchemy import select, update

# Конфигурация проекта
from config import BOT_TOKEN, ADMIN_ID
from database import init_db, async_session, User

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 8000))
SUPPORT_LINK = "@HELPshadowsurveillance_bot"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ДЛЯ КЛИЕНТА (ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ) ---
def get_client_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="💳 Выбрать Тариф")
    builder.button(text="🆘 Поддержка")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- КЛАВИАТУРЫ ДЛЯ АДМИНИСТРАТОРА ---
def get_admin_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👁 Поставить на мониторинг")
    builder.button(text="📊 Активные цели")
    builder.button(text="🛡 Настройка Анти-отслежки")
    builder.button(text="📥 Заявки пользователей")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# --- ОБРАБОТКА СТАРТА ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"id{user_id}"
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Администратору сразу даем полный доступ, обычным пользователям — нет
            is_admin = (user_id == ADMIN_ID)
            user = User(
                tg_id=user_id,
                username=username,
                has_access=is_admin,
                total_slots=5 if is_admin else 0,
                anti_track_level="none"
            )
            session.add(user)
            await session.commit()
            
    # Разделение интерфейса при старте
    if user_id == ADMIN_ID:
        await message.answer(
            f"🛠 **Добро пожаловать, Администратор!**\n"
            f"Система Shadow Surveillance полностью в вашем распоряжении.\n"
            f"Управление пулом юзерботов и контр-защитой активировано.",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            f"🕵️‍♂️ **Система скрытого мониторинга Shadow Surveillance**\n\n"
            f"Для получения доступа к мониторингу сессий, изменений био, юзернеймов и аватарок вам необходимо приобрести подписку.\n\n"
            f"По всем вопросам: {SUPPORT_LINK}",
            reply_markup=get_client_menu()
        )

# ========================================================
# ЛОГИКА ОБЫЧНОГО ПОЛЬЗОВАТЕЛЯ (ПОКУПКА И ТАРИФЫ)
# ========================================================

@dp.message(F.text == "💳 Выбрать Тариф")
async def client_tariffs(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Тариф 'Старт' (1 слот)", callback_data="buy_t_start")
    builder.button(text="⭐ Тариф 'Про' (5 слотов)", callback_data="buy_t_pro")
    builder.adjust(1)
    
    await message.answer(
        "📋 **Доступные тарифные планы Shadow Surveillance:**\n\n"
        "1. **Старт** — Мониторинг 1 аккаунта, базовая история аватарок.\n"
        "2. **Про** — До 5 аккаунтов на контроле + уведомления о смене BIO.\n\n"
        f"Для оформления ручной активации: {SUPPORT_LINK}",
        reply_markup=builder.as_markup()
    )

@dp.message(F.text == "🆘 Поддержка")
async def client_support(message: types.Message):
    await message.answer(f"По любым вопросам, ошибкам оплаты или предложениям обращайтесь в официальный аккаунт поддержки:\n\n👉 {SUPPORT_LINK}")

@dp.callback_query(F.data.startswith("buy_t_"))
async def process_tariff_request(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or f"id{user_id}"
    tariff_type = callback.data.replace("buy_t_", "")
    
    # Отправляем уведомление админу
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Активировать", callback_data=f"adm_app_{user_id}_{tariff_type}")
    builder.button(text="❌ Отклонить", callback_data=f"adm_den_{user_id}")
    builder.adjust(2)
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **Новая заявка на покупку!**\nПользователь: @{username} (ID: `{user_id}`)\nЗапрашивает тариф: **{tariff_type.upper()}**",
            reply_markup=builder.as_markup()
        )
    except Exception:
        pass
        
    await callback.answer("Заявка на покупку отправлена администратору!", show_alert=True)
    await callback.message.answer(f"⏳ Ваша заявка передана администратору. Ожидайте уведомления здесь или напишите: {SUPPORT_LINK}")

# ========================================================
# ЛОГИКА АДМИНИСТРАТОРА (ШПИОНАЖ, АНТИ-ОТСЛЕЖКА, ЗАЯВКИ)
# ========================================================

@dp.message(Command("admin"))
async def cmd_admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"❌ Доступ запрещен. Обратитесь: {SUPPORT_LINK}")
        return
    await message.answer("🛠 Вы в панели администратора. Используйте нижние Reply-кнопки для управления системой.")

@dp.message(F.text == "👁 Поставить на мониторинг")
async def admin_ask_target(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Введите `@username` цели для постановки на слежку (сессии, био, аватарки):")

@dp.message(F.text.startswith("@") & (F.from_user.id == ADMIN_ID))
async def admin_process_target(message: types.Message):
    target_username = message.text.replace("@", "").strip()
    
    async with async_session() as session:
        # Проверяем контр-защиту цели (Пункт 17 ТЗ)
        result = await session.execute(select(User).where(User.username == target_username))
        target = result.scalar_one_or_none()
        
        if target:
            if target.anti_track_level == "shield":
                await message.answer(f"❌ **Заблокировано!** Аккаунт `@{target_username}` защищен уровнем «Щит».")
                return
            elif target.anti_track_level == "control":
                await message.answer(f"🟢 Цель `@{target_username}` добавлена. (Сработал «Контроль» — цель получила скрытое уведомление).")
                try:
                    await bot.send_message(chat_id=target.tg_id, text="⚠️ **Обнаружена попытка отслеживания вашего профиля системой Shadow Surveillance!**")
                except Exception: pass
                return
            elif target.anti_track_level == "full_spy":
                await message.answer(f"🟢 Цель `@{target_username}` добавлена. (Сработал «Полный шпион» — вам будут отправляться фейк-логи).")
                try:
                    await bot.send_message(chat_id=target.tg_id, text="🥷 **Сработал «Полный шпион»!** Бот начал скармливать шпиону ложные данные.")
                except Exception: pass
                return
                
        await message.answer(f"🟢 Цель `@{target_username}` успешно поставлена на мониторинг сессий через MTProto.")

@dp.message(F.text == "📊 Активные цели")
async def admin_list_targets(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📋 **Список объектов на мониторинге:**\n\n_Пока нет активных целей сессий. Используйте кнопку контроля._", parse_mode="Markdown")

@dp.message(F.text == "🛡 Настройка Anti-track")
async def admin_anti_track_settings(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡 Уровень «Щит» (Полный блок)", callback_data="adm_set_shield")
    builder.button(text="👁 Уровень «Контроль» (Лог)", callback_data="adm_set_control")
    builder.button(text="🥷 Уровень «Полный шпион» (Фейк-логи)", callback_data="adm_set_spy")
    builder.adjust(1)
    
    await message.answer("⚙️ **Контр-защита администратора:**\nУстановите уровень безопасности для вашего личного аккаунта:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("adm_set_"))
async def admin_save_anti_track(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    level = callback.data.replace("adm_set_", "")
    db_level = "shield" if level == "shield" else ("control" if level == "control" else "full_spy")
    
    async with async_session() as session:
        await session.execute(update(User).where(User.tg_id == ADMIN_ID).values(anti_track_level=db_level))
        await session.commit()
        
    await callback.answer(f"Защита {db_level} активирована!", show_alert=True)

@dp.message(F.text == "📥 Заявки пользователей")
async def admin_view_requests(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📥 На данный момент входящих заявок на тарифы нет.")

# --- ОБРАБОТКА ОДОБРЕНИЯ ЗАЯВОК АДМИНОМ ---
@dp.callback_query(F.data.startswith("adm_app_"))
async def admin_approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = callback.data.replace("adm_app_", "").split("_")
    client_id = int(data[0])
    tariff = data[1]
    
    slots = 1 if tariff == "start" else 5
    
    async with async_session() as session:
        await session.execute(update(User).where(User.tg_id == client_id).values(has_access=True, total_slots=slots))
        await session.commit()
        
    await callback.message.edit_text(f"✅ Доступ для ID {client_id} успешно активирован (Тариф {tariff.upper()}).")
    try:await bot.send_message(chat_id=client_id, text=f"🎉 Ваша заявка одобрена! Доступ к системе Shadow Surveillance активирован.\nПо любым вопросам: {SUPPORT_LINK}")except Exception: pass@dp.callback_query(F.data.startswith("adm_den_"))async def admin_deny(callback: types.CallbackQuery):if callback.from_user.id != ADMIN_ID: returnclient_id = int(callback.data.replace("adm_den_", ""))await callback.message.edit_text("❌ Заявка пользователя отклонена.")--- ВЕБХУКИ ---async def on_startup(bot: Bot) -> None:await init_db()webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"await bot.set_webhook(webhook_url)def main():app = web.Application()webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)webhook_requests_handler.register(app, path="/webhook")setup_application(app, dp, bot=bot)dp.startup.register(on_startup)web.run_app(app, host="0.0.0.0", port=PORT)if name == "main":main()
