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
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[DATABASE_NAME]
        await self.create_indexes()

    async def create_indexes(self):
        """Создание индексов для оптимизации запросов"""
        # Индекс для уникальности telegram_id в коллекции users
        await self.db.users.create_index("telegram_id", unique=True)
        # Индекс для быстрого поиска дней рождения по user_id
        await self.db.birthdays.create_index("user_id")
        # Индекс для быстрого поиска напоминаний по birthday_id
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
            # Пользователь уже существует, обновляем username если он изменился
            await self.db.users.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"username": username}}
            )

    async def add_birthday(self, user_id: int, name: str, birth_date: datetime, gift_ideas: str = None):
        """Добавить день рождения"""
        # Преобразуем datetime в datetime с обнуленным временем для MongoDB
        birth_datetime = datetime.combine(birth_date.date(), datetime.min.time()) if hasattr(birth_date,
                                                                                             'date') else birth_date

        birthday_data = {
            "user_id": user_id,
            "name": name,
            "birth_date": birth_datetime,  # Сохраняем как datetime, а не date
            "gift_ideas": gift_ideas,
            "created_at": datetime.utcnow()
        }

        result = await self.db.birthdays.insert_one(birthday_data)
        return str(result.inserted_id)

    async def get_birthdays(self, user_id: int):
        """Получить все дни рождения пользователя"""
        cursor = self.db.birthdays.find({"user_id": user_id}).sort("birth_date", 1)
        birthdays = []

        async for birthday in cursor:
            birthday["id"] = str(birthday["_id"])
            del birthday["_id"]
            # Преобразуем datetime обратно в date для совместимости с utils.py
            if isinstance(birthday["birth_date"], datetime):
                birthday["birth_date"] = birthday["birth_date"].date()
            birthdays.append(birthday)

        return birthdays

    async def update_gift_ideas(self, birthday_id: str, gift_ideas: str):
        """Обновить идеи подарков"""
        await self.db.birthdays.update_one(
            {"_id": ObjectId(birthday_id)},
            {"$set": {"gift_ideas": gift_ideas}}
        )

    async def delete_birthday(self, birthday_id: str, user_id: int):
        """Удалить день рождения"""
        # Сначала удаляем все связанные напоминания
        await self.db.reminders.delete_many({"birthday_id": birthday_id})

        # Затем удаляем день рождения
        await self.db.birthdays.delete_one({
            "_id": ObjectId(birthday_id),
            "user_id": user_id
        })

    async def add_reminder(self, birthday_id: str, days_before: int):
        """Добавить напоминание"""
        reminder_data = {
            "birthday_id": birthday_id,
            "days_before": days_before,
            "is_active": True,
            "created_at": datetime.utcnow()
        }

        await self.db.reminders.insert_one(reminder_data)

    async def get_reminders(self, birthday_id: str):
        """Получить напоминания для дня рождения"""
        cursor = self.db.reminders.find({
            "birthday_id": birthday_id,
            "is_active": True
        }).sort("days_before", 1)

        reminders = []
        async for reminder in cursor:
            reminder["id"] = str(reminder["_id"])
            del reminder["_id"]
            reminders.append(reminder)

        return reminders

    async def get_all_active_reminders(self):
        """Получить все активные напоминания с информацией о днях рождения"""
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

        async for reminder in cursor:
            # Преобразуем datetime в date для совместимости
            if isinstance(reminder["birth_date"], datetime):
                reminder["birth_date"] = reminder["birth_date"].date()
            reminders.append(reminder)

        return reminders

    async def delete_reminder(self, reminder_id: str):
        """Удалить напоминание"""
        await self.db.reminders.delete_one({"_id": ObjectId(reminder_id)})

    async def get_birthday_by_id(self, birthday_id: str):
        """Получить день рождения по ID"""
        try:
            birthday = await self.db.birthdays.find_one({"_id": ObjectId(birthday_id)})
            if birthday:
                birthday["id"] = str(birthday["_id"])
                del birthday["_id"]
                # Преобразуем datetime в date для совместимости
                if isinstance(birthday["birth_date"], datetime):
                    birthday["birth_date"] = birthday["birth_date"].date()
                return birthday
            return None
        except:
            return None

    async def close(self):
        """Закрыть соединение с базой данных"""
        if self.client:
            self.client.close()


db = Database()