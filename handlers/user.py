from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command

from database import get_events, get_active_polls, get_poll, vote, get_poll_results

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="События", callback_data="user_events")],
        [InlineKeyboardButton(text="Голосования", callback_data="user_polls")],
        [InlineKeyboardButton(text="Помощь", callback_data="user_help")],
    ])

    await message.answer(
        "Привет! Я бот для турниров по Shadow Fight 4: Arena.\n\n"
        "Выберите действие:",
        reply_markup=kb
    )


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Команды:\n"
        "/start - Главное меню\n"
        "/events - Список событий\n"
        "/polls - Активные голосования\n"
        "/help - Помощь"
    )


@router.message(Command("events"))
async def events_cmd(message: Message):
    events = await get_events(message.chat.id)

    if not events:
        await message.answer("Пока нет событий.")
        return

    text = "События:\n\n"
    for event in events:
        text += f"{event['title']}\n{event['description']}\nДата: {event['event_date']}\n\n"

    await message.answer(text)


@router.message(Command("polls"))
async def polls_cmd(message: Message):
    polls = await get_active_polls(message.chat.id)

    if not polls:
        await message.answer("Нет активных голосований.")
        return

    kb_buttons = []
    for poll in polls:
        kb_buttons.append([
            InlineKeyboardButton(
                text=poll['question'][:40],
                callback_data=f"user_poll_{poll['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await message.answer("Активные голосования:", reply_markup=kb)


@router.callback_query(F.data == "user_events")
async def user_events(callback: CallbackQuery):
    events = await get_events(callback.message.chat.id)

    if not events:
        await callback.message.answer("Пока нет событий.")
        await callback.answer()
        return

    text = "События:\n\n"
    for event in events:
        text += f"{event['title']}\n{event['description']}\nДата: {event['event_date']}\n\n"

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "user_polls")
async def user_polls(callback: CallbackQuery):
    polls = await get_active_polls(callback.message.chat.id)

    if not polls:
        await callback.message.answer("Нет активных голосований.")
        await callback.answer()
        return

    kb_buttons = []
    for poll in polls:
        kb_buttons.append([
            InlineKeyboardButton(
                text=poll['question'][:40],
                callback_data=f"user_poll_{poll['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Активные голосования:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("user_poll_"))
async def user_poll_detail(callback: CallbackQuery):
    poll_id = int(callback.data.split("_")[2])
    poll = await get_poll(poll_id)

    if not poll:
        await callback.message.answer("Голосование не найдено.")
        await callback.answer()
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
        f"{opt}: {results_dict.get(i, 0)} голосов"
        for i, opt in enumerate(options)
    ]) if total > 0 else "Пока нет голосов"

    await callback.message.answer(
        f"Голосование: {poll['question']}\n\nРезультаты:\n{results_text}\n\nВсего: {total}",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "user_help")
async def user_help(callback: CallbackQuery):
    await callback.message.answer(
        "Этот бот создан для турниров по Shadow Fight 4: Arena.\n\n"
        "Вы можете:\n"
        "- Просматривать события\n"
        "- Участвовать в голосованиях\n"
        "- Следить за турнирами"
    )
    await callback.answer()
