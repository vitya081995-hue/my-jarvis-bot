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
import random
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

# --- ФУНКЦИИ ИИ ---
async def get_ai_summary(prompt):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-гуру. {prompt}"}]
        )
        return response
    except: return "Сэр, ИИ временно вне зоны доступа. Видимо, опять сжигают токены."

# --- ОБРАБОТЧИК ГРУППЫ (Чтобы не молчал) ---
@dp.message()
async def group_moderator(message: types.Message):
    if not message.text: return
    text_lower = message.text.lower()
    
    # Анти-спам
    BAD_WORDS = ["хуй", "пизд", "ебан", "сука", "бля", "лох", "скам"]
    URL_PATTERN = r"(https?://\S+|t\.me/\S+|@\w+)"
    if (re.search(URL_PATTERN, text_lower) or any(w in text_lower for w in BAD_WORDS)) and message.from_user.id != (await bot.get_me()).id:
        try: await message.delete(); return
        except: pass

    # Ответ на "Джарвис" (любой регистр) или Reply
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
    
    if "джарвис" in text_lower or is_reply_to_bot:
        try:
            res = await get_ai_summary(f"Ответь дерзко и по делу на: '{message.text}'")
            await message.reply(res)
        except: pass

# --- ЦИКЛ МОНИТОРИНГА ---
async def main_loop():
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    last_morning, last_evening = None, None
    last_thought_time = datetime.datetime.now(warsaw_tz)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # 1. Мысли вслух (раз в 4-6 часов)
            if (now - last_thought_time).total_seconds() > 14400:
                if random.random() < 0.4:
                    thought = await get_ai_summary("Напиши одну короткую и очень едкую мысль о текущем рынке или трейдерах. Без приветствий.")
                    await bot.send_message(CHANNEL_ID, f"🤖 **Мысли вслух:**\n\n{thought}")
                    last_thought_time = now

            # 2. Брифинги
            if now.hour == 8 and now.minute == 0 and last_morning != now.day:
                res = await get_ai_summary("План на крипто-день (08:00). Что ждать от рынка сегодня?")
                await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day

            if now.hour == 20 and now.minute == 0 and last_evening != now.day:
                res = await get_ai_summary("Итоги дня и прогноз на завтра (20:00).")
                await bot.send_message(CHANNEL_ID, f"🌙 **ВЕЧЕРНИЙ ОТЧЕТ**\n\n{res}")
                last_evening = now.day

            # 3. Новости
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
                        is_whale = any(x in entry.title.lower() for x in ["whale", "million", "billion"])
                        
                        res = await get_ai_summary(f"Новость: {title_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        h = "🚨 КИТОВЫЙ РАДАР" if is_whale else src["h"]
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        
                        await bot.send_message(CHANNEL_ID, f"{h}\n\n{sentiment}\n\n📌 {title_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(120)
                except: pass
            await asyncio.sleep(600)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
