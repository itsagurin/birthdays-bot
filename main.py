import asyncio
import logging
import threading
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
import uvicorn

from config import BOT_TOKEN
from database import db
from handlers import router
from scheduler import ReminderScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI приложение для health check
app = FastAPI()

@app.get('/')
async def health_check():
    return {'status': 'ok'}


def run_web():
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run('main:app', host='0.0.0.0', port=port, log_level='info')

async def start_bot():
    """Запуск логики Telegram-бота"""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутера
    dp.include_router(router)

    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await db.init()
        logger.info("База данных инициализирована")

        # Инициализация и запуск планировщика напоминаний
        logger.info("Запуск планировщика напоминаний...")
        scheduler = ReminderScheduler(bot)
        await scheduler.start()
        logger.info("Планировщик запущен")

        # Запуск бота
        logger.info("Запуск бота...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Закрытие соединений
        await bot.session.close()
        await db.close()
        if 'scheduler' in locals() and hasattr(scheduler, 'stop'):
            scheduler.stop()

if __name__ == '__main__':
    # Запускаем веб-сервер в отдельном потоке (для UptimeRobot)
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    # Запускаем бота
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
