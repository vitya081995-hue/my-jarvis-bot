import asyncio, aiohttp, feedparser, datetime, pytz, json, os, g4f, re, random
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

posted_links = load_posted()

async def get_ticker_data(symbol):
    try:
        async with aiohttp.ClientSession() as s:
            # Берем 20 свечей по 5 минут для расчета RSI и тренда
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=20"
            async with s.get(url) as r:
                data = await r.json()
                closes = [float(x[4]) for x in data]
                curr_p = closes[-1]
                
                # Простой расчет RSI
                gains, losses = [], []
                for i in range(1, 15):
                    diff = closes[-i] - closes[-i-1]
                    gains.append(max(diff, 0))
                    losses.append(max(-diff, 0))
                avg_gain = sum(gains) / 14
                avg_loss = sum(losses) / 14
                rs = avg_gain / avg_loss if avg_loss != 0 else 100
                rsi = 100 - (100 / (1 + rs))
                
                change = ((curr_p - closes[-7]) / closes[-7]) * 100
                return {"price": curr_p, "rsi": rsi, "change": change}
    except: return None

async def get_ai_summary(prompt):
    try:
        res = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": f"Ты Джарвис, циничный крипто-аналитик. Сегодня 28 декабря 2025. {prompt}"}]
        )
        if any(x in res for x in ["http", "请求", "limit"]): return None
        return res
    except: return None

@dp.message()
async def commands_handler(message: types.Message):
    if message.from_user.is_bot: return
    if message.text and message.text.lower() == "!анализ":
        btc = await get_ticker_data("BTCUSDT")
        eth = await get_ticker_data("ETHUSDT")
        
        analysis_text = (
            f"₿ BTC: ${btc['price']:.0f} (RSI: {btc['rsi']:.1f}, 30m: {btc['change']:.2f}%)\n"
            f"Ξ ETH: ${eth['price']:.2f} (RSI: {eth['rsi']:.1f}, 30m: {eth['change']:.2f}%)"
        )
        
        prompt = f"Данные рынка:\n{analysis_text}\nДай дерзкий прогноз на 30 минут. Если RSI > 70 - кричи 'ПЕРЕГРЕВ', если < 30 - 'ДНО'."
        ai_say = await get_ai_summary(prompt)
        await message.reply(f"🎯 **ТЕХАНАЛИЗ BINANCE**\n\n{analysis_text}\n\n💬 **Джарвис:** {ai_say}")

async def main_loop():
    global posted_links
    SOURCES = [{"url": "https://blockchain.news/RSS/", "h": "🐋 WHALE ALERT"},
               {"url": "https://www.forexfactory.com/ff_calendar_thisweek.xml", "h": "📊 МАКРО"}]
    tz = pytz.timezone('Europe/Warsaw')
    last_morning, last_evening = None, None

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        while True:
            now = datetime.datetime.now(tz)
            if now.hour >= 8 and last_morning != now.day:
                btc = await get_ticker_data("BTCUSDT")
                res = await get_ai_summary(f"BTC: ${btc['price']}. Утренний брифинг.")
                if res: await bot.send_message(CHANNEL_ID, f"☕️ **УТРЕННИЙ БРИФИНГ**\n\n{res}")
                last_morning = now.day

            for src in SOURCES:
                try:
                    async with session.get(src["url"], timeout=20) as r:
                        feed = feedparser.parse(await r.read())
                    for entry in feed.entries[:10]:
                        if entry.link in posted_links: continue
                        if not any(x in entry.title.upper() for x in ["MILLION", "BILLION", "RATE", "CPI"]): continue
                        
                        posted_links.add(entry.link)
                        t_ru = translator.translate(entry.title).strip()
                        res = await get_ai_summary(f"Новость: {t_ru}. Напиши злую шутку и ПОЗИТИВ/НЕГАТИВ.")
                        if res:
                            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Источник", url=entry.link)]])
                            await bot.send_message(CHANNEL_ID, f"{src['h']}\n\n📌 {t_ru}\n\n💬 *Джарвис:* {res}", reply_markup=markup)
                        await asyncio.sleep(60)
                except: pass
            await asyncio.sleep(1200)

async def main():
    asyncio.create_task(main_loop()); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
