import asyncio, aiohttp, feedparser, datetime, pytz, json, os, g4f, re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from deep_translator import GoogleTranslator
from config import BOT_TOKEN, CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
translator = GoogleTranslator(source='auto', target='ru')
DB_FILE = "posted_news.json"

def load_posted():
    if os.path.exists(DB_FILE):
        try: return set(json.load(open(DB_FILE, "r")))
        except: pass
    return set()

def save_posted(links):
    json.dump(list(links)[-400:], open(DB_FILE, "w"))

posted_links = load_posted()

async def get_btc_price():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd") as r:
                return (await r.json())['bitcoin']['usd']
    except: return "88500"

async def get_ai_summary(prompt):
    curr_date = "28 декабря 2025 года"
    try:
        res = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный профи. Сегодня {curr_date}. {prompt}"}]
        )
        if any(x in res for x in ["http", "html", "请求", "limit"]): return None
        return res
    except: return None

async def main_loop():
    global posted_links
    # Оставили только самое важное
    SOURCES = [
        {"url": "https://blockchain.news/RSS/", "h": "🐋 WHALE ALERT"},
        {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}
    ]
    tz = pytz.timezone('Europe/Warsaw')
    last_morning, last_evening = None, None

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(tz)
            price = await get_btc_price()

            # 1. БРИФИНГИ
            if now.hour >= 8 and last_morning != now.day:
                res = await get_ai_summary(f"BTC: ${price}. Дай дерзкий план на день.")
                if res: await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day
                save_posted(posted_links)

            if now.hour >= 20 and last_evening != now.day:
                res = await get_ai_summary(f"BTC: ${price}. Итоги дня.")
                if res: await bot.send_message(CHANNEL_ID, f"🌙 **ВЕЧЕРНИЙ ОТЧЕТ**\n\n{res}")
                last_evening = now.day

            # 2. КИТЫ И МАКРО
            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=20) as r:
                        feed = feedparser.parse(await r.read())
                    for entry in feed.entries[:10]:
                        if entry.link in posted_links: continue
                        
                        # Фильтр на Крупные суммы (для Whale Alert)
                        is_important = any(x in entry.title.upper() for x in ["MILLION", "BILLION", "INTEREST RATE", "GDP", "CPI"])
                        if not is_important: continue

                        posted_links.add(entry.link)
                        save_posted(posted_links)
                        
                        t_ru = translator.translate(entry.title).strip()
                        res = await get_ai_summary(f"Новость: {t_ru}. Напиши злую шутку и вердикт ПОЗИТИВ/НЕГАТИВ.")
                        if not res: continue

                        sentiment = "🟢 ПОЗИТИВ" if "ПОЗИТИВ" in res.upper() else "🔴 НЕГАТИВ"
                        joke = res.replace("ПОЗИТИВ", "").replace("НЕГАТИВ", "").strip()
                        
                        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                        await bot.send_message(CHANNEL_ID, f"{src['h']}\n\n{sentiment}\n\n📌 {t_ru}\n\n💬 *Джарвис:* {joke}", parse_mode="Markdown", reply_markup=markup)
                        await asyncio.sleep(60)
                except: pass
            await asyncio.sleep(1200)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
