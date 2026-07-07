from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from config import ADMIN_ID
from database import (
    add_event, get_events, delete_event, add_poll, get_active_polls,
    get_poll, vote, get_poll_results, close_poll, get_event
)

router = Router()


class CreateEvent(StatesGroup):
    title = State()
    description = State()
    event_date = State()
    confirm = State()


class CreatePoll(StatesGroup):
    question = State()
    options = State()
    poll_type = State()
    confirm = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать событие", callback_data="create_event")],
        [InlineKeyboardButton(text="Создать голосование", callback_data="create_poll")],
        [InlineKeyboardButton(text="Список событий", callback_data="list_events")],
        [InlineKeyboardButton(text="Активные голосования", callback_data="list_polls")],
        [InlineKeyboardButton(text="Утихомирить всех", callback_data="mute_all")],
        [InlineKeyboardButton(text="Созвать всех", callback_data="summon_all")],
    ])

    await message.answer("Панель администратора:", reply_markup=kb)


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
    await state.update_data(title=message.text)
    await message.answer("Введите описание события:")
    await state.set_state(CreateEvent.description)


@router.message(CreateEvent.description)
async def event_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите дату и время события (например: 15.07.2026 19:00):")
    await state.set_state(CreateEvent.event_date)


@router.message(CreateEvent.event_date)
async def event_date(message: Message, state: FSMContext):
    await state.update_data(event_date=message.text)
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="confirm_event"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_event"),
        ]
    ])

    await message.answer(
        f"Подтвердите создание события:\n\n"
        f"Название: {data['title']}\n"
        f"Описание: {data['description']}\n"
        f"Дата: {data['event_date']}",
        reply_markup=kb
    )
    await state.set_state(CreateEvent.confirm)


@router.callback_query(F.data == "confirm_event", CreateEvent.confirm)
async def confirm_event(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    event_id = await add_event(
        title=data['title'],
        description=data['description'],
        event_date=data['event_date'],
        created_by=callback.from_user.id,
        chat_id=callback.message.chat.id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проголосовать за это событие", callback_data=f"vote_event_{event_id}")]
    ])

    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"Новое событие!\n\n"
            f"{data['title']}\n\n"
            f"{data['description']}\n\n"
            f"Дата: {data['event_date']}\n\n"
            f"Голосуйте, если хотите участвовать:"
        ),
        reply_markup=kb
    )

    await state.clear()
    await callback.message.edit_text("Событие создано!")
    await callback.answer()


@router.callback_query(F.data.startswith("vote_event_"))
async def vote_for_event(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    event = await get_event(event_id)

    if not event:
        await callback.answer("Событие не найдено!", show_alert=True)
        return

    poll_id = await add_poll(
        question=f"Голосование: {event['title']}?",
        options=["Буду участвовать", "Не смогу", "Посмотрю"],
        poll_type="event",
        created_by=callback.from_user.id,
        chat_id=callback.message.chat.id,
        event_id=event_id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Буду участвовать", callback_data=f"vote_{poll_id}_0")],
        [InlineKeyboardButton(text=f"Не смогу", callback_data=f"vote_{poll_id}_1")],
        [InlineKeyboardButton(text=f"Посмотрю", callback_data=f"vote_{poll_id}_2")],
    ])

    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Голос записан!")


