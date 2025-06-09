import asyncpg
from config import DATABASE_URL
from datetime import datetime
from typing import List, Optional


class Database:
    def __init__(self):
        self.pool = None

    async def init(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self.create_tables()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS users
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   telegram_id
                                   BIGINT
                                   UNIQUE
                                   NOT
                                   NULL,
                                   username
                                   VARCHAR
                               (
                                   100
                               ),
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )
                               ''')

            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS birthdays
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   user_id
                                   BIGINT
                                   REFERENCES
                                   users
                               (
                                   telegram_id
                               ) ON DELETE CASCADE,
                                   name VARCHAR
                               (
                                   200
                               ) NOT NULL,
                                   birth_date DATE NOT NULL,
                                   gift_ideas TEXT,
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )
                               ''')

            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS reminders
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   birthday_id
                                   INTEGER
                                   REFERENCES
                                   birthdays
                               (
                                   id
                               ) ON DELETE CASCADE,
                                   days_before INTEGER NOT NULL,
                                   is_active BOOLEAN DEFAULT TRUE,
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )
                               ''')

    async def add_user(self, telegram_id: int, username: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (telegram_id, username) VALUES ($1, $2) ON CONFLICT (telegram_id) DO NOTHING",
                telegram_id, username
            )

    async def add_birthday(self, user_id: int, name: str, birth_date: datetime, gift_ideas: str = None):
        async with self.pool.acquire() as conn:
            birthday_id = await conn.fetchval(
                "INSERT INTO birthdays (user_id, name, birth_date, gift_ideas) VALUES ($1, $2, $3, $4) RETURNING id",
                user_id, name, birth_date.date(), gift_ideas
            )
            return birthday_id

    async def get_birthdays(self, user_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM birthdays WHERE user_id = $1 ORDER BY birth_date",
                user_id
            )
            return [dict(row) for row in rows]

    async def update_gift_ideas(self, birthday_id: int, gift_ideas: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE birthdays SET gift_ideas = $1 WHERE id = $2",
                gift_ideas, birthday_id
            )

    async def delete_birthday(self, birthday_id: int, user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM birthdays WHERE id = $1 AND user_id = $2",
                birthday_id, user_id
            )

    async def add_reminder(self, birthday_id: int, days_before: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO reminders (birthday_id, days_before) VALUES ($1, $2)",
                birthday_id, days_before
            )

    async def get_reminders(self, birthday_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM reminders WHERE birthday_id = $1 AND is_active = TRUE ORDER BY days_before",
                birthday_id
            )
            return [dict(row) for row in rows]

    async def get_all_active_reminders(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                                    SELECT r.*, b.name, b.birth_date, b.user_id, b.gift_ideas
                                    FROM reminders r
                                             JOIN birthdays b ON r.birthday_id = b.id
                                    WHERE r.is_active = TRUE
                                    ''')
            return [dict(row) for row in rows]

    async def delete_reminder(self, reminder_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM reminders WHERE id = $1",
                reminder_id
            )

    async def get_birthday_by_id(self, birthday_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM birthdays WHERE id = $1",
                birthday_id
            )
            return dict(row) if row else None


db = Database()