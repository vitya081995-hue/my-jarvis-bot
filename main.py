import asyncio
import logging
import aiohttp
import ccxt
import feedparser
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

logging.basicConfig(level=logging.INFO)
exchange = ccxt.binance()

async def handle(request):
    return web.Response(text="Jarvis: Geo-Political Monitoring Active")

# --- ГОРЯЧИЕ НОВОСТИ (BREAKING NEWS) ---
async def get_breaking_news():
    """Парсит мировые новости для поиска 'Черных лебедей'"""
    # Используем RSS ленту мировых новостей (Reuters/Investing)
    feed_url = "https://www.investing.com/rss/news_285.rss" 
    try:
        feed = feedparser.parse(feed_url)
        top_news = []
        for entry in feed.entries[:3]:
            top_news.append(f"🔥 {entry.title}")
        return "\n".join(top_news)
    except:
        return "Сэр, новостные каналы перегружены, слежу за котировками."

# --- ЭКОНОМИЧЕСКИЙ КАЛЕНДАРЬ ---
async def get_forex_calendar():
    url = "https://www.forexfactory.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    events = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                rows = soup.select('.calendar__row--featured')[:5]
                for row in rows:
                    title = row.select_one('.calendar__event-title').text.strip()
                    currency = row.select_one('.calendar__currency').text.strip()
                    events.append(f"• **{currency}**: {title}")
    except: pass
    return "\n".join(events) if events else "🏦 Выходной/Праздник. Фокус на геополитике."

async def get_prices():
    try:
        btc = exchange.fetch_ticker('BTC/USDT')['last']
        eth = exchange.fetch_ticker('ETH/USDT')['last']
        return f"₿ BTC: `${btc}`\nΞ ETH: `${eth}`"
    except: return "Ошибка получения цен."

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8000).start()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # --- ЭКСТРЕННЫЙ ВЫПУСК ПРИ ЗАПУСКЕ ---
    prices = await get_prices()
    news = await get_breaking_news()
    calendar = await get_forex_calendar()
    
    alert_text = (
        f"🚨 **ЭКСТРЕННЫЙ ДОКЛАД ДЖАРВИСА**\n\n"
        f"📍 **ГЕОПОЛИТИКА:**\nСША - ВЕНЕСУЭЛА: Конфликт в активной фазе. Мадуро захвачен. Рынки в режиме неопределенности.\n\n"
        f"💰 **РЫНОК СЕЙЧАС:**\n{prices}\n\n"
        f"📅 **КАЛЕНДАРЬ:**\n{calendar}\n\n"
        f"🗞️ **ПОСЛЕДНИЕ ЗАГОЛОВКИ:**\n{news}\n\n"
        f"🛡️ *Сэр, я перехожу в режим повышенной готовности.*"
    )
    
    await bot.send_message(CHANNEL_ID, alert_text, parse_mode="Markdown")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
