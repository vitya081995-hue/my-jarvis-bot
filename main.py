import asyncio, aiohttp, feedparser, datetime, pytz, json, os, g4f
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from deep_translator import GoogleTranslator
from config import BOT_TOKEN, CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
translator = GoogleTranslator(source='auto', target='ru')
DB_FILE = "posted_news.json"
REPORT_LOG = "last_report.txt"

def load_posted():
    if os.path.exists(DB_FILE):
        try: return set(json.load(open(DB_FILE, "r")))
        except: pass
    return set()

def get_last_report_date():
    return open(REPORT_LOG, "r").read().strip() if os.path.exists(REPORT_LOG) else ""

posted_links = load_posted()

async def get_ai_summary(prompt):
    tz = pytz.timezone('Europe/Warsaw')
    curr_time = datetime.datetime.now(tz).strftime("%H:%M")
    try:
        res = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-аналитик. Сейчас {curr_time}. Отвечай кратко и по делу. {prompt}"}]
        )
        return res if res and "http" not in res else None
    except: return None

async def main_loop():
    global posted_links
    # Прямая ссылка на RSS ленту Whale Alert через агрегатор
    WHALE_RSS = "https://www.cryptocontrol.io/en/newsfeed/rss/binance-whale-alert" # Альтернативный поток
    tz = pytz.timezone('Europe/Warsaw')

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(tz)
            today = now.strftime("%Y-%m-%d")

            # 1. Утренний брифинг (8:00)
            if now.hour == 8 and now.minute <= 15 and get_last_report_date() != today:
                res = await get_ai_summary("Сделай краткий и дерзкий торговый план на сегодня.")
                if res:
                    await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                    open(REPORT_LOG, "w").write(today)

            # 2. Мониторинг китов (каждые 60 секунд)
            try:
                async with session.get(WHALE_RSS, timeout=15) as r:
                    feed = feedparser.parse(await r.read())
                
                # Идем по записям в обратном порядке, чтобы постить старые сначала
                for entry in reversed(feed.entries[:15]):
                    if entry.link in posted_links: continue
                    
                    # Фильтр только по важным движениям (USDC, USDT, PYUSD, BTC, ETH)
                    text_to_check = entry.title.upper()
                    if any(x in text_to_check for x in ["WHALE", "TRANSFERRED", "BURNED", "MILLION", "PYUSD"]):
                        posted_links.add(entry.link)
                        json.dump(list(posted_links)[-300:], open(DB_FILE, "w"))
                        
                        t_ru = translator.translate(entry.title).strip()
                        # Джарвис анализирует конкретный перевод
                        res = await get_ai_summary(f"Кит перевел: {t_ru}. Что это значит для рынка? Дай краткий вердикт.")
                        
                        if res:
                            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔍 Детали транзакции", url=entry.link)]])
                            await bot.send_message(CHANNEL_ID, f"🐋 **WHALE ALERT**\n\n📌 {t_ru}\n\n💬 **Джарвис:** {res}", reply_markup=markup)
                        await asyncio.sleep(10) # Чтобы не спамить в одну секунду
            except: pass

            await asyncio.sleep(60)

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
