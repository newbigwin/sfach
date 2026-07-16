import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import (
    add_event, get_events, delete_event, update_event_message_id, get_event_poll,
    add_poll, get_active_polls, get_poll, vote, get_poll_results, get_poll_votes,
    close_poll, update_poll_message_id, get_event,
    create_tournament, get_tournament, get_active_tournaments, start_tournament,
    get_tournament_participants, get_participant_count, finish_tournament,
    get_tournament_prizes, set_tournament_prize, remove_tournament_prize,
    create_match, get_match, set_match_winner, get_tournament_matches,
    get_tournament_standings, delete_tournament, update_tournament_message_id,
    set_setting, get_setting, get_chat_id,
    track_chat_member, get_chat_members,
    add_reminder, delete_reminder,
    auto_generate_bracket,
    create_recurring_event, get_recurring_events, delete_recurring_event,
    update_recurring_event, get_recurring_event,
    resolve_bets, get_match_bets, add_quiz,
    get_all_known_users, get_known_users_count,
    check_match_exists,
    get_bot_stats, get_tournament_analytics, get_match_stats
)

router = Router()


class CreateEvent(StatesGroup):
    title = State()
    description = State()
    event_date = State()
    image = State()
    confirm = State()
    editing = State()


class CreatePoll(StatesGroup):
    question = State()
    options = State()
    poll_type = State()
    image = State()
    editing = State()
    confirm = State()


class CreateTournament(StatesGroup):
    name = State()
    description = State()
    max_participants = State()
    prize_places = State()
    image = State()
    confirm = State()
    editing = State()


class CreateMatch(StatesGroup):
    player1 = State()
    player2 = State()
    confirm = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="События", callback_data="admin_events")],
        [InlineKeyboardButton(text="Голосования", callback_data="admin_polls")],
        [InlineKeyboardButton(text="Турниры", callback_data="admin_tournaments")],
        [InlineKeyboardButton(text="Напоминания", callback_data="admin_reminders")],
        [InlineKeyboardButton(text="Викторины", callback_data="admin_quizzes")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="История баланса", callback_data="admin_balance_history")],
        [InlineKeyboardButton(text="Утихомирить всех", callback_data="mute_menu")],
        [InlineKeyboardButton(text="Созвать всех", callback_data="summon_all")],
        [InlineKeyboardButton(text="Мануал", callback_data="admin_manual")],
    ])


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.chat.type != "private":
        return

    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "Панель администратора",
        reply_markup=admin_keyboard()
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.edit_text(
        "Панель администратора",
        reply_markup=admin_keyboard()
    )
    await callback.answer()


@router.message(Command("setchat"))
async def set_chat(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только админ может настроить чат.")
        return

    if message.chat.type == "private":
        await message.answer("Используйте эту команду в групповом чате!")
        return

    await set_setting("chat_id", message.chat.id)

    await message.answer(
        f"Чат настроен!\n\n"
        f"ID: {message.chat.id}\n"
        f"Название: {message.chat.title}\n\n"
        f"Теперь бот будет публиковать посты здесь."
    )


@router.message(Command("backup"))
async def backup_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    import os
    from config import DB_NAME

    if not os.path.exists(DB_NAME):
        await message.answer("База данных не найдена.")
        return

    from aiogram.types import FSInputFile
    await message.answer("Бэкап базы данных:")
    await message.answer_document(FSInputFile(DB_NAME), caption="backup_shadow_bot.db")


@router.message(Command("restore"))
async def restore_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "Для восстановления БД:\n"
        "1. Отправьте файл бэкапа командой /restore (с вложением)\n"
        "2. Или загрузите файл через Reply на сообщение с бэкапом"
    )


@router.message(Command("restore"), F.document)
async def restore_file_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.document:
        await message.answer("Прикрепите файл бэкапа.")
        return

    import os
    from config import DB_NAME

    file_info = await message.bot.get_file(message.document.file_id)
    await message.bot.download_file(file_info.file_path, DB_NAME)

    await message.answer("База данных восстановлена! Перезапустите бота.")


class CreateReminder(StatesGroup):
    title = State()
    remind_at = State()
    confirm = State()


@router.callback_query(F.data == "admin_reminders")
async def admin_reminders_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать напоминание", callback_data="create_reminder")],
        [InlineKeyboardButton(text="Активные напоминания", callback_data="list_reminders")],
        [InlineKeyboardButton(text="Повторяющиеся события", callback_data="recurring_events")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer("Напоминания:", reply_markup=kb)
    await callback.answer()


class CreateRecurringEvent(StatesGroup):
    title = State()
    description = State()
    day_of_week = State()
    time = State()
    confirm = State()


@router.callback_query(F.data == "recurring_events")
async def recurring_events_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать повторяющееся событие", callback_data="create_recurring")],
        [InlineKeyboardButton(text="Список событий", callback_data="list_recurring")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_reminders")],
    ])
    await callback.message.answer("Повторяющиеся события:", reply_markup=kb)
    await callback.answer()


class CreateRecurringEvent(StatesGroup):
    title = State()
    description = State()
    photo = State()
    day_of_week = State()
    time = State()
    confirm = State()


class EditRecurringEvent(StatesGroup):
    choose_field = State()
    edit_title = State()
    edit_desc = State()
    edit_photo = State()
    edit_day = State()
    edit_time = State()


@router.callback_query(F.data == "create_recurring")
async def create_recurring_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите название события:")
    await state.set_state(CreateRecurringEvent.title)
    await callback.answer()


@router.message(CreateRecurringEvent.title)
async def recurring_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(title=message.text)
    await message.answer("Введите описание (или 'пропустить'):")
    await state.set_state(CreateRecurringEvent.description)


@router.message(CreateRecurringEvent.description)
async def recurring_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    desc = message.text if message.text.lower() != "пропустить" else ""
    await state.update_data(description=desc)
    await message.answer("Отправьте фото для события (или 'пропустить'):")
    await state.set_state(CreateRecurringEvent.photo)


@router.message(CreateRecurringEvent.photo)
async def recurring_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.photo:
        await state.update_data(photo=message.photo[-1].file_id)
    else:
        await state.update_data(photo=None)

    days = "0 - Пн, 1 - Вт, 2 - Ср, 3 - Чт, 4 - Пт, 5 - Сб, 6 - Вс"
    await message.answer(f"День недели:\n{days}\n\nВведите число:")
    await state.set_state(CreateRecurringEvent.day_of_week)


@router.message(CreateRecurringEvent.day_of_week)
async def recurring_day(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        day = int(message.text)
        if day < 0 or day > 6:
            await message.answer("Введите число от 0 до 6:")
            return
    except ValueError:
        await message.answer("Введите число:")
        return

    await state.update_data(day_of_week=day)
    await message.answer("Введите время (ЧЧ:ММ), например 19:00:")
    await state.set_state(CreateRecurringEvent.time)


@router.message(CreateRecurringEvent.time)
async def recurring_time(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        hour, minute = message.text.split(":")
        hour = int(hour)
        minute = int(minute)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            await message.answer("Неверное время. Формат: ЧЧ:ММ")
            return
    except Exception:
        await message.answer("Неверный формат. Используйте ЧЧ:ММ:")
        return

    await state.update_data(hour=hour, minute=minute)

    data = await state.get_data()
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    photo_text = "да" if data.get('photo') else "нет"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_recurring"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_recurring"),
        ]
    ])
    await message.answer(
        f"Повторяющееся событие:\n\n"
        f"Название: {data['title']}\n"
        f"Описание: {data['description'] or 'нет'}\n"
        f"Фото: {photo_text}\n"
        f"День: {days[data['day_of_week']]}\n"
        f"Время: {data['hour']:02d}:{data['minute']:02d}\n\n"
        f"Создать?",
        reply_markup=kb
    )
    await state.set_state(CreateRecurringEvent.confirm)


