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
posted_links = set() # Используем set для мгновенного поиска

# Загрузка базы
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            posted_links = set(json.load(f))
    except: posted_links = set()

async def get_ai_summary(prompt):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}]
        )
        return response
    except: return "Сэр, ИИ временно занят анализом черных дыр. Но новость важная!"

async def main_loop():
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    last_morning = None
    last_evening = None

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # --- БРИФИНГИ ПО РАСПИСАНИЮ ---
            if now.hour == 8 and now.minute == 0 and last_morning != now.day:
                text = await get_ai_summary("Напиши план на крипто-день (Варшава 08:00). Будь дерзким.")
                await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{text}")
                last_morning = now.day

            if now.hour == 20 and now.minute == 0 and last_evening != now.day:
                text = await get_ai_summary("Итоги дня в крипте и краткий прогноз на завтра. 20:00.")
                await bot.send_message(CHANNEL_ID, f"🌙 **ВЕЧЕРНИЙ ОТЧЕТ**\n\n{text}")
                last_evening = now.day

            # --- МОНИТОРИНГ НОВОСТЕЙ ---
            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    
                    for entry in feed.entries[:3]:
                        if entry.link in posted_links: continue
                        
                        # МГНОВЕННО БЛОКИРУЕМ ПОВТОР
                        posted_links.add(entry.link)
                        with open(DB_FILE, "w", encoding="utf-8") as f:
                            json.dump(list(posted_links)[-100:], f)
                        
                        title_ru = translator.translate(entry.title).strip()
                        is_whale = any(x in entry.title.lower() for x in ["whale", "million", "billion"])
                        
                        res = await get_ai_summary(f"Новость: {title_ru}. Напиши 1 злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        header = "🚨 КИТОВЫЙ РАДАР" if is_whale else src["h"]
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        
                        await bot.send_message(CHANNEL_ID, f"{header}\n\n{sentiment}\n\n📌 {title_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(120) # Пауза 2 минуты между постами, чтобы не спамить
                except: pass
            
            await asyncio.sleep(600) # Проверка раз в 10 минут

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
