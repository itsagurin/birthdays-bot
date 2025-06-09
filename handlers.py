from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from keyboards import *
from utils import parse_date, format_birthday_info
import logging

router = Router()


# Состояния для FSM
class BirthdayStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_gift_ideas = State()
    editing_gifts = State()


# Переменная для хранения временных данных
temp_birthday_data = {}
temp_reminder_data = {}


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await db.add_user(message.from_user.id, message.from_user.username)

    welcome_text = """
🎂 *Добро пожаловать в Дневник Дней Рождения!*

Этот бот поможет вам:
• Сохранить все важные дни рождения
• Настроить напоминания заранее
• Записать идеи подарков
• Не забыть поздравить близких

Выберите действие из меню ниже:
    """

    await message.answer(welcome_text, reply_markup=main_menu(), parse_mode='Markdown')


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    """Показать главное меню"""
    welcome_text = """
🎂 *Дневник Дней Рождения*

Выберите действие из меню ниже:
    """
    await callback.message.edit_text(welcome_text, reply_markup=main_menu(), parse_mode='Markdown')


@router.callback_query(F.data == "add_birthday")
async def add_birthday_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления дня рождения"""
    await callback.message.edit_text(
        "👤 Введите имя именинника:",
        reply_markup=back_to_main()
    )
    await state.set_state(BirthdayStates.waiting_for_name)


@router.message(BirthdayStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени именинника"""
    name = message.text.strip()

    if len(name) > 200:
        await message.answer("❌ Имя слишком длинное! Попробуйте еще раз.")
        return

    await state.update_data(name=name)

    await message.answer(
        f"📅 Введите дату рождения для *{name}*\n\n"
        "Поддерживаемые форматы:\n"
        "• 01.01.1990\n"
        "• 01/01/1990\n"
        "• 01-01-1990\n"
        "• 01.01 (текущий год)",
        parse_mode='Markdown'
    )
    await state.set_state(BirthdayStates.waiting_for_date)


@router.message(BirthdayStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка даты рождения"""
    try:
        birth_date = parse_date(message.text)
        data = await state.get_data()

        # Добавляем день рождения в базу
        birthday_id = await db.add_birthday(
            message.from_user.id,
            data['name'],
            birth_date
        )

        await message.answer(
            f"✅ День рождения *{data['name']}* успешно добавлен!\n\n"
            "🎁 Хотите добавить идеи подарков?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data=f"add_gifts_{birthday_id}")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="main_menu")]
            ]),
            parse_mode='Markdown'
        )

        await state.clear()

    except ValueError as e:
        await message.answer(
            "❌ Неверный формат даты! Попробуйте еще раз.\n\n"
            "Поддерживаемые форматы:\n"
            "• 01.01.1990\n"
            "• 01/01/1990\n"
            "• 01-01-1990\n"
            "• 01.01 (текущий год)"
        )


@router.callback_query(F.data.startswith("add_gifts_"))
async def add_gifts_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления идей подарков"""
    birthday_id = int(callback.data.split("_")[2])
    temp_birthday_data[callback.from_user.id] = birthday_id

    await callback.message.edit_text(
        "🎁 Введите идеи подарков (можно через запятую):",
        reply_markup=back_to_main()
    )
    await state.set_state(BirthdayStates.waiting_for_gift_ideas)


@router.message(BirthdayStates.waiting_for_gift_ideas)
async def process_gift_ideas(message: Message, state: FSMContext):
    """Обработка идей подарков"""
    gift_ideas = message.text.strip()
    birthday_id = temp_birthday_data.get(message.from_user.id)

    if birthday_id:
        await db.update_gift_ideas(birthday_id, gift_ideas)
        await message.answer(
            "✅ Идеи подарков сохранены!",
            reply_markup=main_menu()
        )
        del temp_birthday_data[message.from_user.id]

    await state.clear()


@router.callback_query(F.data == "list_birthdays")
async def list_birthdays(callback: CallbackQuery):
    """Показать список дней рождения"""
    birthdays = await db.get_birthdays(callback.from_user.id)

    if not birthdays:
        await callback.message.edit_text(
            "📅 У вас пока нет сохраненных дней рождения.\n\n"
            "Добавьте первый день рождения!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить", callback_data="add_birthday")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
            ])
        )
        return

    # Сортируем по дням до дня рождения
    from utils import days_until_birthday
    birthdays.sort(key=lambda x: days_until_birthday(x['birth_date']))

    text = "📅 *Ваши дни рождения:*\n\n"
    keyboard_buttons = []

    for birthday in birthdays:
        text += format_birthday_info(birthday) + "\n"
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"👤 {birthday['name']}",
            callback_data=f"birthday_{birthday['id']}"
        )])

    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode='Markdown'
    )