@router.callback_query(F.data == "confirm_recurring", CreateRecurringEvent.confirm)
async def confirm_recurring(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()
    await create_recurring_event(
        chat_id=chat_id,
        title=data['title'],
        description=data['description'],
        day_of_week=data['day_of_week'],
        hour=data['hour'],
        minute=data['minute'],
        created_by=callback.from_user.id,
        photo=data.get('photo')
    )

    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    await state.clear()
    await callback.message.answer(
        f"Событие создано!\n"
        f"Каждый {days[data['day_of_week']]} в {data['hour']:02d}:{data['minute']:02d}"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_recurring")
async def cancel_recurring(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "list_recurring")
async def list_recurring(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    events = await get_recurring_events(chat_id)

    if not events:
        await callback.message.answer("Нет повторяющихся событий.")
        await callback.answer()
        return

    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    kb_buttons = []
    for e in events:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{e['title'][:25]} ({days[e['day_of_week']]} {e['hour']:02d}:{e['minute']:02d})",
                callback_data=f"edit_recurring_{e['id']}"
            ),
            InlineKeyboardButton(
                text="Удалить",
                callback_data=f"delete_recurring_{e['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="recurring_events")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Повторяющиеся события:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_recurring_"))
async def edit_recurring_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    event = await get_recurring_event(event_id)
    if not event:
        await callback.message.answer("Событие не найдено.")
        await callback.answer()
        return

    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    photo_text = "да" if event['photo'] else "нет"
    text = (
        f"Событие: {event['title']}\n"
        f"Описание: {event['description'] or 'нет'}\n"
        f"Фото: {photo_text}\n"
        f"День: {days[event['day_of_week']]}\n"
        f"Время: {event['hour']:02d}:{event['minute']:02d}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"ered_{event_id}_title")],
        [InlineKeyboardButton(text="Описание", callback_data=f"ered_{event_id}_desc")],
        [InlineKeyboardButton(text="Фото", callback_data=f"ered_{event_id}_photo")],
        [InlineKeyboardButton(text="День недели", callback_data=f"ered_{event_id}_day")],
        [InlineKeyboardButton(text="Время", callback_data=f"ered_{event_id}_time")],
        [InlineKeyboardButton(text="Назад", callback_data="list_recurring")],
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("ered_"))
async def edit_recurring_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    parts = callback.data.split("_")
    event_id = int(parts[1])
    field = parts[2]

    await state.update_data(event_id=event_id)

    if field == "title":
        await callback.message.answer("Введите новое название:")
        await state.set_state(EditRecurringEvent.edit_title)
    elif field == "desc":
        await callback.message.answer("Введите новое описание:")
        await state.set_state(EditRecurringEvent.edit_desc)
    elif field == "photo":
        await callback.message.answer("Отправьте новое фото (или 'удалить' чтобы убрать):")
        await state.set_state(EditRecurringEvent.edit_photo)
    elif field == "day":
        days = "0 - Пн, 1 - Вт, 2 - Ср, 3 - Чт, 4 - Пт, 5 - Сб, 6 - Вс"
        await callback.message.answer(f"День недели:\n{days}\n\nВведите число:")
        await state.set_state(EditRecurringEvent.edit_day)
    elif field == "time":
        await callback.message.answer("Введите время (ЧЧ:ММ):")
        await state.set_state(EditRecurringEvent.edit_time)

    await callback.answer()


@router.message(EditRecurringEvent.edit_title)
async def edit_recurring_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    await update_recurring_event(data['event_id'], title=message.text)
    await state.clear()
    await message.answer("Название обновлено!")


@router.message(EditRecurringEvent.edit_desc)
async def edit_recurring_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    desc = message.text if message.text.lower() != "удалить" else ""
    await update_recurring_event(data['event_id'], description=desc)
    await state.clear()
    await message.answer("Описание обновлено!")


@router.message(EditRecurringEvent.edit_photo)
async def edit_recurring_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    if message.photo:
        photo = message.photo[-1].file_id
    else:
        photo = None
    await update_recurring_event(data['event_id'], photo=photo)
    await state.clear()
    await message.answer("Фото обновлено!")


@router.message(EditRecurringEvent.edit_day)
async def edit_recurring_day(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        day = int(message.text)
        if day < 0 or day > 6:
            await message.answer("Введите число от 0 до 6:")
            return
    except ValueError:
        await message.answer("Введите число:")
        return

    data = await state.get_data()
    await update_recurring_event(data['event_id'], day_of_week=day)
    await state.clear()
    await message.answer("День обновлён!")


@router.message(EditRecurringEvent.edit_time)
async def edit_recurring_time(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        hour, minute = message.text.split(":")
        hour = int(hour)
        minute = int(minute)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            await message.answer("Неверное время. Формат: ЧЧ:ММ")
            return
    except Exception:
        await message.answer("Неверный формат. Используйте ЧЧ:ММ:")
        return

    data = await state.get_data()
    await update_recurring_event(data['event_id'], hour=hour, minute=minute)
    await state.clear()
    await message.answer("Время обновлено!")


@router.callback_query(F.data.startswith("delete_recurring_"))
async def delete_recurring_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    await delete_recurring_event(event_id)
    await callback.answer("Удалено!", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "create_reminder")
async def create_reminder_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer(
        "Введите текст напоминания:"
    )
    await state.set_state(CreateReminder.title)
    await callback.answer()


@router.message(CreateReminder.title)
async def reminder_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(title=message.text)
    await message.answer(
        "Когда напомнить? Формат: ДД.ММ ЧЧ:ММ\n"
        "Например: 15.06 19:00\n\n"
        "Или через一段时间:\n"
        "30м — через 30 минут\n"
        "1ч — через 1 час\n"
        "2д — через 2 дня"
    )
    await state.set_state(CreateReminder.remind_at)


@router.message(CreateReminder.remind_at)
async def reminder_time(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    from datetime import datetime, timedelta
    text = message.text.strip()
    now = datetime.now()

    try:
        if text.endswith("м"):
            minutes = int(text[:-1])
            remind_at = now + timedelta(minutes=minutes)
        elif text.endswith("ч"):
            hours = int(text[:-1])
            remind_at = now + timedelta(hours=hours)
        elif text.endswith("д"):
            days = int(text[:-1])
            remind_at = now + timedelta(days=days)
        else:
            day, time_part = text.split(" ")
            hour, minute = time_part.split(":")
            remind_at = datetime(now.year, now.month, int(day), int(hour), int(minute))
            if remind_at < now:
                remind_at = remind_at + timedelta(days=1)
    except Exception:
        await message.answer("Неверный формат. Попробуйте снова:")
        return

    await state.update_data(remind_at=remind_at.strftime('%Y-%m-%d %H:%M:%S'))

    data = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_reminder"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_reminder"),
        ]
    ])
    await message.answer(
        f"Напоминание:\n\n"
        f"Текст: {data['title']}\n"
        f"Когда: {remind_at.strftime('%d.%m %H:%M')}\n\n"
        f"Создать?",
        reply_markup=kb
    )
    await state.set_state(CreateReminder.confirm)


@router.callback_query(F.data == "confirm_reminder", CreateReminder.confirm)
async def confirm_reminder(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()
    await add_reminder(
        chat_id=chat_id,
        title=data['title'],
        remind_at=data['remind_at'],
        created_by=callback.from_user.id
    )

    await state.clear()
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "cancel_reminder")
async def cancel_reminder(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.answer("Отменено", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "list_reminders")
async def list_reminders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    from database import get_active_reminders
    reminders = await get_active_reminders(chat_id)

    if not reminders:
        await callback.message.answer("Нет активных напоминаний.")
        await callback.answer()
        return

    kb_buttons = []
    for r in reminders:
        from datetime import datetime
        dt = datetime.fromisoformat(r['remind_at'])
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{r['title'][:30]} ({dt.strftime('%d.%m %H:%M')})",
                callback_data=f"drd{r['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_reminders")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Активные напоминания:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_reminder_"))
async def delete_reminder_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    reminder_id = int(callback.data.split("_")[2])
    await delete_reminder(reminder_id)
    await callback.message.edit_text("Напоминание удалено.")
    await callback.answer()


@router.callback_query(F.data.startswith("drd"))
async def reminder_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    reminder_id = int(callback.data[3:])

    from database import aiosqlite, DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        r = await cursor.fetchone()

    if not r:
        await callback.answer("Напоминание не найдено!")
        return

    from datetime import datetime
    dt = datetime.fromisoformat(r['remind_at'])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_reminder_{r['id']}")]
    ])

    await callback.message.edit_text(
        f"Напоминание:\n\n"
        f"Текст: {r['title']}\n"
        f"Когда: {dt.strftime('%d.%m %H:%M')}\n"
        f"Статус: ожидает",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "admin_manual")
