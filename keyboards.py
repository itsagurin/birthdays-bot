from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить день рождения", callback_data="add_birthday")],
        [InlineKeyboardButton(text="📅 Мои дни рождения", callback_data="list_birthdays")],
        [InlineKeyboardButton(text="🔔 Настроить напоминания", callback_data="manage_reminders")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])
    return keyboard

def birthday_actions(birthday_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Идеи подарков", callback_data=f"gifts_{birthday_id}")],
        [InlineKeyboardButton(text="🔔 Напоминания", callback_data=f"reminders_{birthday_id}")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{birthday_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_birthdays")]
    ])
    return keyboard

def gift_actions(birthday_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить идеи", callback_data=f"edit_gifts_{birthday_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"birthday_{birthday_id}")]
    ])
    return keyboard

def reminder_actions(birthday_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить напоминание", callback_data=f"add_reminder_{birthday_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"birthday_{birthday_id}")]
    ])
    return keyboard

def reminder_days():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 день", callback_data="remind_1")],
        [InlineKeyboardButton(text="3 дня", callback_data="remind_3")],
        [InlineKeyboardButton(text="7 дней", callback_data="remind_7")],
        [InlineKeyboardButton(text="14 дней", callback_data="remind_14")],
        [InlineKeyboardButton(text="30 дней", callback_data="remind_30")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    return keyboard

def confirm_delete(birthday_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{birthday_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"birthday_{birthday_id}")]
    ])
    return keyboard

def back_to_main():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard