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
translator = GoogleTranslator(source='en', target='ru')

DB_FILE = "posted_news.json"
posted_links = []

# --- НАСТРОЙКИ АНТИ-СПАМА ---
BAD_WORDS = ["хуй", "пизд", "ебан", "сука", "бля", "лох", "скам"]
URL_PATTERN = r"(https?://\S+|t\.me/\S+|@\w+)"

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            posted_links = json.load(f)
    except:
        posted_links = []

# --- ОБРАБОТЧИК ДЛЯ ГРУППЫ (МОДЕРАЦИЯ + ОТВЕТЫ) ---
@dp.message()
async def group_moderator(message: types.Message):
    if not message.text: return
    text_lower = message.text.lower()
    
    # 1. Анти-спам
    is_spam = re.search(URL_PATTERN, text_lower) or any(word in text_lower for word in BAD_WORDS)
    if is_spam and message.from_user.id != (await bot.get_me()).id:
        try:
            await message.delete()
            return
        except: pass

    # 2. Интеллектуальный ответ
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    if "джарвис" in text_lower or is_reply:
        try:
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.gpt_4,
                messages=[{"role": "user", "content": f"Ты Джарвис. Ответь дерзко на: '{message.text}'"}],
            )
            await message.reply(response)
        except: pass

# --- ФУНКЦИЯ ПУБЛИКАЦИИ ---
async def send_post(title, sentiment, joke, link, header):
    try:
        chat_info = await bot.get_chat(CHANNEL_ID)
        linked_id = chat_info.linked_chat_id
        
        buttons = [InlineKeyboardButton(text="📖 Источник", url=link)]
        if linked_id:
            buttons.append(InlineKeyboardButton(text="💬 Ворваться в чат", url=f"https://t.me/c/{str(linked_id)[4:]}/1"))
            
        markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
        msg = f"{header}\n\n{sentiment}\n\n📌 {title}\n\n💬 *Джарвис:* {joke}"
        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка: {e}")

# --- ФУНКЦИЯ АВТО-РЕКЛАМЫ ---
async def promo_post():
    promo_text = "🤖 *Сэр, напоминаю:*\n\nПока вы просто читаете, кто-то в комментариях уже обсуждает, как зафиксировать иксы. Не будьте зрителем, заходите в наше логово!"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Вступить в J.A.R.V.I.S.", url=f"https://t.me/criptojarvis20")]
    ])
    await bot.send_message(CHANNEL_ID, promo_text, parse_mode="Markdown", reply_markup=markup)

# --- ОСНОВНОЙ ЦИКЛ ---
async def main_loop():
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    
    last_promo = datetime.datetime.now()

    async with aiohttp.ClientSession() as session:
        while True:
            # Раз в 12 часов выпускаем рекламу
            if (datetime.datetime.now() - last_promo).total_seconds() > 43200:
                await promo_post()
                last_promo = datetime.datetime.now()

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    
                    for entry in feed.entries[:3]:
                        if entry.link in posted_links: continue
                        
                        title_ru = translator.translate(entry.title).strip()
                        is_session = "session" in entry.title.lower() or "market open" in entry.title.lower()
                        
                        analysis = await g4f.ChatCompletion.create_async(
                            model=g4f.models.gpt_4,
                            messages=[{"role": "user", "content": f"Новость: {title_ru}. Напиши 1 злую шутку и ПОЗИТИВ/НЕГАТИВ."}]
                        )
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in analysis.upper() else "🔴 НЕГАТИВ"
                        joke = analysis.split('.')[-1]
                        
                        header = "🕒 СЕССИЯ" if is_session else src["h"]
                        await send_post(title_ru, sentiment, joke, entry.link, header)
                        
                        posted_links.append(entry.link)
                        with open(DB_FILE, "w", encoding="utf-8") as f:
                            json.dump(posted_links[-100:], f)
                        await asyncio.sleep(60)
                except: await asyncio.sleep(20)
            await asyncio.sleep(300)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())