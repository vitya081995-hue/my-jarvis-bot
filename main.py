import asyncio, aiohttp, feedparser, datetime, pytz, json, os, g4f, re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from deep_translator import GoogleTranslator
from config import BOT_TOKEN, CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
translator = GoogleTranslator(source='auto', target='ru')
DB_FILE = "posted_news.json"
REPORT_LOG = "last_report.txt"

# Глобальный флаг, чтобы не пустить вторую копию отчета
is_reporting = False

def load_posted():
    if os.path.exists(DB_FILE):
        try: return set(json.load(open(DB_FILE, "r")))
        except: pass
    return set()

def get_last_report_date():
    if os.path.exists(REPORT_LOG):
        try: return open(REPORT_LOG, "r").read().strip()
        except: pass
    return ""

def set_last_report_date(date_str):
    with open(REPORT_LOG, "w") as f:
        f.write(date_str)

posted_links = load_posted()

async def get_ticker_data(symbol):
    try:
        async with aiohttp.ClientSession() as s:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=20"
            async with s.get(url) as r:
                data = await r.json()
                closes = [float(x[4]) for x in data]
                curr_p = closes[-1]
                gains, losses = [], []
                for i in range(1, 15):
                    diff = closes[-i] - closes[-i-1]; gains.append(max(diff, 0)); losses.append(max(-diff, 0))
                avg_gain = sum(gains)/14; avg_loss = sum(losses)/14
                rs = avg_gain/avg_loss if avg_loss != 0 else 100
                rsi = 100 - (100/(1+rs))
                return {"price": curr_p, "rsi": rsi}
    except: return None

async def get_ai_summary(prompt):
    # ТЕПЕРЬ ДАТА БЕРЕТСЯ АВТОМАТИЧЕСКИ
    now_utc = datetime.datetime.now(pytz.timezone('Europe/Warsaw'))
    curr_date = now_utc.strftime("%d %B %Y года")
    try:
        res = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-аналитик. Сегодня {curr_date}. Твоя задача: только трейдинг и макро. Никакого кардио и завтраков. {prompt}"}]
        )
        if not res or any(x in res for x in ["http", "请求", "limit", "html"]): return None
        return res
    except: return None

@dp.message()
async def commands_handler(message: types.Message):
    if message.from_user.is_bot: return
    if message.text and message.text.lower() == "!анализ":
        btc = await get_ticker_data("BTCUSDT")
        if not btc: return
        res = await get_ai_summary(f"Цена BTC: ${btc['price']:.0f}, RSI: {btc['rsi']:.1f}. Дай краткий прогноз на 30 мин.")
        if res: await message.reply(f"🎯 **ТЕХАНАЛИЗ**\n\n💬 **Джарвис:** {res}")

async def main_loop():
    global posted_links, is_reporting
    SOURCES = [{"url": "https://blockchain.news/RSS/", "h": "🐋 WHALE ALERT"}]
    tz = pytz.timezone('Europe/Warsaw')

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(tz)
            today_str = now.strftime("%Y-%m-%d")
            last_rep = get_last_report_date()

            # ЖЕСТКАЯ ПРОВЕРКА: Если время 8:00+, отчета еще не было и мы прямо сейчас его не пишем
            if now.hour >= 8 and last_rep != today_str and not is_reporting:
                is_reporting = True # Ставим блок
                btc = await get_ticker_data("BTCUSDT")
                # Уточняем в промпте, что завтрак нам не интересен
                res = await get_ai_summary(f"BTC: ${btc['price'] if btc else '88000'}. Сделай ОДИН четкий торговый план на сегодня. Только графики и уровни.")
                if res:
                    await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                    set_last_report_date(today_str)
                is_reporting = False # Снимаем блок

            # Мониторинг новостей остается
            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=20) as r:
                        feed = feedparser.parse(await r.read())
                    for entry in feed.entries[:5]:
                        if entry.link in posted_links: continue
                        if not any(x in entry.title.upper() for x in ["MILLION", "BILLION", "WHALE"]): continue
                        posted_links.add(entry.link)
                        json.dump(list(posted_links)[-500:], open(DB_FILE, "w"))
                        t_ru = translator.translate(entry.title).strip()
                        res = await get_ai_summary(f"Новость: {t_ru}. Дай злой вердикт.")
                        if res:
                            await bot.send_message(CHANNEL_ID, f"{src['h']}\n\n📌 {t_ru}\n\n💬 {res}")
                        await asyncio.sleep(30)
                except: pass
            await asyncio.sleep(600)

async def main():
    asyncio.create_task(main_loop()); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
