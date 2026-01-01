import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web

logging.basicConfig(level=logging.INFO)

async def handle(request):
    return web.Response(text="Jarvis is alive")

async def main():
    # Настройка веб-сервера для Koyeb
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    asyncio.create_task(site.start())

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # --- ТЕСТОВОЕ СООБЩЕНИЕ ---
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text="🚀 Сэр, Джарвис успешно запущен в облаке и готов к работе!")
        print("Тестовое сообщение отправлено в канал!")
    except Exception as e:
        print(f"Ошибка при отправке в канал: {e}")
    # --------------------------

    print("Джарвис запущен и начинает охоту на китов...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