async def admin_manual(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    text = (
        "Мануал бота\n\n"

        "ПЕРВЫЙ ШАГ\n"
        "1. Добавьте бота в группу\n"
        "2. Напишите /setchat в группе\n"
        "3. Бот запомнит чат для публикаций\n\n"

        "КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ\n"
        "/start — главное меню\n"
        "/help — помощь\n"
        "/profile — свой профиль (или ответом на сообщение — профиль другого)\n"
        "/leaderboard — топ по ELO\n"
        "/top — топ по ELO (альт.)\n"
        "/mystats — подробная статистика\n"
        "/tournament_stats — статистика турниров\n"
        "/clans — список кланов\n"
        "/clan — создать клан\n"
        "/clan_join — вступить в клан\n"
        "/clan_leave — покинуть клан\n"
        "/events — список событий\n"
        "/polls — активные голосования\n"
        "/tournaments — список турниров\n"
        "/quiz — викторина (+20 монет)\n\n"

        "МОНЕТЫ\n"
        "/daily — ежедневный бонус +50\n"
        "/balance — баланс монет\n"
        "/coins — помощь по монетам\n"
        "/bet [сумма] [match_id] [user_id] — ставка\n"
        "/coins_top — топ богачей\n\n"

        "АДМИН-КОМАНДЫ\n"
        "/admin — панель администратора\n"
        "/setchat — настроить чат для публикаций\n"
        "/backup — бэкап БД\n"
        "/restore — восстановить БД\n\n"

        "АДМИН: ПАНЕЛЬ\n"
        "События — создание и управление событиями с фото\n"
        "Голосования — опросы с вариантами и фото\n"
        "Турниры — создание, сетка, поединки, ELO\n"
        "Напоминания — отложенные и повторяющиеся\n"
        "Викторины — добавление вопросов\n"
        "Рассылка — сообщения всем пользователям\n"
        "Статистика — аналитика бота\n"
        "Утихомирить — мут с таймером\n"
        "Созвать всех — упомянуть всех\n\n"

        "МОДЕРАЦИЯ\n"
        "Мут на 30м/1ч/3ч/6ч/12ч/24ч\n"
        "Бесконечный мут\n"
        "Снять мут\n"
        "Созвать всех участников"
    )
    await callback.message.answer(text, reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_events")
async def admin_events(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать событие", callback_data="create_event")],
        [InlineKeyboardButton(text="Список событий", callback_data="list_events")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
    ])

    await callback.message.answer("Управление событиями:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin_polls")
async def admin_polls(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать голосование", callback_data="create_poll")],
        [InlineKeyboardButton(text="Активные голосования", callback_data="list_polls")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
    ])

    await callback.message.answer("Управление голосованиями:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin_tournaments")
async def admin_tournaments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать турнир", callback_data="create_tournament")],
        [InlineKeyboardButton(text="Активные турниры", callback_data="list_tournaments")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
    ])

    await callback.message.answer("Управление турнирами:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer(
        "Панель администратора",
        reply_markup=admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "create_event")
async def start_create_event(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите название события:")
    await state.set_state(CreateEvent.title)
    await callback.answer()


@router.message(CreateEvent.title)
async def event_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(title=message.text)
    await message.answer("Введите описание события:")
    await state.set_state(CreateEvent.description)


@router.message(CreateEvent.description)
async def event_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(description=message.text)
    await message.answer("Введите дату и время (например: 15.07.2026 19:00):")
    await state.set_state(CreateEvent.event_date)


@router.message(CreateEvent.event_date)
async def event_date(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(event_date=message.text)
    await message.answer(
        "Отправьте изображение для поста или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_event_image")]
        ])
    )
    await state.set_state(CreateEvent.image)


@router.callback_query(F.data == "skip_event_image", CreateEvent.image)
async def skip_event_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Пропускаю изображение...")
    await show_event_preview(callback, state)
    await callback.answer()


@router.message(CreateEvent.image, F.photo)
async def event_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await message.answer("Изображение добавлено!")
    await show_event_preview(message, state)


async def show_event_preview(message_or_callback, state: FSMContext):
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Редактировать название", callback_data="edit_event_title"),
            InlineKeyboardButton(text="Редактировать описание", callback_data="edit_event_desc"),
        ],
        [
            InlineKeyboardButton(text="Редактировать дату", callback_data="edit_event_date"),
            InlineKeyboardButton(text="Изображение", callback_data="edit_event_image"),
        ],
        [
            InlineKeyboardButton(text="Опубликовать", callback_data="confirm_event"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_event"),
        ]
    ])

    text = (
        f"Предпросмотр события:\n\n"
        f"Название: {data['title']}\n"
        f"Описание: {data['description']}\n"
        f"Дата: {data['event_date']}\n"
        f"Изображение: {'да' if data.get('image_file_id') else 'нет'}\n\n"
        f"Нажмите 'Опубликовать' или отредактируйте."
    )

    if isinstance(message_or_callback, Message):
        if data.get('image_file_id'):
            await message_or_callback.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=kb
            )
        else:
            await message_or_callback.answer(text, reply_markup=kb)
    else:
        if data.get('image_file_id'):
            await message_or_callback.message.delete()
            await message_or_callback.message.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=kb
            )
        else:
            await message_or_callback.message.edit_text(text, reply_markup=kb)

    await state.set_state(CreateEvent.confirm)


@router.callback_query(F.data == "edit_event_image", CreateEvent.confirm)
async def edit_event_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer(
        "Отправьте новое изображение или нажмите 'Удалить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Удалить изображение", callback_data="remove_event_image")]
        ])
    )
    await state.set_state(CreateEvent.editing)
    await state.update_data(edit_field="image")
    await callback.answer()


@router.callback_query(F.data == "remove_event_image", CreateEvent.editing)
async def remove_event_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(image_file_id=None)
    await callback.answer("Удалено!", show_alert=True)
    await callback.message.delete()
    await show_event_preview(callback, state)
    await callback.answer()


@router.message(CreateEvent.editing, F.photo)
async def event_editing_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await message.answer("Изображение обновлено!")
    await show_event_preview(message, state)


@router.callback_query(F.data == "edit_event_title", CreateEvent.confirm)
async def edit_event_title(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новое название:")
    await state.set_state(CreateEvent.editing)
    await state.update_data(edit_field="title")
    await callback.answer()


@router.callback_query(F.data == "edit_event_desc", CreateEvent.confirm)
async def edit_event_desc(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новое описание:")
    await state.set_state(CreateEvent.editing)
    await state.update_data(edit_field="description")
    await callback.answer()


@router.callback_query(F.data == "edit_event_date", CreateEvent.confirm)
async def edit_event_date(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новую дату:")
    await state.set_state(CreateEvent.editing)
    await state.update_data(edit_field="event_date")
    await callback.answer()


@router.message(CreateEvent.editing)
async def event_editing_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    field = data['edit_field']
    await state.update_data(**{field: message.text})
    await show_event_preview(message, state)


@router.callback_query(F.data == "confirm_event", CreateEvent.confirm)
async def confirm_event(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()

    event_id = await add_event(
        title=data['title'],
        description=data['description'],
        event_date=data['event_date'],
        created_by=callback.from_user.id,
        chat_id=chat_id,
        image_file_id=data.get('image_file_id')
    )

    poll_id = await add_poll(
        question=f"Голосование: {data['title']}?",
        options=["Буду участвовать", "Не смогу", "Посмотрю"],
        poll_type="event",
        created_by=callback.from_user.id,
        chat_id=chat_id,
        event_id=event_id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Буду участвовать", callback_data=f"vote_{poll_id}_0")],
        [InlineKeyboardButton(text="Не смогу", callback_data=f"vote_{poll_id}_1")],
        [InlineKeyboardButton(text="Посмотрю", callback_data=f"vote_{poll_id}_2")],
    ])

    text = (
        f"{data['title']}\n\n"
        f"{data['description']}\n\n"
        f"Дата: {data['event_date']}"
    )

    if data.get('image_file_id'):
        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=data['image_file_id'],
            caption=text,
            reply_markup=kb
        )
    else:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb
        )

    await update_event_message_id(event_id, msg.message_id)

    await state.clear()
    await callback.answer("Опубликовано!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data == "cancel_event")
async def cancel_event(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.answer("Отменено", show_alert=True)
    await callback.message.delete()
    await callback.answer()



    await callback.answer("Голос записан!")


@router.callback_query(F.data == "list_events")
async def list_events(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    events = await get_events(chat_id) if chat_id else []

    if not events:
        await callback.message.answer("Нет событий.")
        await callback.answer()
        return

    kb_buttons = []
    for event in events:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"Голоса: {event['title'][:25]}",
                callback_data=f"view_event_votes_{event['id']}"
            ),
            InlineKeyboardButton(
                text=f"Удалить",
                callback_data=f"delete_event_{event['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_events")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("События:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("view_event_votes_"))
async def view_event_votes_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    event_id = int(callback.data.split("_")[3])
    event = await get_event(event_id)
    if not event:
        await callback.answer("Событие не найдено!", show_alert=True)
        return

    event_poll = await get_event_poll(event_id)
    if not event_poll:
        await callback.message.answer("Голосование ещё не начато.")
        await callback.answer()
        return

    votes = await get_poll_votes(event_poll['id'])
    if not votes:
        await callback.message.answer("Пока никто не проголосовал.")
        await callback.answer()
        return

    options = event_poll['options'].split("|")
    votes_by_option = {}
    for v in votes:
        idx = v['option_index']
        if idx not in votes_by_option:
            votes_by_option[idx] = []
        votes_by_option[idx].append(v['user_id'])

    text = f"Голосование по событию: {event['title']}\n\n"

    for i, opt in enumerate(options):
        voters = votes_by_option.get(i, [])
        text += f"📌 {opt} ({len(voters)}):\n"
        if voters:
            for uid in voters:
                text += f'  • <a href="tg://user?id={uid}">{uid}</a>\n'
        else:
            text += "  — никто\n"
        text += "\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="list_events")]
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    await delete_event(event_id)
    await callback.answer("Удалено!", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "create_poll")
async def start_create_poll(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За следующее событие", callback_data="poll_type_event")],
        [InlineKeyboardButton(text="За время проведения", callback_data="poll_type_time")],
        [InlineKeyboardButton(text="Общее голосование", callback_data="poll_type_general")],
    ])

    await callback.message.answer("Выберите тип голосования:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("poll_type_"))
async def select_poll_type(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    poll_type = callback.data.split("_")[2]
    await state.update_data(poll_type=poll_type)

    type_names = {
        "event": "за следующее событие",
        "time": "за время проведения",
        "general": "общее"
    }

    await callback.message.answer(f"Введите вопрос ({type_names[poll_type]}):")
    await state.set_state(CreatePoll.question)
    await callback.answer()


@router.message(CreatePoll.question)
async def poll_question(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(question=message.text)
    await message.answer("Введите варианты (каждый с новой строки, минимум 2):")
    await state.set_state(CreatePoll.options)


@router.message(CreatePoll.options)
async def poll_options(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    options = [opt.strip() for opt in message.text.split("\n") if opt.strip()]

    if len(options) < 2:
        await message.answer("Нужно минимум 2 варианта:")
        return

    if len(options) > 10:
        await message.answer("Максимум 10 вариантов:")
        return

    await state.update_data(options=options)
    data = await state.get_data()

    await message.answer(
        "Отправьте изображение для поста или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_poll_image")]
        ])
    )
    await state.set_state(CreatePoll.image)


@router.callback_query(F.data == "skip_poll_image", CreatePoll.image)
async def skip_poll_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Пропускаю изображение...")
    await show_poll_preview(callback, state)
    await callback.answer()


@router.message(CreatePoll.image, F.photo)
async def poll_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await message.answer("Изображение добавлено!")
    await show_poll_preview(message, state)


async def show_poll_preview(message_or_callback, state: FSMContext):
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Редактировать вопрос", callback_data="edit_poll_question"),
            InlineKeyboardButton(text="Редактировать варианты", callback_data="edit_poll_options"),
        ],
        [
            InlineKeyboardButton(text="Изображение", callback_data="edit_poll_image"),
        ],
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_poll"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_poll"),
        ]
    ])

    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(data['options'])])
    text = (
        f"Предпросмотр опроса:\n\n"
        f"Вопрос: {data['question']}\n\n"
        f"Варианты:\n{options_text}\n\n"
        f"Изображение: {'да' if data.get('image_file_id') else 'нет'}"
    )

    if isinstance(message_or_callback, Message):
        if data.get('image_file_id'):
            await message_or_callback.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=kb
            )
        else:
            await message_or_callback.answer(text, reply_markup=kb)
    else:
        if data.get('image_file_id'):
            await message_or_callback.message.delete()
            await message_or_callback.message.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=kb
            )
        else:
            await message_or_callback.message.edit_text(text, reply_markup=kb)

    await state.set_state(CreatePoll.confirm)


