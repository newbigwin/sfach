from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from config import ADMIN_ID
from database import (
    add_event, get_events, delete_event, add_poll, get_active_polls,
    get_poll, vote, get_poll_results, close_poll, get_event,
    create_tournament, get_tournament, get_active_tournaments, start_tournament,
    get_tournament_participants, get_participant_count, finish_tournament,
    create_match, get_pending_matches, set_match_winner, get_tournament_matches,
    get_tournament_standings, delete_tournament
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


class CreateTournament(StatesGroup):
    name = State()
    description = State()
    max_participants = State()
    confirm = State()


class CreateMatch(StatesGroup):
    player1 = State()
    player2 = State()
    confirm = State()


class SetWinner(StatesGroup):
    match_id = State()
    winner = State()


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
        [InlineKeyboardButton(text="Управление турнирами", callback_data="tournaments_menu")],
        [InlineKeyboardButton(text="Утихомирить всех", callback_data="mute_all")],
        [InlineKeyboardButton(text="Созвать всех", callback_data="summon_all")],
    ])

    await message.answer("Панель администратора:", reply_markup=kb)


@router.callback_query(F.data == "tournaments_menu")
async def tournaments_menu(callback: CallbackQuery):
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

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать событие", callback_data="create_event")],
        [InlineKeyboardButton(text="Создать голосование", callback_data="create_poll")],
        [InlineKeyboardButton(text="Список событий", callback_data="list_events")],
        [InlineKeyboardButton(text="Активные голосования", callback_data="list_polls")],
        [InlineKeyboardButton(text="Управление турнирами", callback_data="tournaments_menu")],
        [InlineKeyboardButton(text="Утихомирить всех", callback_data="mute_all")],
        [InlineKeyboardButton(text="Созвать всех", callback_data="summon_all")],
    ])

    await callback.message.answer("Панель администратора:", reply_markup=kb)
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
    await state.update_data(name=message.text)
    await message.answer("Введите описание турнира:")
    await state.set_state(CreateTournament.description)


@router.message(CreateTournament.description)
async def tournament_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите максимальное количество участников (4, 8, 16, 32):")
    await state.set_state(CreateTournament.max_participants)


@router.message(CreateTournament.max_participants)
async def tournament_max_participants(message: Message, state: FSMContext):
    try:
        max_p = int(message.text)
        if max_p not in [4, 8, 16, 32]:
            await message.answer("Допустимые значения: 4, 8, 16, 32. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("Введите число. Попробуйте снова:")
        return

    await state.update_data(max_participants=max_p)
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_tournament"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_tournament"),
        ]
    ])

    await message.answer(
        f"Создать турнир?\n\n"
        f"Название: {data['name']}\n"
        f"Описание: {data['description']}\n"
        f"Макс. участников: {data['max_participants']}",
        reply_markup=kb
    )
    await state.set_state(CreateTournament.confirm)


@router.callback_query(F.data == "confirm_tournament", CreateTournament.confirm)
async def confirm_tournament(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    tournament_id = await create_tournament(
        name=data['name'],
        description=data['description'],
        max_participants=data['max_participants'],
        created_by=callback.from_user.id,
        chat_id=callback.message.chat.id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Записаться на турнир", callback_data=f"join_tournament_{tournament_id}")]
    ])

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"Турнир создан!\n\n"
            f"{data['name']}\n\n"
            f"{data['description']}\n\n"
            f"Макс. участников: {data['max_participants']}\n\n"
            f"Записывайтесь!"
        ),
        reply_markup=kb
    )

    await state.clear()
    await callback.message.edit_text("Турнир создан!")
    await callback.answer()


