from datetime import datetime, date
import re


def parse_date(date_str: str) -> datetime:
    """Парсит дату в различных форматах"""
    date_str = date_str.strip()

    # Попробуем различные форматы
    formats = [
        "%d.%m.%Y",  # 01.01.1990
        "%d/%m/%Y",  # 01/01/1990
        "%d-%m-%Y",  # 01-01-1990
        "%d.%m",  # 01.01 (текущий год)
        "%d/%m",  # 01/01 (текущий год)
        "%d-%m",  # 01-01 (текущий год)
    ]

    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # Если год не указан, используем текущий
            if fmt in ["%d.%m", "%d/%m", "%d-%m"]:
                parsed_date = parsed_date.replace(year=datetime.now().year)
            return parsed_date
        except ValueError:
            continue

    raise ValueError("Неверный формат даты")


def format_date(birth_date: date) -> str:
    """Форматирует дату для отображения"""
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]

    return f"{birth_date.day} {months[birth_date.month - 1]} {birth_date.year}"


def calculate_age(birth_date: date) -> int:
    """Вычисляет возраст"""
    today = date.today()
    age = today.year - birth_date.year

    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1

    return age


def days_until_birthday(birth_date: date) -> int:
    """Вычисляет дни до дня рождения"""
    today = date.today()
    this_year_birthday = birth_date.replace(year=today.year)

    if this_year_birthday < today:
        this_year_birthday = birth_date.replace(year=today.year + 1)

    return (this_year_birthday - today).days


def format_birthday_info(birthday: dict) -> str:
    """Форматирует информацию о дне рождения"""
    birth_date = birthday['birth_date']
    age = calculate_age(birth_date)
    days_left = days_until_birthday(birth_date)

    info = f"🎂 *{birthday['name']}*\n"
    info += f"📅 {format_date(birth_date)} ({age} лет)\n"

    if days_left == 0:
        info += "🎉 *СЕГОДНЯ ДЕНЬ РОЖДЕНИЯ!*\n"
    elif days_left == 1:
        info += "🔥 *Завтра день рождения!*\n"
    else:
        info += f"⏰ Через {days_left} дней\n"

    if birthday.get('gift_ideas'):
        info += f"🎁 Идеи подарков: {birthday['gift_ideas']}\n"

    return info