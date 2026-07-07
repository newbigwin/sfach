from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command

from config import ADMIN_ID
from database import (
    get_events, get_active_polls, get_poll, vote, get_poll_results,
    get_active_tournaments, get_tournament, join_tournament, leave_tournament,
    get_tournament_participants, get_participant_count, get_tournament_standings,
    get_setting, get_chat_id, track_chat_member
)

router = Router()


@router.message()
async def track_user(message: Message):
    if message.from_user and message.chat.type != "private":
        chat_id = await get_chat_id()
        if chat_id and str(message.chat.id) == str(chat_id):
            await track_chat_member(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                username=message.from_user.username,
                display_name=message.from_user.full_name
            )


@router.message(CommandStart())
async def start(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="События", callback_data="user_events")],
        [InlineKeyboardButton(text="Голосования", callback_data="user_polls")],
        [InlineKeyboardButton(text="Турниры", callback_data="user_tournaments")],
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
        "/tournaments - Турниры\n"
        "/help - Помощь"
    )


@router.message(Command("events"))
async def events_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

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
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

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
    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Чат не настроен.")
        await callback.answer()
        return

    events = await get_events(chat_id)

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
    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Чат не настроен.")
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
        "- Записываться на турниры\n"
        "- Смотреть турнирную сетку"
    )
    await callback.answer()


@router.message(Command("tournaments"))
async def tournaments_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    tournaments = await get_active_tournaments(message.chat.id)

    if not tournaments:
        await message.answer("Нет активных турниров.")
        return

    kb_buttons = []
    for t in tournaments:
        count = await get_participant_count(t['id'])
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{t['name']} ({count}/{t['max_participants']})",
                callback_data=f"user_tournament_{t['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await message.answer("Активные турниры:", reply_markup=kb)


@router.callback_query(F.data == "user_tournaments")
async def user_tournaments(callback: CallbackQuery):
    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Чат не настроен.")
        await callback.answer()
        return

    tournaments = await get_active_tournaments(chat_id)

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
                callback_data=f"user_tournament_{t['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Активные турниры:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("user_tournament_"))
async def user_tournament_detail(callback: CallbackQuery):
    tournament_id = int(callback.data.split("_")[2])
    tournament = await get_tournament(tournament_id)

    if not tournament:
        await callback.message.answer("Турнир не найден.")
        await callback.answer()
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
            text += f"{i}. {p['display_name'] or p['username']}\n"

    kb_buttons = []

    if tournament['status'] == 'registration':
        user_id = callback.from_user.id
        is_joined = any(p['user_id'] == user_id for p in participants)

        if is_joined:
            kb_buttons.append([InlineKeyboardButton(text="Покинуть турнир", callback_data=f"leave_tournament_{tournament_id}")])
        elif count < tournament['max_participants']:
            kb_buttons.append([InlineKeyboardButton(text="Записаться", callback_data=f"join_tournament_{tournament_id}")])

    if tournament['status'] in ('registration', 'in_progress'):
        kb_buttons.append([InlineKeyboardButton(text="Турнирная сетка", callback_data=f"user_standings_{tournament_id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("join_tournament_"))
async def join_tournament_handler(callback: CallbackQuery, bot: Bot):
    tournament_id = int(callback.data.split("_")[2])
    tournament = await get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    if tournament['status'] != 'registration':
        await callback.answer("Запись закрыта!", show_alert=True)
        return

    count = await get_participant_count(tournament_id)
    if count >= tournament['max_participants']:
        await callback.answer("Нет свободных мест!", show_alert=True)
        return

    user = callback.from_user
    display_name = user.full_name or user.username or str(user.id)

    success = await join_tournament(
        tournament_id=tournament_id,
        user_id=user.id,
        username=user.username,
        display_name=display_name
    )

    if success:
        await callback.answer("Вы записаны на турнир!", show_alert=True)

        chat_id = await get_setting("chat_id")
        if chat_id:
            await bot.send_message(
                chat_id=chat_id,
                text=f'<a href="tg://user?id={user.id}">{display_name}</a> записался на турнир "{tournament["name"]}"',
                parse_mode="HTML"
            )

        admin_text = f'<a href="tg://user?id={user.id}">{display_name}</a>'
        if user.username:
            admin_text += f" (@{user.username})"
        admin_text += f' записался на турнир "{tournament["name"]}"'

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="HTML"
        )
    else:
        await callback.answer("Вы уже записаны!", show_alert=True)


@router.callback_query(F.data.startswith("leave_tournament_"))
async def leave_tournament_handler(callback: CallbackQuery):
    tournament_id = int(callback.data.split("_")[2])
    tournament = await get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    if tournament['status'] != 'registration':
        await callback.answer("Нельзя покинуть турнир!", show_alert=True)
        return

    await leave_tournament(tournament_id, callback.from_user.id)
    await callback.answer("Вы покинули турнир.", show_alert=True)
    await callback.message.edit_text(f"Вы покинули турнир \"{tournament['name']}\".")


@router.callback_query(F.data.startswith("user_standings_"))
async def user_standings(callback: CallbackQuery):
    tournament_id = int(callback.data.split("_")[2])
    standings_data = await get_tournament_standings(tournament_id)

    if not standings_data:
        await callback.message.answer("Пока нет результатов.")
        await callback.answer()
        return

    text = "Турнирная сетка:\n\n"
    for i, s in enumerate(standings_data, 1):
        name = s['display_name'] or s['username'] or str(s['user_id'])
        text += f"{i}. {name} - Побед: {s['wins']}, Поражений: {s['losses']}\n"

    await callback.message.answer(text)
    await callback.answer()
