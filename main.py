import asyncio
import ccxt.async_support as ccxt
import feedparser
from aiogram import Bot
from openai import AsyncOpenAI
from config import BOT_TOKEN, CHANNEL_ID  # из .env / config
import datetime
import pytz

# Ключи
OPENROUTER_KEY = "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"
ai_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)

UTC = pytz.utc
KIEV = pytz.timezone('Europe/Kiev')  # или 'Europe/Warsaw' для твоей зоны

async def get_prices():
    exchange = ccxt.binance()
    try:
        btc = (await exchange.fetch_ticker('BTC/USDT'))['last']
        eth = (await exchange.fetch_ticker('ETH/USDT'))['last']
        return btc, eth
    except Exception as e:
        print(f"Price fetch error: {e}")
        return 90600, 3090  # fallback на текущий уровень 10.01.2026

async def get_news():
    feed = feedparser.parse("https://cointelegraph.com/rss")
    news_items = [entry.title for entry in feed.entries[:4] if 'bitcoin' in entry.title.lower() or 'ethereum' in entry.title.lower() or 'crypto' in entry.title.lower()]
    return " | ".join(news_items) if news_items else "BTC & ETH hold steady amid ETF repositioning & macro flows."

async def get_ai_verdict(btc, eth, news, is_morning=True):
    try:
        period = "на сегодня (утренний взгляд)" if is_morning else "на ночь и завтра (итоги дня)"
        response = await ai_client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[
                {"role": "system", "content": """Ты — Джарвис, ИИ Тони Старка. Кратко, саркастично, экспертно. 
Фокус только на BTC и ETH. Учитывай: захват Мадуро (нефть/доллар/хедж), ETF flows (in/out), macro (Fed, bonds), геополитику. 
Дай вердикт: long/short/neutral + 3–7 дней цели + стопы для каждого."""},
                {"role": "user", "content": f"Сэр, BTC ${btc:,.0f}, ETH ${eth:,.0f}. Новости: {news}. Дай прогноз {period}."}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI error: {e}")
        return "Сэр, ИИ в лёгком шоке от рынка... но держим курс на 90k+ для BTC."

async def send_digest(is_morning=True):
    btc, eth = await get_prices()
    news = await get_news()
    analysis = await get_ai_verdict(btc, eth, news, is_morning)

    title = "🌅 **УТРЕННИЙ ДАЙДЖЕСТ ДЖАРВИСА**" if is_morning else "🌙 **ВЕЧЕРНИЙ ДАЙДЖЕСТ ДЖАРВИСА**"
    time_str = datetime.datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')

    report = (
        f"{title} — {time_str}\n\n"
        f"💰 **BTC:** `${btc:,.0f}`\n"
        f"🔵 **ETH:** `${eth:,.0f}`\n\n"
        f"🧠 **ВЕРДИКТ ИИ (Тони Старк mode):**\n{analysis}\n\n"
        f"🗞️ **Главные новости:** {news}\n\n"
        f"⚡ *Системы в боевом режиме. ETF flows, macro, Maduro — всё под контролем.*"
    )

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
    finally:
        await bot.session.close()

async def schedule_digests():
    while True:
        now_utc = datetime.datetime.now(UTC)
        now_hour = now_utc.hour

        # Утренний ~ 08:00 UTC
        if now_hour == 8 and now_utc.minute < 5:
            await send_digest(is_morning=True)
            print("Morning digest sent")

        # Вечерний ~ 20:00 UTC
        if now_hour == 20 and now_utc.minute < 5:
            await send_digest(is_morning=False)
            print("Evening digest sent")

        # Спим 5 минут и проверяем снова (экономим CPU)
        await asyncio.sleep(300)

async def main():
    # Опционально: веб-сервер для healthcheck на Koyeb
    # ... (оставь как было, если нужно)

    print("Jarvis War Room запущен. Ожидаю 08:00 и 20:00 UTC...")
    await schedule_digests()

if __name__ == "__main__":
    asyncio.run(main())