@router.callback_query(F.data == "edit_poll_question", CreatePoll.confirm)
async def edit_poll_question(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новый вопрос:")
    await state.set_state(CreatePoll.editing)
    await state.update_data(edit_field="question")
    await callback.answer()


@router.callback_query(F.data == "edit_poll_options", CreatePoll.confirm)
async def edit_poll_options(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новые варианты (каждый с новой строки, минимум 2):")
    await state.set_state(CreatePoll.editing)
    await state.update_data(edit_field="options")
    await callback.answer()


@router.message(CreatePoll.editing, F.text)
async def poll_editing_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    field = data['edit_field']

    if field == "question":
        await state.update_data(question=message.text)
    elif field == "options":
        options = [opt.strip() for opt in message.text.split("\n") if opt.strip()]
        if len(options) < 2:
            await message.answer("Нужно минимум 2 варианта:")
            return
        if len(options) > 10:
            await message.answer("Максимум 10 вариантов:")
            return
        await state.update_data(options=options)

    await message.answer("Обновлено!")
    await show_poll_preview(message, state)


@router.callback_query(F.data == "edit_poll_image", CreatePoll.confirm)
async def edit_poll_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer(
        "Отправьте новое изображение или нажмите 'Удалить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Удалить изображение", callback_data="remove_poll_image")]
        ])
    )
    await state.set_state(CreatePoll.editing)
    await state.update_data(edit_field="image")
    await callback.answer()


@router.callback_query(F.data == "remove_poll_image", CreatePoll.editing)
async def remove_poll_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(image_file_id=None)
    await callback.answer("Удалено!", show_alert=True)
    await callback.message.delete()
    await show_poll_preview(callback, state)
    await callback.answer()


@router.message(CreatePoll.editing, F.photo)
async def poll_editing_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await message.answer("Изображение обновлено!")
    await show_poll_preview(message, state)


@router.callback_query(F.data == "confirm_poll", CreatePoll.confirm)
async def confirm_poll(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()

    poll_id = await add_poll(
        question=data['question'],
        options=data['options'],
        poll_type=data['poll_type'],
        created_by=callback.from_user.id,
        chat_id=chat_id,
        image_file_id=data.get('image_file_id')
    )

    kb_buttons = []
    for i, opt in enumerate(data['options']):
        kb_buttons.append([InlineKeyboardButton(text=opt, callback_data=f"vote_{poll_id}_{i}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    text = f"Голосование: {data['question']}"

    if data.get('image_file_id'):
        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=data['image_file_id'],
            caption=text,
            reply_markup=kb
        )
    else:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb
        )

    await update_poll_message_id(poll_id, msg.message_id)

    await state.clear()
    await callback.answer("Опубликовано!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data == "cancel_poll")
async def cancel_poll(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.answer("Отменено", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("vote_") & ~F.data.startswith("vote_event_"))
async def handle_vote(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    poll_id = int(parts[1])
    option_index = int(parts[2])

    success = await vote(poll_id, callback.from_user.id, option_index)

    if not success:
        await callback.answer("Вы уже голосовали!", show_alert=True)
        return

    poll = await get_poll(poll_id)
    if not poll:
        await callback.answer("Голосование не найдено!", show_alert=True)
        return

    options = poll['options'].split("|")
    kb_buttons = []
    for i, opt in enumerate(options):
        kb_buttons.append([InlineKeyboardButton(text=opt, callback_data=f"vote_{poll_id}_{i}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    results = await get_poll_results(poll_id)
    results_dict = {r[0]: r[1] for r in results}
    total = sum(results_dict.values())

    results_text = "\n".join([
        f"{opt}: {results_dict.get(i, 0)} голосов ({results_dict.get(i, 0) * 100 // max(total, 1)}%)"
        for i, opt in enumerate(options)
    ])

    await callback.message.edit_text(
        f"Голосование: {poll['question']}\n\nРезультаты:\n{results_text}\n\nВсего: {total}",
        reply_markup=kb
    )
    await callback.answer("Голос записан!")

    user = callback.from_user
    name = user.first_name or user.username or str(user.id)
    link = f"<a href=\"tg://user?id={user.id}\">{name}</a>"
    voted_option = options[option_index]
    poll_question = poll['question']
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"{link} отдал голос за <b>{voted_option}</b> в голосовании <b>{poll_question}</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "list_polls")
async def list_polls(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    polls = await get_active_polls(chat_id)

    if not polls:
        await callback.message.answer("Нет активных голосований.")
        await callback.answer()
        return

    kb_buttons = []
    for poll in polls:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"Кто голосовал: {poll['question'][:25]}",
                callback_data=f"view_votes_{poll['id']}"
            ),
            InlineKeyboardButton(
                text=f"Закрыть",
                callback_data=f"close_poll_{poll['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_polls")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Голосования:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("view_votes_"))
async def view_votes_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    poll_id = int(callback.data.split("_")[2])
    poll = await get_poll(poll_id)
    if not poll:
        await callback.answer("Голосование не найдено!", show_alert=True)
        return

    options = poll['options'].split("|")
    votes = await get_poll_votes(poll_id)

    if not votes:
        await callback.message.answer("Пока никто не проголосовал.")
        await callback.answer()
        return

    votes_by_option = {}
    for v in votes:
        idx = v['option_index']
        if idx not in votes_by_option:
            votes_by_option[idx] = []
        votes_by_option[idx].append(v['user_id'])

    text = f"Голосование: {poll['question']}\n\n"

    for i, opt in enumerate(options):
        voters = votes_by_option.get(i, [])
        text += f"📌 {opt} ({len(voters)}):\n"
        if voters:
            for uid in voters:
                text += f'  • <a href="tg://user?id={uid}">{uid}</a>\n'
        else:
            text += "  — никто\n"
        text += "\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="list_polls")]
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("close_poll_"))
async def close_poll_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    poll_id = int(callback.data.split("_")[2])
    await close_poll(poll_id)
    await callback.message.answer("Голосование закрыто.")
    await callback.answer()


@router.callback_query(F.data == "mute_menu")
async def mute_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="30 минут", callback_data="mute_30")],
        [InlineKeyboardButton(text="1 час", callback_data="mute_60")],
        [InlineKeyboardButton(text="3 часа", callback_data="mute_180")],
        [InlineKeyboardButton(text="6 часов", callback_data="mute_360")],
        [InlineKeyboardButton(text="12 часов", callback_data="mute_720")],
        [InlineKeyboardButton(text="24 часа", callback_data="mute_1440")],
        [InlineKeyboardButton(text="До моего снятия", callback_data="mute_infinite")],
        [InlineKeyboardButton(text="Снять мут со всех", callback_data="unmute_all")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
    ])

    await callback.message.answer("Настройка мута:", reply_markup=kb)
    await callback.answer()


async def do_mute(bot: Bot, chat_id: int, until_date=None):
    muted_count = 0
    members = await get_chat_members(chat_id)

    for member in members:
        if member['user_id'] == ADMIN_ID:
            continue

        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member['user_id'],
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            muted_count += 1
        except Exception:
            continue

    return muted_count


async def do_unmute(bot: Bot, chat_id: int):
    unmuted_count = 0
    members = await get_chat_members(chat_id)

    for member in members:
        if member['user_id'] == ADMIN_ID:
            continue

        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member['user_id'],
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                )
            )
            unmuted_count += 1
        except Exception:
            continue

    return unmuted_count


@router.callback_query(F.data.startswith("mute_") & ~F.data.startswith("mute_menu"))
async def mute_with_timer(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    minutes = int(callback.data.split("_")[1])
    until_date = datetime.now() + timedelta(minutes=minutes)

    muted_count = await do_mute(bot, chat_id, until_date)

    timer_text = {
        30: "30 минут", 60: "1 час", 180: "3 часа",
        360: "6 часов", 720: "12 часов", 1440: "24 часа"
    }.get(minutes, f"{minutes} минут")

    await callback.message.answer(f"Утихомирены: {muted_count} участников на {timer_text}.")
    await callback.answer()


@router.callback_query(F.data == "mute_infinite")
async def mute_infinite(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    muted_count = await do_mute(bot, chat_id, until_date=None)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Снять мут со всех", callback_data="unmute_all")]
    ])

    await callback.message.answer(
        f"Утихомирены: {muted_count} участников (до снятия).\n\n"
        f"Нажмите кнопку ниже чтобы снять мут.",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "unmute_all")
async def unmute_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    unmuted_count = await do_unmute(bot, chat_id)

    await callback.message.answer(f"Голос возвращен: {unmuted_count} участникам.")
    await callback.answer()


@router.callback_query(F.data == "summon_all")
async def summon_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    members = await get_chat_members(chat_id)

    if not members:
        await callback.message.answer("Нет участников.")
        await callback.answer()
        return

    mentions = []
    for m in members[:50]:
        name = m['display_name'] or m['username'] or str(m['user_id'])
        mentions.append(f'<a href="tg://user?id={m["user_id"]}">{name}</a>')

    await bot.send_message(
        chat_id=chat_id,
        text=f"Созыв!\n\n{' '.join(mentions)}\n\nПриглашаем принять участие!",
        parse_mode="HTML"
    )
    await callback.message.answer("Созваны все участники!")
    await callback.answer()


@router.callback_query(F.data == "create_tournament")
async def start_create_tournament(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите название турнира:")
    await state.set_state(CreateTournament.name)
    await callback.answer()


@router.message(CreateTournament.name)
async def tournament_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(name=message.text)
    await message.answer("Введите описание турнира:")
    await state.set_state(CreateTournament.description)


@router.message(CreateTournament.description)
async def tournament_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(description=message.text)
    await message.answer("Макс. участников (4, 8, 16, 32):")
    await state.set_state(CreateTournament.max_participants)


@router.message(CreateTournament.max_participants)
async def tournament_max_participants(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        max_p = int(message.text)
        if max_p not in [4, 8, 16, 32]:
            await message.answer("Допустимые значения: 4, 8, 16, 32:")
            return
    except ValueError:
        await message.answer("Введите число:")
        return

    await state.update_data(max_participants=max_p)
    await message.answer(
        "Выберите количество призовых мест:\n\n"
        "1 — Только победитель\n"
        "3 — Три призовых места\n"
        "5 — Пять призовых мест\n\n"
        "Введите число или нажмите кнопку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Только победитель", callback_data="prize_1")],
            [InlineKeyboardButton(text="Три призовых места", callback_data="prize_3")],
            [InlineKeyboardButton(text="Пять призовых мест", callback_data="prize_5")],
        ])
    )
    await state.set_state(CreateTournament.prize_places)


