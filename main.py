import asyncio
import logging
import aiohttp
import ccxt
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
exchange = ccxt.binance()

# --- ВЕБ-СЕРВЕР ДЛЯ KOYEB (АНТИ-СОН) ---
async def handle(request):
    return web.Response(text="Jarvis System: Full Power Mode Online")

# --- ПАРСЕР МАКРО-СОБЫТИЙ (FOREX FACTORY) ---
async def get_forex_calendar():
    url = "https://www.forexfactory.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    events = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # Собираем ключевые события дня
                    rows = soup.select('.calendar__row--featured')[:7]
                    for row in rows:
                        title = row.select_one('.calendar__event-title').text.strip()
                        impact_icon = "🔴" if "high" in str(row).lower() else "🟡"
                        currency = row.select_one('.calendar__currency').text.strip()
                        events.append(f"{impact_icon} **{currency}**: {title}")
    except Exception as e:
        logging.error(f"Ошибка календаря: {e}")
    return "\n".join(events) if events else "Сэр, на сегодня важных макро-событий не обнаружено."

# --- ПОЛУЧЕНИЕ ЦЕН ---
async def get_market_data():
    report = ""
    for coin in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
        try:
            ticker = exchange.fetch_ticker(coin)
            report += f"• {coin}: `${ticker['last']}`\n"
        except: continue
    return report

# --- ДЕТЕКТОР КИТОВ (ФОНОВЫЙ) ---
async def whale_tracker(bot: Bot):
    last_price = None
    while True:
        try:
            ticker = exchange.fetch_ticker('BTC/USDT')
            price = ticker['last']
            if last_price and abs(price - last_price) > 400:
                await bot.send_message(CHANNEL_ID, f"⚠️ **ВНИМАНИЕ, СЭР!**\nОбнаружена активность китов! BTC изменился на ${abs(price - last_price):.2f}\nТекущий курс: `${price}`")
            last_price = price
        except: pass
        await asyncio.sleep(60)

# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    # Запуск сервера для предотвращения спячки Koyeb
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8000).start()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Команда /price для личных сообщений
    @dp.message(Command("price"))
    async def cmd_price(message: types.Message):
        data = await get_market_data()
        await message.answer(f"📊 **Текущий рынок:**\n{data}", parse_mode="Markdown")

    # Формирование супер-отчета при запуске
    prices = await get_market_data()
    calendar = await get_forex_calendar()
    
    welcome_text = (
        f"🧥 **Джарвис: Протокол 'Максимум' активирован**\n\n"
        f"💰 **Котировки:**\n{prices}\n"
        f"📅 **Экономический календарь:**\n{calendar}\n\n"
        f"🐋 Детектор китов: **ОНЛАЙН**\n"
        f"📡 Охота на новости: **АКТИВНА**"
    )

    try:
        await bot.send_message(CHANNEL_ID, welcome_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка отправки в канал: {e}")

    # Запуск фоновых процессов
    asyncio.create_task(whale_tracker(bot))
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
