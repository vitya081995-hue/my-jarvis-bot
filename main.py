import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from aiohttp import web # Добавьте это

logging.basicConfig(level=logging.INFO)

# Крошечный сервер для обмана Koyeb
async def handle(request):
    return web.Response(text="Jarvis is alive")

async def main():
    # Запускаем веб-сервер на порту 8000 в фоне
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    asyncio.create_task(site.start())

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    print("Джарвис запущен и начинает охоту на китов...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
