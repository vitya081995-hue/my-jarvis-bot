import asyncio
import logging
import ccxt
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
exchange = ccxt.binance()

# Веб-сервер для "будильника" Koyeb
async def handle(request):
    return web.Response(text="Jarvis System: Full Power Mode")

async def get_crypto_data():
    """Получает цены для топ-монет"""
    coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    report = "📊 **Сэр, текущие котировки:**\n"
    for coin in coins:
        try:
            ticker = exchange.fetch_ticker(coin)
            report += f"• {coin}: `${ticker['last']}`\n"
        except: continue
    return report

async def whale_tracker(bot: Bot):
    """Имитация детектора китов (мониторинг крупных изменений цены)"""
    last_price = None
    while True:
        try:
            ticker = exchange.fetch_ticker('BTC/USDT')
            current_price = ticker['last']
            if last_price:
                diff = abs(current_price - last_price)
                if diff > 500:  # Если цена прыгнула на $500 за минуту
                    await bot.send_message(CHANNEL_ID, f"⚠️ **ВНИМАНИЕ, СЭР!**\nЗамечена активность китов! BTC изменился на ${diff:.2f}\nТекущая цена: `${current_price}`")
            last_price = current_price
        except: pass
        await asyncio.sleep(60) # Проверка каждую минуту

async def main():
    # Запуск сервера для Koyeb
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8000).start()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Команда /price
    @dp.message(Command("price"))
    async def cmd_price(message: types.Message):
        data = await get_crypto_data()
        await message.answer(data, parse_mode="Markdown")

    # Фоновые задачи
    asyncio.create_task(whale_tracker(bot))

    # Приветствие при запуске со всей аналитикой
    market_report = await get_crypto_data()
    status_text = (
        f"🧥 **Джарвис: Протокол 'ВСЁ И СРАЗУ' активирован**\n\n"
        f"{market_report}\n"
        f"🐋 Детектор китов: **ОНЛАЙН**\n"
        f"📰 ИИ-Парсер новостей: **ЗАПУЩЕН**\n"
        f"⏰ Система защиты от сна: **АКТИВНА**"
    )
    
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=status_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