@router.callback_query(F.data.startswith("prize_"), CreateTournament.prize_places)
async def tournament_prize_places(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    prize_places = int(callback.data.split("_")[1])
    await state.update_data(prize_places=prize_places, participation_award=0)

    await callback.message.answer(
        "Отправьте изображение для поста или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_tourney_image")]
        ])
    )
    await state.set_state(CreateTournament.image)
    await callback.answer()


@router.message(CreateTournament.prize_places)
async def tournament_prize_places_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        prize_places = int(message.text)
        if prize_places < 1 or prize_places > 10:
            await message.answer("Введите число от 1 до 10:")
            return
    except ValueError:
        await message.answer("Введите число:")
        return

    await state.update_data(prize_places=prize_places, participation_award=0)

    await message.answer(
        "Отправьте изображение для поста или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_tourney_image")]
        ])
    )
    await state.set_state(CreateTournament.image)


@router.callback_query(F.data == "skip_tourney_image", CreateTournament.image)
async def skip_tourney_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Пропускаю изображение...")
    await show_tournament_preview(callback, state)
    await callback.answer()


@router.message(CreateTournament.image, F.photo)
async def tournament_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await message.answer("Изображение добавлено!")
    await show_tournament_preview(message, state)


async def show_tournament_preview(message_or_callback, state: FSMContext):
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Редактировать название", callback_data="edit_tourney_name"),
            InlineKeyboardButton(text="Редактировать описание", callback_data="edit_tourney_desc"),
        ],
        [
            InlineKeyboardButton(text="Редактировать макс.", callback_data="edit_tourney_max"),
            InlineKeyboardButton(text="Изображение", callback_data="edit_tourney_image"),
        ],
        [
            InlineKeyboardButton(text="Опубликовать", callback_data="confirm_tournament"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_tournament"),
        ]
    ])

    text = (
        f"Предпросмотр турнира:\n\n"
        f"Название: {data['name']}\n"
        f"Описание: {data['description']}\n"
        f"Макс. участников: {data['max_participants']}\n"
        f"Призовых мест: {data.get('prize_places', 1)}\n"
        f"Изображение: {'да' if data.get('image_file_id') else 'нет'}\n\n"
        f"Нажмите 'Опубликовать' или отредактируйте."
    )

    if isinstance(message_or_callback, Message):
        if data.get('image_file_id'):
            await message_or_callback.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=kb
            )
        else:
            await message_or_callback.answer(text, reply_markup=kb)
    else:
        if data.get('image_file_id'):
            await message_or_callback.message.delete()
            await message_or_callback.message.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=kb
            )
        else:
            await message_or_callback.message.edit_text(text, reply_markup=kb)

    await state.set_state(CreateTournament.confirm)


@router.callback_query(F.data == "edit_tourney_image", CreateTournament.confirm)
async def edit_tourney_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer(
        "Отправьте новое изображение или нажмите 'Удалить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Удалить изображение", callback_data="remove_tourney_image")]
        ])
    )
    await state.set_state(CreateTournament.editing)
    await state.update_data(edit_field="image")
    await callback.answer()


@router.callback_query(F.data == "remove_tourney_image", CreateTournament.editing)
async def remove_tourney_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.update_data(image_file_id=None)
    await callback.answer("Удалено!", show_alert=True)
    await callback.message.delete()
    await show_tournament_preview(callback, state)
    await callback.answer()


@router.message(CreateTournament.editing, F.photo)
async def tournament_editing_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo = message.photo[-1]
    await state.update_data(image_file_id=photo.file_id)
    await message.answer("Изображение обновлено!")
    await show_tournament_preview(message, state)