@router.callback_query(F.data.startswith("birthday_"))
async def show_birthday_details(callback: CallbackQuery):
    """Показать детали дня рождения"""
    birthday_id = int(callback.data.split("_")[1])
    birthday = await db.get_birthday_by_id(birthday_id)

    if not birthday:
        await callback.answer("❌ День рождения не найден")
        return

    text = format_birthday_info(birthday)

    await callback.message.edit_text(
        text,
        reply_markup=birthday_actions(birthday_id),
        parse_mode='Markdown'
    )


@router.callback_query(F.data.startswith("gifts_"))
async def show_gifts(callback: CallbackQuery):
    """Показать идеи подарков"""
    birthday_id = int(callback.data.split("_")[1])
    birthday = await db.get_birthday_by_id(birthday_id)

    if not birthday:
        await callback.answer("❌ День рождения не найден")
        return

    text = f"🎁 *Идеи подарков для {birthday['name']}:*\n\n"

    if birthday['gift_ideas']:
        text += birthday['gift_ideas']
    else:
        text += "Пока нет идей подарков"

    await callback.message.edit_text(
        text,
        reply_markup=gift_actions(birthday_id),
        parse_mode='Markdown'
    )


@router.callback_query(F.data.startswith("edit_gifts_"))
async def edit_gifts_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования идей подарков"""
    birthday_id = int(callback.data.split("_")[2])
    temp_birthday_data[callback.from_user.id] = birthday_id

    await callback.message.edit_text(
        "🎁 Введите новые идеи подарков:",
        reply_markup=back_to_main()
    )
    await state.set_state(BirthdayStates.editing_gifts)


@router.message(BirthdayStates.editing_gifts)
async def process_edit_gifts(message: Message, state: FSMContext):
    """Обработка редактирования идей подарков"""
    gift_ideas = message.text.strip()
    birthday_id = temp_birthday_data.get(message.from_user.id)

    if birthday_id:
        await db.update_gift_ideas(birthday_id, gift_ideas)
        await message.answer(
            "✅ Идеи подарков обновлены!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 К дню рождения", callback_data=f"birthday_{birthday_id}")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
            ])
        )
        del temp_birthday_data[message.from_user.id]

    await state.clear()


@router.callback_query(F.data.startswith("add_reminder_"))
async def add_reminder_start(callback: CallbackQuery):
    """Начало добавления напоминания"""
    birthday_id = int(callback.data.split("_")[2])
    temp_reminder_data[callback.from_user.id] = birthday_id

    await callback.message.edit_text(
        "🔔 За сколько дней до дня рождения напомнить?",
        reply_markup=reminder_days()
    )


@router.callback_query(F.data.startswith("remind_"))
async def process_reminder_days(callback: CallbackQuery):
    """Обработка выбора дней для напоминания"""
    days = int(callback.data.split("_")[1])
    birthday_id = temp_reminder_data.get(callback.from_user.id)

    if birthday_id:
        await db.add_reminder(birthday_id, days)

        days_text = "в день рождения" if days == 0 else f"за {days} дней" if days > 1 else "за 1 день"

        await callback.message.edit_text(
            f"✅ Напоминание {days_text} добавлено!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔔 К напоминаниям", callback_data=f"reminders_{birthday_id}")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
            ])
        )
        del temp_reminder_data[callback.from_user.id]


@router.callback_query(F.data.startswith("reminders_"))
async def show_reminders(callback: CallbackQuery):
    """Показать напоминания для дня рождения"""
    birthday_id = int(callback.data.split("_")[1])
    birthday = await db.get_birthday_by_id(birthday_id)
    reminders = await db.get_reminders(birthday_id)

    if not birthday:
        await callback.answer("❌ День рождения не найден")
        return

    text = f"🔔 *Напоминания для {birthday['name']}:*\n\n"

    if reminders:
        for reminder in reminders:
            days = reminder['days_before']
            if days == 0:
                text += "• В день рождения\n"
            elif days == 1:
                text += "• За 1 день\n"
            else:
                text += f"• За {days} дней\n"
    else:
        text += "Напоминания не настроены"

    await callback.message.edit_text(
        text,
        reply_markup=reminder_actions(birthday_id),
        parse_mode='Markdown'
    )


@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete_birthday(callback: CallbackQuery):
    """Подтверждение удаления дня рождения"""
    birthday_id = int(callback.data.split("_")[1])
    birthday = await db.get_birthday_by_id(birthday_id)

    if not birthday:
        await callback.answer("❌ День рождения не найден")
        return

    await callback.message.edit_text(
        f"❌ Вы уверены, что хотите удалить день рождения *{birthday['name']}*?\n\n"
        "Это действие нельзя отменить!",
        reply_markup=confirm_delete(birthday_id),
        parse_mode='Markdown'
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_birthday_confirmed(callback: CallbackQuery):
    """Подтвержденное удаление дня рождения"""
    birthday_id = int(callback.data.split("_")[2])

    await db.delete_birthday(birthday_id, callback.from_user.id)

    await callback.message.edit_text(
        "✅ День рождения удален!",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "manage_reminders")
async def manage_reminders(callback: CallbackQuery):
    """Управление напоминаниями"""
    birthdays = await db.get_birthdays(callback.from_user.id)

    if not birthdays:
        await callback.message.edit_text(
            "📅 У вас пока нет сохраненных дней рождения.\n\n"
            "Сначала добавьте дни рождения!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить день рождения", callback_data="add_birthday")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
            ])
        )
        return

    text = "🔔 *Настройка напоминаний*\n\n"
    text += "Выберите день рождения для настройки напоминаний:"

    keyboard_buttons = []
    for birthday in birthdays:
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"👤 {birthday['name']}",
            callback_data=f"reminders_{birthday['id']}"
        )])

    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode='Markdown'
    )


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показать справку"""
    help_text = """
🎂 *Помощь по использованию бота*

*Основные функции:*
• ➕ Добавление дней рождения с датами
• 🎁 Сохранение идей подарков
• 🔔 Настройка напоминаний (за 1, 3, 7, 14, 30 дней)
• 📅 Просмотр всех дней рождения

*Форматы дат:*
• 01.01.1990
• 01/01/1990  
• 01-01-1990
• 01.01 (текущий год)

*Напоминания:*
Бот будет присылать уведомления каждый день в 9:00 утра за указанное количество дней до дня рождения.

*Команды:*
/start - Главное меню
/help - Эта справка

Удачного использования! 🎉
    """

    await callback.message.edit_text(
        help_text,
        reply_markup=back_to_main(),
        parse_mode='Markdown'
    )


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=main_menu()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
🎂 *Помощь по использованию бота*

*Основные функции:*
• ➕ Добавление дней рождения с датами
• 🎁 Сохранение идей подарков
• 🔔 Настройка напоминаний (за 1, 3, 7, 14, 30 дней)
• 📅 Просмотр всех дней рождения

*Форматы дат:*
• 01.01.1990
• 01/01/1990  
• 01-01-1990
• 01.01 (текущий год)

*Напоминания:*
Бот будет присылать уведомления каждый день в 9:00 утра за указанное количество дней до дня рождения.

*Команды:*
/start - Главное меню
/help - Эта справка

Удачного использования! 🎉
    """

    await message.answer(
        help_text,
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )