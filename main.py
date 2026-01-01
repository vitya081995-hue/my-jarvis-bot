import asyncio
import logging
import ccxt
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

logging.basicConfig(level=logging.INFO)
exchange = ccxt.binance()

async def handle(request):
    return web.Response(text="Jarvis System: Online")

# Функция получения цены
async def get_crypto_price(symbol="BTC/USDT"):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except:
        return None

async def main():
    # Веб-сервер для Koyeb (Free tier)
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8000).start()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Команда /price в личку боту
    @dp.message(Command("price"))
    async def send_price(message: types.Message):
        price = await get_crypto_price()
        await message.answer(f"📊 Сэр, цена BTC сейчас: ${price}")

    # Приветствие в канал
    btc_now = await get_crypto_price()
    status_text = (
        f"🚀 **Джарвис активирован в облаке!**\n\n"
        f"✅ Система: Стабильна\n"
        f"💰 BTC/USDT: ${btc_now}\n"
        f"📡 Охота на новости: Начата"
    )
    
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=status_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка связи с каналом: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
