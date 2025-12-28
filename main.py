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

DB_FILE = os.path.join(os.getcwd(), "posted_news.json")

def load_posted_links():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except: pass
    return set()

def save_posted_links(links):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(links)[-400:], f)
    except: pass

posted_links = load_posted_links()

async def get_btc_price():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd") as r:
                return (await r.json())['bitcoin']['usd']
    except: return "88500"

async def get_ai_summary(prompt):
    # Указываем декабрь 2025, чтобы он не бредил январем
    curr_date = "28 декабря 2025 года"
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис. Сегодня {curr_date}. Игнорируй прогнозы на начало 2025. {prompt}"}]
        )
        return response
    except: return "Сэр, система ИИ перегружена."

# --- ЗАЩИТА ОТ ЭХО И САМООТВЕТОВ ---
@dp.message()
async def group_moderator(message: types.Message):
    # Игнорируем, если пишет БОТ (включая самого себя)
    if message.from_user.is_bot:
        return
        
    if not message.text: return
    text_lower = message.text.lower()
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
    
    if "джарвис" in text_lower or is_reply_to_bot:
        p = await get_btc_price()
        res = await get_ai_summary(f"Цена деда: ${p}. Ответь на вопрос: '{message.text}'")
        await message.reply(res)

async def main_loop():
    global posted_links
    SOURCES = [
        {"url": "https://blockchain.news/RSS/", "h": "🚨 BIZ & WHALES"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}
    ]
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    last_morning, last_evening, last_thought = None, None, datetime.datetime.now(warsaw_tz)

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # Утренний брифинг (теперь точно по времени)
            if now.hour >= 8 and last_morning != now.day:
                p = await get_btc_price()
                res = await get_ai_summary(f"Цена BTC: ${p}. Дай сводку на сегодня.")
                await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day
                save_posted_links(posted_links)

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    
                    for entry in feed.entries[:15]:
                        # Фильтр по дате (не старше 24ч)
                        pub = entry.get('published_parsed')
                        if pub:
                            p_dt = datetime.datetime(*pub[:6]).replace(tzinfo=pytz.UTC)
                            if (datetime.datetime.now(pytz.UTC) - p_dt).total_seconds() > 86400:
                                continue

                        if entry.link in posted_links: continue
                        
                        # Фильтр старых годов
                        if any(y in entry.title for y in ["2024", "January 2025"]):
                            continue

                        posted_links.add(entry.link)
                        save_posted_links(posted_links)
                        
                        t_ru = translator.translate(entry.title).strip()
                        is_whale = any(x in entry.title.upper() for x in ["MILLION", "BILLION", "WHALE"])
                        
                        res = await get_ai_summary(f"Новость: {t_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        h = "🐋 WHALE ALERT" if is_whale else src["h"]
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        
                        await bot.send_message(CHANNEL_ID, f"{h}\n\n{sentiment}\n\n📌 {t_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(60)
                except: pass
            await asyncio.sleep(1200)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
