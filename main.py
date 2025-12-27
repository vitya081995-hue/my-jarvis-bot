import asyncio
import aiohttp
import feedparser
import datetime
import pytz
import logging
import json
import os
import g4f
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from deep_translator import GoogleTranslator
from config import BOT_TOKEN, CHANNEL_ID

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
translator = GoogleTranslator(source='auto', target='ru')

DB_FILE = "posted_news.json"
posted_links = []
HEADERS = {'User-Agent': 'Mozilla/5.0'}

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            posted_links = json.load(f)
    except: posted_links = []

# --- ФУНКЦИИ АНАЛИТИКИ ---
async def get_ai_summary(prompt):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}]
        )
        return response
    except: return "Сэр, связь с ИИ временно прервана, но я слежу за графиками."

# --- ОСНОВНОЙ ЦИКЛ ---
async def main_loop():
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    
    last_morning_report = None
    last_evening_report = None
    warsaw_tz = pytz.timezone('Europe/Warsaw')

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # 1. УТРЕННИЙ БРИФИНГ (08:00 по Варшаве)
            if now.hour == 8 and now.minute == 0 and last_morning_report != now.day:
                summary = await get_ai_summary("Напиши краткий план на крипто-день. Что ждать от рынка сегодня? Будь дерзким.")
                msg = f"☕️ **УТРЕННИЙ БРИФИНГ (ВАРШАВА 08:00)**\n\n{summary}\n\n🤖 *Джарвис на связи. Удачной охоты!*"
                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                last_morning_report = now.day

            # 2. ВЕЧЕРНИЙ ИТОГ И ПРОГНОЗ (20:00 по Варшаве)
            if now.hour == 20 and now.minute == 0 and last_evening_report != now.day:
                forecast = await get_ai_summary("Подведи итог дня в крипте. Что произошло важного и какой прогноз на завтра?")
                msg = f"🌙 **ВЕЧЕРНИЙ ОТЧЕТ (ВАРШАВА 20:00)**\n\n{forecast}\n\n📈 **ПРОГНОЗ:** Будьте осторожны, сэр."
                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                last_evening_report = now.day

            # --- ОБЫЧНЫЙ МОНИТОРИНГ НОВОСТЕЙ ---
            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    
                    for entry in feed.entries[:2]:
                        link = entry.link
                        if link in posted_links: continue
                        
                        title_ru = translator.translate(entry.title).strip()
                        is_whale = any(x in entry.title.lower() for x in ["whale", "million", "billion"])
                        
                        analysis = await get_ai_summary(f"Новость: {title_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in analysis.upper() else "🔴 НЕГАТИВ"
                        joke = analysis.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        header = "🚨 КИТОВЫЙ РАДАР" if is_whale else src["h"]
                        
                        buttons = [InlineKeyboardButton(text="📖 Источник", url=link)]
                        markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
                        
                        post = f"{header}\n\n{sentiment}\n\n📌 {title_ru}\n\n💬 *Джарвис:* {joke}"
                        await bot.send_message(CHANNEL_ID, post, parse_mode="Markdown", reply_markup=markup)
                        
                        posted_links.append(link)
                        with open(DB_FILE, "w", encoding="utf-8") as f:
                            json.dump(posted_links[-100:], f)
                        await asyncio.sleep(60)
                except: pass
            
            await asyncio.sleep(30) # Проверка каждую полминуты

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
