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
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except: pass
    return set()

def save_posted_links(links):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(links)[-400:], f) # Увеличили память до 400 ссылок
    except: pass

posted_links = load_posted_links()
# Дополнительная память для заголовков, чтобы не частить похожими новостями
posted_titles = []

async def get_btc_price():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd") as r:
                data = await r.json()
                return data['bitcoin']['usd']
    except: return "88500" # Заглушка на случай сбоя API

async def get_ai_summary(prompt):
    # Жесткая установка даты для ИИ
    current_date = "28 декабря 2025 года"
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-дворецкий. Сегодня {current_date}. Забудь всё, что было в начале 2025 года. Твоя аналитика только на текущий момент. {prompt}"}]
        )
        return response
    except: return "Сэр, мой нейроинтерфейс залагал. Но я всё еще слежу за вами."

@dp.message()
async def group_moderator(message: types.Message):
    if not message.text: return
    text_lower = message.text.lower()
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
    if "джарвис" in text_lower or is_reply_to_bot:
        price = await get_btc_price()
        res = await get_ai_summary(f"Цена деда: ${price}. Ответь на: '{message.text}'")
        await message.reply(res)

async def main_loop():
    global posted_links, posted_titles
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
            
            # Брифинги
            if now.hour >= 8 and last_morning != now.day:
                price = await get_btc_price()
                res = await get_ai_summary(f"Биткоин ${price}. Краткий прогноз на день. Без старой инфы.")
                await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day
                save_posted_links(posted_links)

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    
                    for entry in feed.entries[:15]:
                        # 1. ПРОВЕРКА ДАТЫ (Игнорируем старье старше 24ч)
                        pub = entry.get('published_parsed') or entry.get('updated_parsed')
                        if pub:
                            p_dt = datetime.datetime(*pub[:6]).replace(tzinfo=pytz.UTC)
                            if (datetime.datetime.now(pytz.UTC) - p_dt).total_seconds() > 86400:
                                continue

                        # 2. ПРОВЕРКА ДУБЛЕЙ (Ссылка + Заголовок)
                        if entry.link in posted_links: continue
                        
                        title_clean = re.sub(r'[^а-яА-Яa-zA-Z]', '', entry.title[:30])
                        if title_clean in posted_titles: continue

                        # 3. ФИЛЬТР "ПРОШЛОГО"
                        if any(year in entry.title for year in ["2023", "2024", "January 2025"]):
                            continue

                        posted_links.add(entry.link)
                        posted_titles.append(title_clean)
                        if len(posted_titles) > 50: posted_titles.pop(0)
                        save_posted_links(posted_links)
                        
                        title_ru = translator.translate(entry.title).strip()
                        is_whale = any(x in entry.title.upper() for x in ["MILLION", "BILLION", "WHALE", "TRANSFER"])
                        
                        res = await get_ai_summary(f"Новость: {title_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        h = "🐋 WHALE ALERT" if is_whale else src["h"]
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        await bot.send_message(CHANNEL_ID, f"{h}\n\n{sentiment}\n\n📌 {title_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(60)
                except: pass
            await asyncio.sleep(1200)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