@router.callback_query(F.data == "edit_tourney_name", CreateTournament.confirm)
async def edit_tourney_name(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новое название:")
    await state.set_state(CreateTournament.editing)
    await state.update_data(edit_field="name")
    await callback.answer()


@router.callback_query(F.data == "edit_tourney_desc", CreateTournament.confirm)
async def edit_tourney_desc(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите новое описание:")
    await state.set_state(CreateTournament.editing)
    await state.update_data(edit_field="description")
    await callback.answer()


@router.callback_query(F.data == "edit_tourney_max", CreateTournament.confirm)
async def edit_tourney_max(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите макс. участников (4, 8, 16, 32):")
    await state.set_state(CreateTournament.editing)
    await state.update_data(edit_field="max_participants")
    await callback.answer()


@router.message(CreateTournament.editing)
async def tournament_editing_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    field = data['edit_field']

    if field == "max_participants":
        try:
            value = int(message.text)
            if value not in [4, 8, 16, 32]:
                await message.answer("Допустимые значения: 4, 8, 16, 32:")
                return
        except ValueError:
            await message.answer("Введите число:")
            return
    else:
        value = message.text

    await state.update_data(**{field: value})
    await show_tournament_preview(message, state)


@router.callback_query(F.data == "confirm_tournament", CreateTournament.confirm)
async def confirm_tournament(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()

    tournament_id = await create_tournament(
        name=data['name'],
        description=data['description'],
        max_participants=data['max_participants'],
        created_by=callback.from_user.id,
        chat_id=chat_id,
        image_file_id=data.get('image_file_id'),
        prize_places=data.get('prize_places', 1),
        participation_award=data.get('participation_award', 0)
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Записаться", callback_data=f"join_tournament_{tournament_id}")]
    ])

    prize_text = ""
    prize_places = data.get('prize_places', 1)
    if prize_places == 1:
        prize_text = "Приз: победитель"
    else:
        prize_text = f"Призовых мест: {prize_places}"

    text = (
        f"{data['name']}\n\n"
        f"{data['description']}\n\n"
        f"Макс. участников: {data['max_participants']}\n"
        f"{prize_text}\n\n"
        f"Записывайтесь!"
    )

    if data.get('image_file_id'):
        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=data['image_file_id'],
            caption=text,
            reply_markup=kb
        )
    else:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb
        )

    await update_tournament_message_id(tournament_id, msg.message_id)

    await state.clear()
    await callback.answer("Опубликовано!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data == "cancel_tournament")
async def cancel_tournament(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.answer("Отменено", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "list_tournaments")
async def list_tournaments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    tournaments = await get_active_tournaments(chat_id) if chat_id else []

    if not tournaments:
        await callback.message.answer("Нет активных турниров.")
        await callback.answer()
        return

    kb_buttons = []
    for t in tournaments:
        count = await get_participant_count(t['id'])
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{t['name']} ({count}/{t['max_participants']})",
                callback_data=f"tournament_details_{t['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_tournaments")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Турниры:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("tournament_details_"))
async def tournament_details(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    tournament = await get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    participants = await get_tournament_participants(tournament_id)
    count = len(participants)

    text = (
        f"Турнир: {tournament['name']}\n"
        f"Описание: {tournament['description']}\n"
        f"Участники: {count}/{tournament['max_participants']}\n"
        f"Статус: {tournament['status']}\n\n"
    )

    if participants:
        text += "Участники:\n"
        for i, p in enumerate(participants, 1):
            name = p['display_name'] or str(p['user_id'])
            if p['username']:
                name += f" (@{p['username']})"
            text += f"{i}. {name}\n"
    else:
        text += "Пока нет участников.\n"

    kb_buttons = []

    if tournament['status'] == 'registration':
        kb_buttons.append([InlineKeyboardButton(text="Начать турнир", callback_data=f"start_tournament_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Удалить", callback_data=f"delete_tournament_{tournament_id}")])
    elif tournament['status'] == 'in_progress':
        kb_buttons.append([InlineKeyboardButton(text="Автосетка", callback_data=f"auto_bracket_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Создать поединок", callback_data=f"create_match_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Результаты", callback_data=f"match_list_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Сетка", callback_data=f"standings_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Завершить", callback_data=f"finish_tournament_{tournament_id}")])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="list_tournaments")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("auto_bracket_"))
async def auto_bracket_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    tournament_id = int(callback.data.split("_")[2])

    from database import auto_generate_bracket
    matches, error = await auto_generate_bracket(tournament_id)

    if error:
        await callback.message.answer(error)
        await callback.answer()
        return

    participants = await get_tournament_participants(tournament_id)
    tournament = await get_tournament(tournament_id)

    text = f"Сетка турнира \"{tournament['name']}\":\n\n"

    all_matches = await get_tournament_matches(tournament_id)
    for m in all_matches:
        p1_name = str(m['player1_id'])
        p2_name = str(m['player2_id']) if m['player2_id'] else "BYE"
        for p in participants:
            if p['user_id'] == m['player1_id']:
                p1_name = p['display_name'] or p['username'] or str(p['user_id'])
            if m['player2_id'] and p['user_id'] == m['player2_id']:
                p2_name = p['display_name'] or p['username'] or str(p['user_id'])
        status = "✅" if m['winner_id'] else "⏳"
        text += f"{status} Раунд {m['round_num']}: {p1_name} vs {p2_name}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Опубликовать в чат", callback_data=f"publish_bracket_{tournament_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"tournament_details_{tournament_id}")],
    ])

    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("publish_bracket_"))
