import asyncio
import logging
import aiohttp
import ccxt
import feedparser
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

# --- НАСТРОЙКИ ---
OPENROUTER_KEY = "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"
ai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

async def handle(request): return web.Response(text="Jarvis AI: Online")

# --- МОЗГ ДЖАРВИСА (ИИ АНАЛИЗ) ---
async def jarvis_analyze(context):
    try:
        response = await ai_client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[
                {"role": "system", "content": "Ты - Джарвис, высокоинтеллектуальный ИИ. Твоя задача: анализировать новости и кратко (2-3 предложения) объяснять их влияние на крипторынок. Стиль: уверенный, лаконичный, британский акцент."},
                {"role": "user", "content": f"Сэр, проанализируйте это: {context}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Сэр, мои аналитические цепи временно недоступны. Ошибка: {e}"

# --- СБОР ДАННЫХ ---
async def get_data():
    exchange = ccxt.binance()
    try:
        btc = exchange.fetch_ticker('BTC/USDT')['last']
        feed = feedparser.parse("https://www.investing.com/rss/news_285.rss")
        news = feed.entries[0].title if feed.entries else "Тишина в эфире"
        return btc, news
    except: return "???", "Ошибка связи"

async def main():
    # Запуск веб-сервера для Koyeb
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8000).start()

    bot = Bot(token=BOT_TOKEN)
    
    # ФОРМИРОВАНИЕ ИНТЕЛЛЕКТУАЛЬНОГО ОТЧЕТА
    btc_price, top_news = await get_data()
    # Джарвис анализирует ситуацию в Венесуэле и новости
    context = f"BTC ${btc_price}. Главная новость: {top_news}. Учитывай также захват Мадуро в Венесуэле США."
    analysis = await jarvis_analyze(context)

    report = (
        f"🤖 **СИСТЕМНЫЙ ДОКЛАД ДЖАРВИСА**\n\n"
        f"💰 **BTC:** `${btc_price}`\n"
        f"🗞️ **TOP NEWS:** {top_news}\n\n"
        f"🧠 **АНАЛИЗ:**\n{analysis}\n\n"
        f"🛡️ *Все системы переведены в боевой режим.*"
    )
    
    await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")

    dp = Dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
