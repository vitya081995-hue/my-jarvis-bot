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

DB_FILE = "/workspace/posted_news.json" # Путь для Koyeb
posted_links = []

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            posted_links = json.load(f)
    except: posted_links = []

async def get_ai_summary(prompt):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}]
        )
        return response
    except: return "Сэр, ИИ анализирует данные. Новость заслуживает внимания!"

async def send_post(title, sentiment, joke, link, header):
    try:
        # Пытаемся найти привязанный чат для кнопки комментариев
        chat = await bot.get_chat(CHANNEL_ID)
        buttons = [InlineKeyboardButton(text="📖 Источник", url=link)]
        
        if chat.linked_chat_id:
            # Кнопка, которая ведет сразу в обсуждение
            buttons.append(InlineKeyboardButton(text="💬 Обсудить", url=f"https://t.me/c/{str(chat.linked_chat_id)[4:]}/1"))
            
        markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
        msg = f"{header}\n\n{sentiment}\n\n📌 {title}\n\n💬 *Джарвис:* {joke}"
        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

async def main_loop():
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    last_morning, last_evening = None, None

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # Отчеты
            if now.hour == 8 and now.minute == 0 and last_morning != now.day:
                res = await get_ai_summary("План на крипто-день. Коротко и дерзко.")
                await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day

            if now.hour == 20 and now.minute == 0 and last_evening != now.day:
                res = await get_ai_summary("Итоги дня и прогноз на завтра.")
                await bot.send_message(CHANNEL_ID, f"🌙 **ВЕЧЕРНИЙ ОТЧЕТ**\n\n{res}")
                last_evening = now.day

            # Новости
            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    for entry in feed.entries[:2]:
                        if entry.link in posted_links: continue
                        
                        posted_links.append(entry.link)
                        with open(DB_FILE, "w", encoding="utf-8") as f:
                            json.dump(posted_links[-100:], f)
                        
                        title_ru = translator.translate(entry.title).strip()
                        res = await get_ai_summary(f"Новость: {title_ru}. Напиши шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        await send_post(title_ru, sentiment, joke, entry.link, src["h"])
                        await asyncio.sleep(120)
                except: pass
            await asyncio.sleep(600)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
