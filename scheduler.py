from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, date
from database import db
from utils import days_until_birthday, format_birthday_info
import asyncio


class ReminderScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        """Запускает планировщик"""
        self.scheduler.add_job(
            self.check_reminders,
            'cron',
            hour=9,  # Проверяем каждый день в 9 утра
            minute=0
        )
        self.scheduler.start()

    async def check_reminders(self):
        """Проверяет напоминания и отправляет уведомления"""
        try:
            reminders = await db.get_all_active_reminders()

            for reminder in reminders:
                birth_date = reminder['birth_date']
                days_left = days_until_birthday(birth_date)

                # Если количество дней до дня рождения совпадает с напоминанием
                if days_left == reminder['days_before']:
                    await self.send_reminder(reminder)

        except Exception as e:
            print(f"Ошибка при проверке напоминаний: {e}")

    async def send_reminder(self, reminder):
        """Отправляет напоминание пользователю"""
        try:
            user_id = reminder['user_id']
            name = reminder['name']
            days_before = reminder['days_before']
            gift_ideas = reminder['gift_ideas']

            if days_before == 0:
                message = f"🎉 *СЕГОДНЯ ДЕНЬ РОЖДЕНИЯ!*\n\n"
                message += f"У {name} сегодня день рождения! 🎂"
            elif days_before == 1:
                message = f"🔥 *Завтра день рождения!*\n\n"
                message += f"У {name} завтра день рождения! 🎂"
            else:
                message = f"🔔 *Напоминание о дне рождения*\n\n"
                message += f"У {name} день рождения через {days_before} дней! 🎂"

            if gift_ideas:
                message += f"\n\n🎁 Идеи подарков: {gift_ideas}"

            await self.bot.send_message(user_id, message, parse_mode='Markdown')

        except Exception as e:
            print(f"Ошибка при отправке напоминания: {e}")

    def stop(self):
        """Останавливает планировщик"""
        self.scheduler.shutdown()