async def publish_bracket(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат!")
        await callback.answer()
        return

    tournament_id = int(callback.data.split("_")[2])
    participants = await get_tournament_participants(tournament_id)
    tournament = await get_tournament(tournament_id)
    all_matches = await get_tournament_matches(tournament_id)

    text = f"Сетка турнира \"{tournament['name']}\":\n\n"
    for m in all_matches:
        p1_name = str(m['player1_id'])
        p2_name = str(m['player2_id']) if m['player2_id'] else "BYE"
        p1_id = m['player1_id']
        p2_id = m['player2_id']
        for p in participants:
            if p['user_id'] == m['player1_id']:
                p1_name = p['display_name'] or p['username'] or str(p['user_id'])
            if m['player2_id'] and p['user_id'] == m['player2_id']:
                p2_name = p['display_name'] or p['username'] or str(p['user_id'])
        p1_link = f'<a href="tg://user?id={p1_id}">{p1_name}</a>'
        p2_link = f'<a href="tg://user?id={p2_id}">{p2_name}</a>' if p2_id else "BYE"
        text += f"Раунд {m['round_num']}: {p1_link} vs {p2_link}\n"

    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    await callback.answer("Опубликовано!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data.startswith("start_tournament_"))
async def start_tournament_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    tournament_id = int(callback.data.split("_")[2])
    count = await get_participant_count(tournament_id)

    if count < 2:
        await callback.answer("Нужно минимум 2 участника!", show_alert=True)
        return

    await start_tournament(tournament_id)
    tournament = await get_tournament(tournament_id)
    participants = await get_tournament_participants(tournament_id)

    mentions = ", ".join([
        f"[{p['display_name'] or p['username'] or str(p['user_id'])}](tg://user?id={p['user_id']})"
        for p in participants
    ])

    await bot.send_message(
        chat_id=chat_id,
        text=f"Турнир \"{tournament['name']}\" начат!\n\nУчастники: {mentions}",
        parse_mode="Markdown"
    )
    await callback.answer("Турнир начат!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data.startswith("delete_tournament_"))
async def delete_tournament_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    await delete_tournament(tournament_id)
    await callback.answer("Удалено!", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("create_match_"))
async def start_create_match(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    participants = await get_tournament_participants(tournament_id)

    if len(participants) < 2:
        await callback.answer("Нужно минимум 2 участника!", show_alert=True)
        return

    await state.update_data(tournament_id=tournament_id)

    kb_buttons = []
    for p in participants:
        name = p['display_name'] or p['username'] or str(p['user_id'])
        kb_buttons.append([InlineKeyboardButton(text=name, callback_data=f"select_p1_{p['user_id']}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Выберите первого бойца:", reply_markup=kb)
    await state.set_state(CreateMatch.player1)
    await callback.answer()


@router.callback_query(F.data.startswith("select_p1_"))
async def select_player1(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    player1_id = int(callback.data.split("_")[2])
    await state.update_data(player1_id=player1_id)

    data = await state.get_data()
    participants = await get_tournament_participants(data['tournament_id'])

    kb_buttons = []
    for p in participants:
        if p['user_id'] != player1_id:
            name = p['display_name'] or p['username'] or str(p['user_id'])
            kb_buttons.append([InlineKeyboardButton(text=name, callback_data=f"select_p2_{p['user_id']}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text("Выберите второго бойца:", reply_markup=kb)
    await state.set_state(CreateMatch.player2)
    await callback.answer()


@router.callback_query(F.data.startswith("select_p2_"))
async def select_player2(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    player2_id = int(callback.data.split("_")[2])
    await state.update_data(player2_id=player2_id)

    data = await state.get_data()
    participants = await get_tournament_participants(data['tournament_id'])

    p1 = next((p for p in participants if p['user_id'] == data['player1_id']), None)
    p2 = next((p for p in participants if p['user_id'] == player2_id), None)

    p1_name = p1['display_name'] or p1['username'] or str(p1['user_id'])
    p2_name = p2['display_name'] or p2['username'] or str(p2['user_id'])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_match"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_match"),
        ]
    ])

    await callback.message.edit_text(
        f"Создать поединок?\n\n{p1_name} vs {p2_name}",
        reply_markup=kb
    )
    await state.set_state(CreateMatch.confirm)
    await callback.answer()


@router.callback_query(F.data == "confirm_match", CreateMatch.confirm)
async def confirm_match(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()

    existing = await check_match_exists(
        data['tournament_id'],
        data['player1_id'],
        data['player2_id']
    )
    if existing:
        await callback.message.answer("Эти игроки уже сражались в этом турнире!")
        await state.clear()
        await callback.answer()
        return

    matches = await get_tournament_matches(data['tournament_id'])
    round_num = 1
    match_num = len([m for m in matches if m['round_num'] == round_num]) + 1

    match_id = await create_match(
        tournament_id=data['tournament_id'],
        player1_id=data['player1_id'],
        player2_id=data['player2_id'],
        round_num=round_num,
        match_num=match_num
    )

    participants = await get_tournament_participants(data['tournament_id'])

    p1 = next((p for p in participants if p['user_id'] == data['player1_id']), None)
    p2 = next((p for p in participants if p['user_id'] == data['player2_id']), None)

    p1_name = p1['display_name'] or p1['username'] or str(p1['user_id'])
    p2_name = p2['display_name'] or p2['username'] or str(p2['user_id'])

    p1_link = f'<a href="tg://user?id={data["player1_id"]}">{p1_name}</a>'
    p2_link = f'<a href="tg://user?id={data["player2_id"]}">{p2_name}</a>'

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p1_name} победил", callback_data=f"set_winner_{match_id}_{data['player1_id']}")],
        [InlineKeyboardButton(text=f"{p2_name} победил", callback_data=f"set_winner_{match_id}_{data['player2_id']}")],
        [InlineKeyboardButton(text=f"Ставка на {p1_name}", callback_data=f"betch_{match_id}_{data['player1_id']}")],
        [InlineKeyboardButton(text=f"Ставка на {p2_name}", callback_data=f"betch_{match_id}_{data['player2_id']}")],
    ])

    await bot.send_message(
        chat_id=chat_id,
        text=f"Поединок!\n\n{p1_link} vs {p2_link}\n\nКто победил?",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await state.clear()
    await callback.answer("Опубликовано!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data == "cancel_match")
async def cancel_match(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.answer("Отменено", show_alert=True)
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("set_winner_"))
async def set_winner_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Только админ может указать победителя!", show_alert=True)
        return

    parts = callback.data.split("_")
    match_id = int(parts[2])
    winner_id = int(parts[3])

    await set_match_winner(match_id, winner_id)
    total_pool, num_winners, share = await resolve_bets(match_id, winner_id)

    match = await get_match(match_id)
    participants = await get_tournament_participants(match['tournament_id'])

    winner = next((p for p in participants if p['user_id'] == winner_id), None)
    winner_name = winner['display_name'] or winner['username'] or str(winner_id)

    result_text = f'<a href="tg://user?id={winner_id}">{winner_name}</a> победил!'
    if total_pool > 0:
        result_text += f"\n\nБанк: {total_pool} монет"
        if num_winners > 0:
            result_text += f"\nКаждый победитель получает ставку + {share} монет"

    await callback.message.edit_text(result_text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("match_list_"))
async def match_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    matches = await get_tournament_matches(tournament_id)

    if not matches:
        await callback.message.answer("Пока нет поединков.")
        await callback.answer()
        return

    participants = await get_tournament_participants(tournament_id)

    text = "Поединки:\n\n"
    for m in matches:
        p1 = next((p for p in participants if p['user_id'] == m['player1_id']), None)
        p2 = next((p for p in participants if p['user_id'] == m['player2_id']), None) if m['player2_id'] else None

        p1_name = (p1['display_name'] or p1['username'] or str(m['player1_id'])) if p1 else "TBD"
        p2_name = (p2['display_name'] or p2['username'] or str(m['player2_id'])) if p2 else "TBD"

        if m['status'] == 'finished':
            winner = next((p for p in participants if p['user_id'] == m['winner_id']), None)
            winner_name = winner['display_name'] or winner['username'] if winner else "TBD"
            text += f"Р{m['round_num']} П{m['match_num']}: {p1_name} vs {p2_name} -> {winner_name}\n"
        else:
            text += f"Р{m['round_num']} П{m['match_num']}: {p1_name} vs {p2_name} (ожидает)\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"tournament_details_{tournament_id}")]
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("standings_"))
async def standings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[1])
    standings_data = await get_tournament_standings(tournament_id)

    if not standings_data:
        await callback.message.answer("Пока нет результатов.")
        await callback.answer()
        return

    text = "Турнирная сетка:\n\n"
    for i, s in enumerate(standings_data, 1):
        name = s['display_name'] or s['username'] or str(s['user_id'])
        text += f"{i}. {name} - Побед: {s['wins']}, Поражений: {s['losses']}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"tournament_details_{tournament_id}")]
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("finish_tournament_"))
async def finish_tournament_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    await show_prize_places(callback, tournament_id)


async def show_prize_places(callback_or_message, tournament_id, edit=False):
    tournament = await get_tournament(tournament_id)
    if not tournament:
        if hasattr(callback_or_message, 'answer'):
            await callback_or_message.answer("Турнир не найден!")
        return

    prize_places = tournament['prize_places'] or 1
    prizes = await get_tournament_prizes(tournament_id)
    assigned = {p['place']: p for p in prizes}

    text = f"Назначьте призовые места для \"{tournament['name']}\":\n\n"

    kb_buttons = []
    for place in range(1, prize_places + 1):
        place_label = {1: "1 место", 2: "2 место", 3: "3 место"}.get(place, f"{place} место")
        if place in assigned:
            p = assigned[place]
            text += f"{place_label}: ID {p['user_id']}\n"
            kb_buttons.append([InlineKeyboardButton(
                text=f"{place_label} — ID {p['user_id']}",
                callback_data=f"apz{tournament_id}x{place}"
            )])
        else:
            kb_buttons.append([InlineKeyboardButton(
                text=f"{place_label} — выбрать",
                callback_data=f"apz{tournament_id}x{place}"
            )])

    kb_buttons.append([
        InlineKeyboardButton(text="Объявить результаты", callback_data=f"announce_results_{tournament_id}")
    ])
    kb_buttons.append([
        InlineKeyboardButton(text="Назад", callback_data=f"tournament_details_{tournament_id}")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    if edit and hasattr(callback_or_message, 'edit_text'):
        await callback_or_message.edit_text(text, reply_markup=kb)
    else:
        await callback_or_message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("apz"))
async def assign_prize_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    parts = callback.data.split("x")
    tournament_id = int(parts[0][3:])
    place = int(parts[1])

    participants = await get_tournament_participants(tournament_id)

    text = f"Выберите игрока для {place} места:\n\n"

    kb_buttons = []
    for p in participants:
        name = p['display_name'] or str(p['user_id'])
        if p['username']:
            name += f" (@{p['username']})"
        kb_buttons.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"asp{tournament_id}x{p['user_id']}x{place}"
            ),
            InlineKeyboardButton(
                text="Профиль",
                callback_data=f"upf{p['user_id']}"
            )
        ])

    kb_buttons.append([
        InlineKeyboardButton(text="Назад", callback_data=f"finish_tournament_{tournament_id}")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("asp"))
async def select_prize_player(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    parts = callback.data.split("x")
    tournament_id = int(parts[0][3:])
    user_id = int(parts[1])
    place = int(parts[2])

    await set_tournament_prize(tournament_id, user_id, place, f"{place} место")

    tournament = await get_tournament(tournament_id)
    prizes = await get_tournament_prizes(tournament_id)
    assigned = {p['place']: p for p in prizes}
    prize_places = tournament['prize_places'] or 1

    text = f"Назначьте призовые места для \"{tournament['name']}\":\n\n"

    kb_buttons = []
    for p in range(1, prize_places + 1):
        place_label = {1: "1 место", 2: "2 место", 3: "3 место"}.get(p, f"{p} место")
        if p in assigned:
            prize = assigned[p]
            kb_buttons.append([InlineKeyboardButton(
                text=f"{place_label} — ID {prize['user_id']}",
                callback_data=f"apz{tournament_id}x{p}"
            )])
        else:
            kb_buttons.append([InlineKeyboardButton(
                text=f"{place_label} — выбрать",
                callback_data=f"apz{tournament_id}x{p}"
            )])

    kb_buttons.append([
        InlineKeyboardButton(text="Объявить результаты", callback_data=f"announce_results_{tournament_id}")
    ])
    kb_buttons.append([
        InlineKeyboardButton(text="Назад", callback_data=f"tournament_details_{tournament_id}")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("Место назначено!")


@router.callback_query(F.data.startswith("announce_results_"))
async def announce_results_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    tournament_id = int(callback.data.split("_")[2])
    await finish_tournament(tournament_id)

    tournament = await get_tournament(tournament_id)
    prizes = await get_tournament_prizes(tournament_id)
    standings = await get_tournament_standings(tournament_id)

    from database import update_player_stats, update_tournament_stats, calculate_elo_change

    if standings and len(standings) >= 2:
        for i in range(len(standings)):
            for j in range(i + 1, len(standings)):
                winner = standings[i]
                loser = standings[j]
                elo_change = calculate_elo_change(winner['elo'] if 'elo' in winner.keys() else 1000, loser['elo'] if 'elo' in loser.keys() else 1000)
                await update_player_stats(winner['user_id'], chat_id, elo_change, True)
                await update_player_stats(loser['user_id'], chat_id, -elo_change, False)

    if prizes:
        for prize in prizes:
            if prize['place'] == 1:
                await update_tournament_stats(prize['user_id'], chat_id, True)
            else:
                await update_tournament_stats(prize['user_id'], chat_id, False)
    elif standings:
        await update_tournament_stats(standings[0]['user_id'], chat_id, True)
        for s in standings[1:]:
            await update_tournament_stats(s['user_id'], chat_id, False)

    from database import check_and_award_achievements, get_user_achievements
    all_awarded = []
    if prizes:
        for prize in prizes:
            awarded = await check_and_award_achievements(prize['user_id'], chat_id)
            all_awarded.extend(awarded)
    elif standings:
        for s in standings:
            awarded = await check_and_award_achievements(s['user_id'], chat_id)
            all_awarded.extend(awarded)

    text = f"Турнир \"{tournament['name']}\" завершен!\n\n"

    if prizes:
        text += "Призовые места:\n"
        for prize in prizes:
            name = str(prize['user_id'])
            uid = prize['user_id']
            if standings:
                for s in standings:
                    if s['user_id'] == prize['user_id']:
                        name = s['display_name'] or s['username'] or str(s['user_id'])
                        uid = s['user_id']
                        break
            text += f'  {prize["place"]} место: <a href="tg://user?id={uid}">{name}</a>\n'
    elif standings:
        winner = standings[0]
        winner_name = winner['display_name'] or winner['username'] or str(winner['user_id'])
        text += f'Победитель: <a href="tg://user?id={winner["user_id"]}">{winner_name}</a>\n'

    if all_awarded:
        text += "\nНаграждены достижениями:\n"
        from database import ACHIEVEMENTS
        for a in set(all_awarded):
            if a in ACHIEVEMENTS:
                text += f"  {ACHIEVEMENTS[a][0]}\n"

    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    await callback.answer("Готово!", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data == "admin_quizzes")
async def admin_quizzes_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить вопрос", callback_data="add_quiz")],
        [InlineKeyboardButton(text="Опубликовать в чат", callback_data="publish_quiz")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer("Викторины:", reply_markup=kb)
    await callback.answer()


class AddQuiz(StatesGroup):
    question = State()
    options = State()
    correct = State()


@router.callback_query(F.data == "add_quiz")
async def add_quiz_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Введите вопрос:")
    await state.set_state(AddQuiz.question)
    await callback.answer()


@router.message(AddQuiz.question)
async def quiz_question(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(question=message.text)
    await message.answer("Введите 4 варианта ответа через запятую:")
    await state.set_state(AddQuiz.options)


@router.message(AddQuiz.options)
async def quiz_options(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    options = [o.strip() for o in message.text.split(",")]
    if len(options) != 4:
        await message.answer("Нужно ровно 4 варианта через запятую:")
        return

    await state.update_data(options=options)
    await message.answer("Номер правильного ответа (1-4):")
    await state.set_state(AddQuiz.correct)


@router.message(AddQuiz.correct)
async def quiz_correct(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        correct = int(message.text) - 1
        if correct < 0 or correct > 3:
            await message.answer("Введите число от 1 до 4:")
            return
    except ValueError:
        await message.answer("Введите число:")
        return

    data = await state.get_data()
    chat_id = await get_chat_id()
    if not chat_id:
        await message.answer("Сначала настройте чат командой /setchat!")
        await state.clear()
        return

    await add_quiz(
        chat_id=chat_id,
        question=data['question'],
        options=data['options'],
        correct_index=correct,
        created_by=message.from_user.id
    )

    await state.clear()
    await message.answer("Вопрос добавлен!")


class PublishQuiz(StatesGroup):
    question = State()
    options = State()
    correct = State()
    image = State()


@router.callback_query(F.data == "publish_quiz")
async def publish_quiz_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.answer("Введите вопрос:")
    await state.set_state(PublishQuiz.question)
    await callback.answer()


@router.message(PublishQuiz.question)
async def publish_quiz_question(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(question=message.text)
    await message.answer("Введите 4 варианта ответа через запятую:")
    await state.set_state(PublishQuiz.options)


@router.message(PublishQuiz.options)
async def publish_quiz_options(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    options = [o.strip() for o in message.text.split(",")]
    if len(options) != 4:
        await message.answer("Нужно ровно 4 варианта через запятую:")
        return
    await state.update_data(options=options)
    await message.answer("Номер правильного ответа (1-4):")
    await state.set_state(PublishQuiz.correct)


@router.message(PublishQuiz.correct)
async def publish_quiz_correct(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        correct = int(message.text) - 1
        if correct < 0 or correct > 3:
            await message.answer("Введите число от 1 до 4:")
            return
    except ValueError:
        await message.answer("Введите число:")
        return
    await state.update_data(correct=correct)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без картинки", callback_data="pqz_no_image")]
    ])
    await message.answer("Прикрепите изображение или нажмите 'Без картинки':", reply_markup=kb)
    await state.set_state(PublishQuiz.image)


@router.callback_query(F.data == "pqz_no_image", PublishQuiz.image)
async def publish_quiz_no_image(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    await _publish_quiz_final(callback.message, state, bot, None)


@router.message(PublishQuiz.image, F.photo)
async def publish_quiz_with_image(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    photo = message.photo[-1]
    await _publish_quiz_final(message, state, bot, photo.file_id)


async def _publish_quiz_final(msg, state, bot, image_file_id):
    data = await state.get_data()
    chat_id = await get_chat_id()
    if not chat_id:
        await msg.answer("Сначала настройте чат командой /setchat!")
        await state.clear()
        return

    quiz_id = await add_quiz(
        chat_id=chat_id,
        question=data['question'],
        options=data['options'],
        correct_index=data['correct'],
        created_by=msg.from_user.id if hasattr(msg, 'from_user') else 0,
        image=image_file_id
    )

    kb_buttons = []
    for i, opt in enumerate(data['options']):
        kb_buttons.append([InlineKeyboardButton(text=opt, callback_data=f"qz{quiz_id}x{i}")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    text = f"Викторина:\n\n{data['question']}"

    if image_file_id:
        await bot.send_photo(chat_id=chat_id, photo=image_file_id, caption=text, reply_markup=kb)
    else:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)

    await state.clear()
    await msg.answer("Опубликовано!")


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    count = await get_known_users_count()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить рассылку", callback_data="send_broadcast")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer(
        f"Известно пользователей: {count}\n\n"
        f"Отправьте сообщение для рассылки (текст, фото или видео):",
        reply_markup=kb
    )
    await callback.answer()


class BroadcastState(StatesGroup):
    waiting_content = State()


@router.callback_query(F.data == "send_broadcast")
async def send_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer("Отправьте сообщение для рассылки:")
    await state.set_state(BroadcastState.waiting_content)
    await callback.answer()


@router.message(BroadcastState.waiting_content)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    users = await get_all_known_users()
    if not users:
        await message.answer("Нет пользователей для рассылки.")
        await state.clear()
        return

    sent = 0
    failed = 0

    await message.answer(f"Начинаю рассылку для {len(users)} пользователей...")

    for user in users:
        try:
            if message.photo:
                await message.bot.send_photo(
                    chat_id=user['user_id'],
                    photo=message.photo[-1].file_id,
                    caption=message.caption or ""
                )
            elif message.video:
                await message.bot.send_video(
                    chat_id=user['user_id'],
                    video=message.video.file_id,
                    caption=message.caption or ""
                )
            elif message.text:
                await message.bot.send_message(
                    chat_id=user['user_id'],
                    text=message.text
                )
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"Рассылка завершена!\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}"
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    try:
        stats = await get_bot_stats()
        t_stats = await get_tournament_analytics()

        text = (
            f"Статистика бота:\n\n"
            f"Пользователей: {stats['total_users']}\n"
            f"Турниров: {stats['total_tournaments']}\n"
            f"Матчей: {stats['total_matches']}\n"
            f"Событий: {stats['total_events']}\n"
            f"Голосований: {stats['total_polls']}\n"
            f"Ставок: {stats['total_bets']}\n"
            f"Кланов: {stats['total_clans']}\n"
        )

        if t_stats.get('top_winners'):
            text += "\nТоп победителей:\n"
            for i, w in enumerate(t_stats['top_winners'][:3], 1):
                text += f"  {i}. ID {w['winner_id']} — {w['wins']} побед\n"

        await callback.message.answer(text)
    except Exception as e:
        await callback.message.answer(f"Ошибка при получении статистики: {e}")
    await callback.answer()


@router.message(Command("history"))
async def admin_balance_history(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return

    target_id = message.reply_to_message.from_user.id
    from database import get_user_name, get_balance_history
    name = await get_user_name(target_id)
    link = f'<a href="tg://user?id={target_id}">{name}</a>'
    history = await get_balance_history(target_id, 15)

    text = f"История баланса: {link}\n\n"

    if history:
        for h in history:
            sign = "+" if h['amount'] > 0 else ""
            text += f"{sign}{h['amount']} — {h['reason']}\n"
    else:
        text += "Пока нет операций."

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_balance_history")
async def admin_balance_history_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.answer("Ответьте на сообщение пользователя, чтобы посмотреть историю его баланса.")
    await callback.answer()


@router.message(Command("history"))
async def admin_balance_history(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return

    target_id = message.reply_to_message.from_user.id
    from database import get_user_name, get_balance_history
    name = await get_user_name(target_id)
    link = f'<a href="tg://user?id={target_id}">{name}</a>'
    history = await get_balance_history(target_id, 15)

    text = f"История баланса: {link}\n\n"

    if history:
        for h in history:
            sign = "+" if h['amount'] > 0 else ""
            text += f"{sign}{h['amount']} — {h['reason']}\n"
    else:
        text += "Пока нет операций."

    await message.answer(text, parse_mode="HTML")
