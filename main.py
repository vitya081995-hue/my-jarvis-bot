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
            json.dump(list(links)[-300:], f)
    except: pass

posted_links = load_posted_links()

# --- НОВАЯ ФУНКЦИЯ: ПОЛУЧЕНИЕ РЕАЛЬНОЙ ЦЕНЫ ---
async def get_btc_price():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd") as r:
                data = await r.json()
                return data['bitcoin']['usd']
    except: return "неизвестно сколько (но явно не 30к)"

async def get_ai_summary(prompt):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-гуру на дворе декабрь 2025. {prompt}"}]
        )
        return response
    except: return "Сэр, ИИ временно вне связи."

@dp.message()
async def group_moderator(message: types.Message):
    if not message.text: return
    text_lower = message.text.lower()
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
    if "джарвис" in text_lower or is_reply_to_bot:
        price = await get_btc_price()
        res = await get_ai_summary(f"Биткоин сейчас стоит ${price}. Ответь дерзко на: '{message.text}'")
        await message.reply(res)

async def main_loop():
    global posted_links
    SOURCES = [
        {"url": "https://blockchain.news/RSS/", "h": "🚨 BIZ & WHALES"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    last_morning, last_evening = None, None
    last_thought = datetime.datetime.now(warsaw_tz)

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # --- БРИФИНГИ С РЕАЛЬНОЙ ЦЕНОЙ ---
            if now.hour >= 8 and last_morning != now.day:
                price = await get_btc_price()
                res = await get_ai_summary(f"Биткоин сейчас ${price}. Дай краткий и дерзкий прогноз на этот крипто-день, оперируя этой ценой.")
                await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day
                save_posted_links(posted_links)

            if now.hour >= 20 and last_evening != now.day:
                price = await get_btc_price()
                res = await get_ai_summary(f"Биткоин сейчас ${price}. Итоги дня и прогноз на завтра.")
                await bot.send_message(CHANNEL_ID, f"🌙 **ВЕЧЕРНИЙ ОТЧЕТ**\n\n{res}")
                last_evening = now.day
                save_posted_links(posted_links)

            # --- (Остальной код новостей и мыслей без изменений) ---
            if (now - last_thought).total_seconds() > 14400 and random.random() < 0.4:
                price = await get_btc_price()
                thought = await get_ai_summary(f"Биткоин по ${price}. Напиши одну едкую мысль о рынке.")
                await bot.send_message(CHANNEL_ID, f"🤖 **Мысли вслух:**\n\n{thought}")
                last_thought = now

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    for entry in feed.entries[:20]: 
                        if entry.link in posted_links: continue
                        posted_links.add(entry.link)
                        save_posted_links(posted_links)
                        title_ru = translator.translate(entry.title).strip()
                        is_whale = any(x in entry.title.upper() for x in ["MILLION", "BILLION", "WHALE", "TRANSFER"])
                        res = await get_ai_summary(f"Новость: {title_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        header = "🐋 WHALE ALERT" if is_whale else src["h"]
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        await bot.send_message(CHANNEL_ID, f"{header}\n\n{sentiment}\n\n📌 {title_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(45)
                except: pass
            await asyncio.sleep(900)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
