import asyncio
import aiohttp
import ccxt
import feedparser
from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

# Ваш рабочий ключ OpenRouter
OPENROUTER_KEY = "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"
ai_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)

async def handle(request): return web.Response(text="Jarvis War Room: Online")

async def get_ai_analysis(price, news):
    try:
        response = await ai_client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[
                {"role": "system", "content": "Ты - Джарвис. Проанализируй влияние захвата Мадуро в Венесуэле и ударов США на крипторынок. Стиль: Тони Старк, кратко, экспертно."},
                {"role": "user", "content": f"Сэр, BTC сейчас {price}. Новость: {news}. Дайте прогноз."}
            ]
        )
        return response.choices[0].message.content
    except: return "Сэр, модули ИИ не отвечают, но я слежу за графиками."

async def main():
    # Веб-сервер для Koyeb
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8000).start()

    bot = Bot(token=BOT_TOKEN)
    exchange = ccxt.binance()
    
    # Сбор данных
    btc = exchange.fetch_ticker('BTC/USDT')['last']
    feed = feedparser.parse("https://www.investing.com/rss/news_285.rss")
    top_news = feed.entries[0].title if feed.entries else "Геополитический шок в Венесуэле."
    
    # ИИ Анализ
    analysis = await get_ai_analysis(btc, top_news)

    # Отправка доклада
    report = (
        f"🚨 **ЭКСТРЕННЫЙ АНАЛИЗ ДЖАРВИСА**\n\n"
        f"💰 **BTC:** `${btc}`\n\n"
        f"🧠 **ВЕРДИКТ ИИ:**\n{analysis}\n\n"
        f"🗞️ **ГЛАВНОЕ:** {top_news}\n\n"
        f"⚠️ *Системы в режиме боевого дежурства.*"
    )
    
    await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
    
    dp = Dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
