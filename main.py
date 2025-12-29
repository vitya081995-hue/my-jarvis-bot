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
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-аналитик. Сейчас {curr_time}. Отвечай кратко, едко и по делу. {prompt}"}]
        )
        return res if res and "http" not in res else None
    except: return None

async def main_loop():
    global posted_links
    # Прямой агрегатор всех алертов Whale Alert
    WHALE_RSS = "https://www.cryptocontrol.io/en/newsfeed/rss/binance-whale-alert" 
    tz = pytz.timezone('Europe/Warsaw')

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(tz)
            today = now.strftime("%Y-%m-%d")

            # 1. Утренний брифинг (8:00)
            if now.hour == 8 and now.minute <= 10 and get_last_report_date() != today:
                res = await get_ai_summary("Сделай краткий план на сегодня. Только уровни и цели.")
                if res:
                    await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                    open(REPORT_LOG, "w").write(today)

            # 2. Мониторинг ВСЕХ КРУПНЫХ ПЕРЕВОДОВ
            try:
                async with session.get(WHALE_RSS, timeout=15) as r:
                    feed = feedparser.parse(await r.read())
                
                # Проверяем последние 20 записей
                for entry in reversed(feed.entries[:20]):
                    if entry.link in posted_links: continue
                    
                    title_up = entry.title.upper()
                    # Ловим всё: переводы, сжигания, чеканку любых монет
                    if any(x in title_up for x in ["WHALE", "TRANSFERRED", "BURNED", "MINTED", "MILLION"]):
                        posted_links.add(entry.link)
                        json.dump(list(posted_links)[-400:], open(DB_FILE, "w"))
                        
                        t_ru = translator.translate(entry.title).strip()
                        # Джарвис анализирует движение кита
                        res = await get_ai_summary(f"Крупный перевод: {t_ru}. Что это значит? Дай краткий вердикт.")
                        
                        if res:
                            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔍 Читать в источнике", url=entry.link)]])
                            await bot.send_message(CHANNEL_ID, f"🐋 **WHALE ALERT**\n\n📌 {t_ru}\n\n💬 **Джарвис:** {res}", reply_markup=markup)
                        await asyncio.sleep(5) 
            except: pass

            await asyncio.sleep(60) # Проверка каждую минуту

async def main():
    asyncio.create_task(main_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