@router.callback_query(F.data == "cancel_tournament")
async def cancel_tournament(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание турнира отменено.")
    await callback.answer()


@router.callback_query(F.data == "list_tournaments")
async def list_tournaments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournaments = await get_active_tournaments(callback.message.chat.id)

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
                callback_data=f"tournament_{t['id']}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Выберите турнир:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("tournament_"))
async def tournament_details(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[1])
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
            text += f"{i}. {p['display_name'] or p['username']}\n"
    else:
        text += "Пока нет участников.\n"

    kb_buttons = []

    if tournament['status'] == 'registration':
        kb_buttons.append([InlineKeyboardButton(text="Начать турнир", callback_data=f"start_tournament_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Удалить турнир", callback_data=f"delete_tournament_{tournament_id}")])
    elif tournament['status'] == 'in_progress':
        kb_buttons.append([InlineKeyboardButton(text="Создать поединок", callback_data=f"create_match_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Результаты поединков", callback_data=f"match_list_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Турнирная сетка", callback_data=f"standings_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Завершить турнир", callback_data=f"finish_tournament_{tournament_id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("start_tournament_"))
async def start_tournament_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    tournament = await get_tournament(tournament_id)

    if not tournament:
        await callback.answer("Турнир не найден!", show_alert=True)
        return

    count = await get_participant_count(tournament_id)
    if count < 2:
        await callback.answer("Нужно минимум 2 участника!", show_alert=True)
        return

    await start_tournament(tournament_id)

    participants = await get_tournament_participants(tournament_id)
    mentions = " ".join([f"[user](tg://user?id={p['user_id']})" for p in participants])

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"Турнир \"{tournament['name']}\" начинается!\n\nУчастники:\n{mentions}\n\nОжидайте поединков!",
        parse_mode="Markdown"
    )
    await callback.message.edit_text("Турнир начат!")
    await callback.answer()


@router.callback_query(F.data.startswith("delete_tournament_"))
async def delete_tournament_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    await delete_tournament(tournament_id)
    await callback.message.edit_text("Турнир удален.")
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

    await state.update_data(tournament_id=tournament_id, participants=[p['user_id'] for p in participants])

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
    data = await state.get_data()

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

    match = await get_match(match_id)
    participants = await get_tournament_participants(data['tournament_id'])

    p1 = next((p for p in participants if p['user_id'] == data['player1_id']), None)
    p2 = next((p for p in participants if p['user_id'] == data['player2_id']), None)

    p1_name = p1['display_name'] or p1['username'] or str(p1['user_id'])
    p2_name = p2['display_name'] or p2['username'] or str(p2['user_id'])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p1_name} - Победил", callback_data=f"set_winner_{match_id}_{data['player1_id']}")],
        [InlineKeyboardButton(text=f"{p2_name} - Победил", callback_data=f"set_winner_{match_id}_{data['player2_id']}")],
    ])

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"Новый поединок!\n\n{p1_name} vs {p2_name}\n\nКто победил?",
        reply_markup=kb
    )

    await state.clear()
    await callback.message.edit_text("Поединок создан!")
    await callback.answer()


@router.callback_query(F.data == "cancel_match")
async def cancel_match(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание поединка отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("set_winner_"))
async def set_winner_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    parts = callback.data.split("_")
    match_id = int(parts[2])
    winner_id = int(parts[3])

    await set_match_winner(match_id, winner_id)

    match = await get_match(match_id)
    participants = await get_tournament_participants(match['tournament_id'])

    winner = next((p for p in participants if p['user_id'] == winner_id), None)
    winner_name = winner['display_name'] or winner['username'] or str(winner_id)

    await callback.message.edit_text(f"Победитель: {winner_name}")
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

        p1_name = p1['display_name'] or p1['username'] or str(m['player1_id']) if p1 else "TBD"
        p2_name = p2['display_name'] or p2['username'] or str(m['player2_id']) if p2 else "TBD"

        if m['status'] == 'finished':
            winner = next((p for p in participants if p['user_id'] == m['winner_id']), None)
            winner_name = winner['display_name'] or winner['username'] if winner else "TBD"
            text += f"Р{m['round_num']} П{m['match_num']}: {p1_name} vs {p2_name} -> {winner_name}\n"
        else:
            text += f"Р{m['round_num']} П{m['match_num']}: {p1_name} vs {p2_name} (ожидает)\n"

    await callback.message.answer(text)
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

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data.startswith("finish_tournament_"))
async def finish_tournament_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    await finish_tournament(tournament_id)

    tournament = await get_tournament(tournament_id)
    standings_data = await get_tournament_standings(tournament_id)

    if standings_data:
        winner = standings_data[0]
        winner_name = winner['display_name'] or winner['username'] or str(winner['user_id'])

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"[user](tg://user?id={winner['user_id']})", callback_data="noop")]
        ])

        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=(
                f"Турнир \"{tournament['name']}\" завершен!\n\n"
                f"Победитель: {winner_name}\n"
                f"Побед: {winner['wins']}, Поражений: {winner['losses']}"
            ),
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"Турнир \"{tournament['name']}\" завершен!"
        )

    await callback.message.edit_text("Турнир завершен!")
    await callback.answer()
