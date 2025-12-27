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

# Заголовки, чтобы сайты (особенно ForexFactory) не блокировали бота
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            posted_links = json.load(f)
    except:
        posted_links = []

@dp.message()
async def group_moderator(message: types.Message):
    if not message.text: return
    text_lower = message.text.lower()
    BAD_WORDS = ["хуй", "пизд", "ебан", "сука", "бля", "лох", "скам"]
    URL_PATTERN = r"(https?://\S+|t\.me/\S+|@\w+)"
    
    is_spam = re.search(URL_PATTERN, text_lower) or any(word in text_lower for word in BAD_WORDS)
    if is_spam and message.from_user.id != (await bot.get_me()).id:
        try:
            await message.delete()
            return
        except: pass

    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    if "джарвис" in text_lower or is_reply:
        try:
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.gpt_4,
                messages=[{"role": "user", "content": f"Ты Джарвис, ИИ-ассистент. Ответь кратко и по делу: '{message.text}'"}],
            )
            await message.reply(response)
        except: pass

async def send_post(title, sentiment, joke, link, header):
    try:
        chat_info = await bot.get_chat(CHANNEL_ID)
        linked_id = chat_info.linked_chat_id
        
        buttons = [InlineKeyboardButton(text="📖 Источник", url=link)]
        if linked_id:
            buttons.append(InlineKeyboardButton(text="💬 Чат", url=f"https://t.me/c/{str(linked_id)[4:]}/1"))
            
        markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
        msg = f"{header}\n\n{sentiment}\n\n📌 {title}\n\n💬 *Джарвис:* {joke}"
        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка публикации: {e}")

async def promo_post():
    promo_text = "🤖 *Сэр, напоминаю:*\n\nРынок не ждет. Заходите в обсуждение, пока иксы не улетели без вас!"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Вступить в J.A.R.V.I.S.", url=f"https://t.me/criptojarvis20")]
    ])
    await bot.send_message(CHANNEL_ID, promo_text, parse_mode="Markdown", reply_markup=markup)

async def main_loop():
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    
    last_promo = datetime.datetime.now()

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            if (datetime.datetime.now() - last_promo).total_seconds() > 43200:
                await promo_post()
                last_promo = datetime.datetime.now()

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        content = await r.read()
                        feed = feedparser.parse(content)
                    
                    for entry in feed.entries[:3]:
                        link = entry.link if hasattr(entry, 'link') else src["url"]
                        if link in posted_links: continue
                        
                        title_ru = translator.translate(entry.title).strip()
                        
                        # Проверка на китов и макро
                        is_whale = any(x in entry.title.lower() for x in ["whale", "million", "billion", "transferred"])
                        is_macro = "📊 МАКРО" in src["h"]
                        
                        prompt = f"Новость: {title_ru}. Напиши 1 короткую злую шутку и в конце напиши слово ПОЗИТИВ или НЕГАТИВ."
                        if is_macro:
                            prompt = f"Экономическое событие: {title_ru}. Объясни кратко, почему это важно для крипты и напиши ПОЗИТИВ/НЕГАТИВ."

                        analysis = await g4f.ChatCompletion.create_async(
                            model=g4f.models.gpt_4,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in analysis.upper() else "🔴 НЕГАТИВ"
                        joke = analysis.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        header = src["h"]
                        if is_whale: header = "🚨 КИТОВЫЙ РАДАР"

                        await send_post(title_ru, sentiment, joke, link, header)
                        
                        posted_links.append(link)
                        with open(DB_FILE, "w", encoding="utf-8") as f:
                            json.dump(posted_links[-100:], f)
                        await asyncio.sleep(60)
                except Exception as e:
                    logging.error(f"Ошибка в источнике {src['url']}: {e}")
                    await asyncio.sleep(20)
            await asyncio.sleep(600) # Проверка раз в 10 минут

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
