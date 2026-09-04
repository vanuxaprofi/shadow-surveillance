import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Используем токен напрямую для быстрого теста (в продакшене вернем безопасность!)
BOT_TOKEN = "8949353261:AAGzbCUwPVQJnYr3eJAJhr65CgPY1WkfgNs"
ADMIN_ID = 5008484060

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👁 Начать мониторинг")
    builder.button(text="📊 Мои слежки")
    builder.button(text="🛡 Анти-отслежка")
    builder.button(text="👤 Профиль и Тарифы")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"🕵️‍♂️ **Shadow Surveillance v1.0** приветствует тебя, {message.from_user.first_name}!\n\n"
        f"Система готова к скрытому мониторингу сессий, био и аватарок.\n"
        f"Выберите действие на панели управления:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "👁 Начать мониторинг")
async def start_monitor(message: types.Message):
    await message.answer(
        "Введите `@username` или `ID` цели, за которой хотите установить наблюдение.\n\n"
        "⚠️ _Система автоматически проверит цель на наличие уровней контр-защиты._",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📊 Мои слежки")
async def my_targets(message: types.Message):
    await message.answer(
        "📋 **Список ваших активных слежек:**\n"
        "Занято слотов: 0 из 1 бесплатного.\n\n"
        "У вас пока нет активных целей. Нажмите 'Начать мониторинг', чтобы добавить.",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🛡 Анти-отслежка")
async def anti_track(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡 Активировать «Щит» (Блок)", callback_data="buy_shield")
    builder.button(text="👁 Активировать «Контроль» (Лог)", callback_data="buy_control")
    builder.button(text="🥷 «Полный шпион» (Фейк-логи)", callback_data="buy_spy")
    builder.adjust(1)
    
    await message.answer(
        "🛡 **Модуль Контршпионажа (Анти-отслежка):**\n\n"
        "Вы можете защитить свой аккаунт от отслеживания другими пользователями этого бота:\n\n"
        "1. **«Щит»** — никто не сможет добавить вас в список слежки.\n"
        "2. **«Контроль»** — вы узнаете юзернейм того, кто пытается за вами шпионить.\n"
        "3. **«Полный шпион»** — бот будет скармливать шпиону поддельные (фейковые) логи вашей активности, пока вы будете видеть его действия.",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

@dp.message(F.text == "👤 Профиль и Тарифы")
async def profile_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить Слоты (Telegram Stars)", callback_data="buy_stars")
    
    await message.answer(
        f"👤 **Ваш профиль:**\n"
        f"├ ID: `{message.from_user.id}`\n"
        f"├ Доступ к системе: **Демо-режим**\n"
        f"├ Доступные слоты: **1**\n"
        f"└ Статус Анти-отслежки: **Отключена**",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

# --- АДМИН-ПАНЕЛЬ ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен. Вы не являетесь администратором системы.")
        return
        
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Управление пользователями", callback_data="adm_users")
    builder.button(text="🔑 Управление Юзерботами (Сессии)", callback_data="adm_sessions")
    builder.button(text="🟢 Статус Системы", callback_data="adm_status")
    builder.adjust(1)
    
    await message.answer("🛠 **Панель Администратора Shadow Surveillance**", reply_markup=builder.as_markup())

# --- ОБРАБОТКА ИНЛАЙН КНОПОК (ЗАГЛУШКИ ДЛЯ ТЕСТА) ---
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    await callback.answer("⏳ Модуль оплаты через Telegram Stars находится в режиме разработки.")
    await callback.message.answer("Заявка на активацию отправлена администратору системы!")

async def main():
    logging.info("Демо-версия бота успешно запущена!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

