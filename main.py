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

# Путь к файлу в директории, которую Koyeb меньше трогает при рестартах
DB_FILE = os.path.join(os.getcwd(), "posted_news.json")

def load_posted_links():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logging.error(f"Ошибка загрузки БД: {e}")
    return set()

def save_posted_links(links):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(links)[-200:], f) # Храним последние 200 ссылок
    except Exception as e:
        logging.error(f"Ошибка сохранения БД: {e}")

posted_links = load_posted_links()

async def get_ai_summary(prompt):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-гуру. {prompt}"}]
        )
        return response
    except: return "Сэр, ИИ временно ушел в офлайн. Видимо, цена газа слишком высока."

@dp.message()
async def group_moderator(message: types.Message):
    if not message.text: return
    text_lower = message.text.lower()
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
    
    if "джарвис" in text_lower or is_reply_to_bot:
        res = await get_ai_summary(f"Ответь дерзко на: '{message.text}'")
        await message.reply(res)

async def main_loop():
    global posted_links
    SOURCES = [
        {"url": "https://www.coinbase.com/blog/rss", "h": "📰 COINBASE"},
        {"url": "https://cointelegraph.com/rss", "h": "📰 COINTELEGAPH"},
        {"url": "https://cryptopotato.com/feed", "h": "🚨 КИТОВЫЙ РАДАР"}, 
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    last_thought = datetime.datetime.now(warsaw_tz)

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(warsaw_tz)
            
            # Мысли вслух
            if (now - last_thought).total_seconds() > 14400 and random.random() < 0.4:
                thought = await get_ai_summary("Напиши одну короткую едкую мысль о рынке.")
                await bot.send_message(CHANNEL_ID, f"🤖 **Мысли вслух:**\n\n{thought}")
                last_thought = now

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=30) as r:
                        feed = feedparser.parse(await r.read())
                    
                    for entry in feed.entries[:5]: # Проверяем чуть больше записей
                        if entry.link in posted_links:
                            continue
                        
                        # Блокируем СРАЗУ
                        posted_links.add(entry.link)
                        save_posted_links(posted_links)
                        
                        title_ru = translator.translate(entry.title).strip()
                        is_whale = any(x in entry.title.lower() for x in ["whale", "million", "billion"])
                        
                        res = await get_ai_summary(f"Новость: {title_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        h = "🚨 КИТОВЫЙ РАДАР" if is_whale else src["h"]
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        
                        await bot.send_message(CHANNEL_ID, f"{h}\n\n{sentiment}\n\n📌 {title_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(30) # Небольшая пауза между разными новостями
                except Exception as e:
                    logging.error(f"Ошибка источника {src['url']}: {e}")
            
            await asyncio.sleep(1200) # Проверка раз в 20 минут - этого достаточно

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
