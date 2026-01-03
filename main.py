import asyncio
import aiohttp
import ccxt
import feedparser
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, CHANNEL_ID
from aiohttp import web
from openai import AsyncOpenAI  # Для ИИ-рассуждений

# Настройка ИИ (Бесплатный ключ можно взять на OpenRouter)
# Если ключа пока нет, он просто будет выдавать текст сам
AI_CLIENT = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="ВАШ_КЛЮЧ_OPENROUTER", 
)

async def get_ai_opinion(news_text):
    """Джарвис начинает рассуждать"""
    try:
        response = await AI_CLIENT.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free", # Бесплатная мощная модель
            messages=[{
                "role": "system", 
                "content": "Ты - Джарвис, ИИ-помощник. Проанализируй новость и кратко скажи, как она повлияет на курс Биткоина. Будь ироничным и точным."
            }, {"role": "user", "content": news_text}]
        )
        return response.choices[0].message.content
    except:
        return "Сэр, мои аналитические модули перегружены, но ситуация явно накаляется."

async def main():
    # ... (код сервера остается прежним) ...
    bot = Bot(token=BOT_TOKEN)
    
    # ЭКСТРЕННЫЙ АНАЛИЗ
    news_brief = "США нанесли удары по Венесуэле, Мадуро захвачен. Золото растет."
    ai_thought = await get_ai_opinion(news_brief) # Вот тут он начинает ДУМАТЬ
    
    report = (
        f"🚨 **ЭКСТРЕННЫЙ ДОКЛАД: ВЕНЕСУЭЛА**\n\n"
        f"📍 **ФАКТЫ:** США вошли в Каракас. Мадуро вне игры.\n\n"
        f"🧠 **РАССУЖДЕНИЯ ДЖАРВИСА:**\n{ai_thought}\n\n"
        f"🛡️ *Системы переведены в режим 'War Room'.*"
    )
    
    await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
    # ... (дальше запуск polling) ...
