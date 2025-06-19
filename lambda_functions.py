import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import router
from database import db

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(router)

def lambda_handler(event, context):
    body = event.get("body")
    if not body:
        return {"statusCode": 400, "body": "No body provided."}

    async def process():
        update = types.Update.model_validate_json(body)
        await db.init()
        await dp.feed_update(bot, update)
        return {"statusCode": 200, "body": "ok"}

    try:
        result = asyncio.run(process())
        return result
    except Exception as e:
        logging.exception("Update processing failed")
        return {"statusCode": 500, "body": str(e)}