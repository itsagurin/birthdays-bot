import os
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME
from datetime import datetime
from typing import List, Optional
import pymongo
from bson import ObjectId


class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def init(self):
        """Инициализация подключения к MongoDB"""
        if not MONGODB_URL:
            raise RuntimeError("Не задана переменная окружения MONGODB_URL")

        # Создаём клиент с TLS и корневыми сертификатами certifi
        self.client = AsyncIOMotorClient(
            MONGODB_URL,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsCAFile=certifi.where(),
            socketTimeoutMS=20000,
            connectTimeoutMS=20000,
            serverSelectionTimeoutMS=20000,
        )

        # Принудительный вызов ping, чтобы проверить связь и сразу поймать ошибки
        try:
            await self.client.admin.command("ping")
        except Exception as e:
            raise RuntimeError(f"Не удалось подключиться к MongoDB: {e}")

        # Инициализируем базу и создаём индексы
        self.db = self.client[DATABASE_NAME]
        await self.create_indexes()
        print(f"✅ Успешно подключились к базе {DATABASE_NAME}")

    async def create_indexes(self):
        """Создание индексов для оптимизации запросов"""
        await self.db.users.create_index("telegram_id", unique=True)
        await self.db.birthdays.create_index("user_id")
        await self.db.reminders.create_index("birthday_id")

    async def add_user(self, telegram_id: int, username: str = None):
        """Добавить пользователя"""
        user_data = {
            "telegram_id": telegram_id,
            "username": username,
            "created_at": datetime.utcnow()
        }
        try:
            await self.db.users.insert_one(user_data)
        except pymongo.errors.DuplicateKeyError:
            await self.db.users.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"username": username}}
            )

    async def add_birthday(self, user_id: int, name: str, birth_date: datetime, gift_ideas: str = None):
        birth_datetime = datetime.combine(birth_date.date(), datetime.min.time()) if hasattr(birth_date, 'date') else birth_date
        birthday_data = {
            "user_id": user_id,
            "name": name,
            "birth_date": birth_datetime,
            "gift_ideas": gift_ideas,
            "created_at": datetime.utcnow()
        }
        result = await self.db.birthdays.insert_one(birthday_data)
        return str(result.inserted_id)

    async def get_birthdays(self, user_id: int):
        cursor = self.db.birthdays.find({"user_id": user_id}).sort("birth_date", 1)
        birthdays = []
        async for b in cursor:
            b["id"] = str(b["_id"])
            del b["_id"]
            if isinstance(b["birth_date"], datetime):
                b["birth_date"] = b["birth_date"].date()
            birthdays.append(b)
        return birthdays

    async def update_gift_ideas(self, birthday_id: str, gift_ideas: str):
        await self.db.birthdays.update_one(
            {"_id": ObjectId(birthday_id)},
            {"$set": {"gift_ideas": gift_ideas}}
        )

    async def delete_birthday(self, birthday_id: str, user_id: int):
        await self.db.reminders.delete_many({"birthday_id": birthday_id})
        await self.db.birthdays.delete_one({
            "_id": ObjectId(birthday_id),
            "user_id": user_id
        })

    async def add_reminder(self, birthday_id: str, days_before: int):
        reminder_data = {
            "birthday_id": birthday_id,
            "days_before": days_before,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        await self.db.reminders.insert_one(reminder_data)

    async def get_reminders(self, birthday_id: str):
        cursor = self.db.reminders.find({
            "birthday_id": birthday_id,
            "is_active": True
        }).sort("days_before", 1)
        reminders = []
        async for r in cursor:
            r["id"] = str(r["_id"])
            del r["_id"]
            reminders.append(r)
        return reminders

    async def get_all_active_reminders(self):
        pipeline = [
            {"$match": {"is_active": True}},
            {"$lookup": {
                "from": "birthdays",
                "let": {"birthday_id": {"$toObjectId": "$birthday_id"}},
                "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", "$$birthday_id"]}}}],
                "as": "birthday"
            }},
            {"$unwind": "$birthday"},
            {"$project": {
                "id": {"$toString": "$_id"},
                "birthday_id": 1,
                "days_before": 1,
                "is_active": 1,
                "name": "$birthday.name",
                "birth_date": "$birthday.birth_date",
                "user_id": "$birthday.user_id",
                "gift_ideas": "$birthday.gift_ideas"
            }}
        ]
        cursor = self.db.reminders.aggregate(pipeline)
        reminders = []
        async for r in cursor:
            if isinstance(r["birth_date"], datetime):
                r["birth_date"] = r["birth_date"].date()
            reminders.append(r)
        return reminders

    async def delete_reminder(self, reminder_id: str):
        await self.db.reminders.delete_one({"_id": ObjectId(reminder_id)})

    async def get_birthday_by_id(self, birthday_id: str):
        try:
            b = await self.db.birthdays.find_one({"_id": ObjectId(birthday_id)})
            if not b:
                return None
            b["id"] = str(b["_id"])
            del b["_id"]
            if isinstance(b["birth_date"], datetime):
                b["birth_date"] = b["birth_date"].date()
            return b
        except Exception:
            return None

    async def close(self):
        if self.client:
            self.client.close()


db = Database()