@router.callback_query(F.data == "cancel_event")
async def cancel_event(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание события отменено.")
    await callback.answer()


@router.callback_query(F.data == "list_events")
async def list_events(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    events = await get_events(callback.message.chat.id)

    if not events:
        await callback.message.answer("Нет событий.")
        await callback.answer()
        return

    text = "Список событий:\n\n"
    kb_buttons = []

    for event in events:
        text += f"ID: {event['id']} | {event['title']} | {event['event_date']}\n"
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"Удалить: {event['title']}",
                callback_data=f"delete_event_{event['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    await delete_event(event_id)
    await callback.message.edit_text("Событие удалено.")
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
    poll_type = callback.data.split("_")[2]
    await state.update_data(poll_type=poll_type)

    type_names = {
        "event": "за следующее событие",
        "time": "за время проведения",
        "general": "общее"
    }

    await callback.message.answer(f"Введите вопрос для голосования ({type_names[poll_type]}):")
    await state.set_state(CreatePoll.question)
    await callback.answer()


@router.message(CreatePoll.question)
async def poll_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer("Введите варианты ответов (каждый с новой строки, минимум 2):")
    await state.set_state(CreatePoll.options)


@router.message(CreatePoll.options)
async def poll_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split("\n") if opt.strip()]

    if len(options) < 2:
        await message.answer("Нужно минимум 2 варианта. Попробуйте снова:")
        return

    if len(options) > 10:
        await message.answer("Максимум 10 вариантов. Попробуйте снова:")
        return

    await state.update_data(options=options)
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_poll"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_poll"),
        ]
    ])

    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    await message.answer(
        f"Вопрос: {data['question']}\n\nВарианты:\n{options_text}",
        reply_markup=kb
    )
    await state.set_state(CreatePoll.confirm)


@router.callback_query(F.data == "confirm_poll", CreatePoll.confirm)
async def confirm_poll(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    poll_id = await add_poll(
        question=data['question'],
        options=data['options'],
        poll_type=data['poll_type'],
        created_by=callback.from_user.id,
        chat_id=callback.message.chat.id
    )

    kb_buttons = []
    for i, opt in enumerate(data['options']):
        kb_buttons.append([InlineKeyboardButton(text=opt, callback_data=f"vote_{poll_id}_{i}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"Голосование: {data['question']}",
        reply_markup=kb
    )

    await state.clear()
    await callback.message.edit_text("Голосование создано!")
    await callback.answer()


@router.callback_query(F.data == "cancel_poll")
async def cancel_poll(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание голосования отменено.")
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
        f"Голосование: {poll['question']}\n\nРезультаты:\n{results_text}\n\nВсего голосов: {total}",
        reply_markup=kb
    )
    await callback.answer("Голос записан!")


@router.callback_query(F.data == "list_polls")
async def list_polls(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    polls = await get_active_polls(callback.message.chat.id)

    if not polls:
        await callback.message.answer("Нет активных голосований.")
        await callback.answer()
        return

    kb_buttons = []
    for poll in polls:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"Закрыть: {poll['question'][:30]}",
                callback_data=f"close_poll_{poll['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(f"Активные голосования ({len(polls)}):", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("close_poll_"))
async def close_poll_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    poll_id = int(callback.data.split("_")[2])
    await close_poll(poll_id)
    await callback.message.edit_text("Голосование закрыто.")
    await callback.answer()


@router.callback_query(F.data == "mute_all")
async def mute_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = callback.message.chat.id
    muted_count = 0

    async for member in bot.get_chat_members(chat_id):
        if member.user.id == callback.from_user.id:
            continue
        if member.status in ("creator", "administrator"):
            continue

        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member.user.id,
                permissions={"can_send_messages": False}
            )
            muted_count += 1
        except Exception:
            continue

    await callback.message.answer(f"Утихомирены: {muted_count} участников.")
    await callback.answer()


@router.callback_query(F.data == "summon_all")
async def summon_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = callback.message.chat.id
    members = []

    async for member in bot.get_chat_members(chat_id):
        if member.user.id == callback.from_user.id:
            continue
        if member.user.is_bot:
            continue
        if member.status in ("creator", "administrator"):
            continue

        members.append(member.user.id)

    if not members:
        await callback.message.answer("Нет участников для созыва.")
        await callback.answer()
        return

    mentions = " ".join([f"[user](tg://user?id={uid})" for uid in members[:50]])

    await callback.message.answer(
        f"Созыв всех участников!\n\n{mentions}\n\nПриглашаем вас принять участие!",
        parse_mode="Markdown"
    )
    await callback.answer()
