from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import (
    get_events, get_active_polls, get_poll, vote, get_poll_results,
    get_active_tournaments, get_tournament, join_tournament, leave_tournament,
    get_tournament_participants, get_participant_count, get_tournament_standings,
    get_setting, get_chat_id, track_chat_member,
    get_or_create_player, get_leaderboard, get_player_stats,
    create_clan, get_clan, get_user_clan, join_clan, leave_clan,
    get_clan_members, get_clans, get_clan_member_count
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
        "/profile - Мой профиль\n"
        "/leaderboard - Таблица лидеров\n"
        "/clan - Мой клан\n"
        "/clans - Все кланы\n"
        "/clan_join <ID> - Вступить в клан\n"
        "/clan_leave - Покинуть клан\n"
        "/help - Помощь"
    )


@router.message(Command("profile"))
async def profile_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    player = await get_or_create_player(user_id, chat_id)

    total_games = player['wins'] + player['losses']
    winrate = (player['wins'] * 100 // total_games) if total_games > 0 else 0

    text = (
        f"Профиль: {message.from_user.full_name}\n\n"
        f"Рейтинг (ELO): {player['elo']}\n"
        f"Победы: {player['wins']}\n"
        f"Поражения: {player['losses']}\n"
        f"Винрейт: {winrate}%\n"
        f"Турниров сыграно: {player['tournaments_played']}\n"
        f"Турниров выиграно: {player['tournaments_won']}\n"
        f"Текущая серия: {player['current_streak']}\n"
        f"Лучшая серия: {player['best_streak']}"
    )

    from database import get_user_achievements
    achievements = await get_user_achievements(user_id)

    if achievements:
        text += "\n\nДостижения:\n"
        for a in achievements:
            text += f"  {a['achievement_name']}\n"

    await message.answer(text)


@router.message(Command("leaderboard"))
async def leaderboard_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    chat_id = message.chat.id
    players = await get_leaderboard(chat_id, limit=10)

    if not players:
        await message.answer("Пока нет данных о рейтинге.")
        return

    medals = ["", "", ""]
    text = "Таблица лидеров:\n\n"

    for i, p in enumerate(players):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {p['user_id']} — ELO: {p['elo']} (W:{p['wins']} L:{p['losses']})\n"

    await message.answer(text)


class CreateClan(StatesGroup):
    name = State()
    tag = State()
    description = State()
    confirm = State()


@router.message(Command("clans"))
async def clans_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    chat_id = message.chat.id
    clans = await get_clans(chat_id)

    if not clans:
        await message.answer("Пока нет кланов.")
        return

    text = "Кланы:\n\n"
    for c in clans:
        count = await get_clan_member_count(c['id'])
        text += f"[{c['tag']}] {c['name']} — ELO: {c['elo']} ({count} чел.)\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мой клан", callback_data="my_clan")],
        [InlineKeyboardButton(text="Создать клан", callback_data="create_clan_start")],
    ])
    await message.answer(text, reply_markup=kb)


@router.message(Command("clan"))
async def clan_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    clan = await get_user_clan(user_id, chat_id)
    if not clan:
        await message.answer("Вы не в клане. Используйте /clans чтобы присоединиться.")
        return

    members = await get_clan_members(clan['id'])
    count = len(members)

    text = (
        f"Клан: [{clan['tag']}] {clan['name']}\n"
        f"Описание: {clan['description']}\n"
        f"ELO: {clan['elo']}\n"
        f"Победы: {clan['wins']} | Поражения: {clan['losses']}\n"
        f"Участники: {count}\n\n"
        f"Участники:\n"
    )

    for m in members:
        role = " " if m['role'] == 'leader' else " "
        name = str(m['user_id'])
        text += f"  {role} {name} (ELO: {m['elo'] or 1000})\n"

    await message.answer(text)


@router.callback_query(F.data == "my_clan")
async def my_clan_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    clan = await get_user_clan(user_id, chat_id)
    if not clan:
        await callback.message.answer("Вы не в клане.")
        await callback.answer()
        return

    members = await get_clan_members(clan['id'])
    count = len(members)

    text = (
        f"Клан: [{clan['tag']}] {clan['name']}\n"
        f"ELO: {clan['elo']}\n"
        f"Участники: {count}\n\n"
        f"Участники:\n"
    )

    for m in members:
        role = " " if m['role'] == 'leader' else " "
        name = str(m['user_id'])
        text += f"  {role} {name}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Покинуть клан", callback_data="leave_clan_confirm")]
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "create_clan_start")
async def create_clan_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название клана:")
    await state.set_state(CreateClan.name)
    await callback.answer()


@router.message(CreateClan.name)
async def clan_name(message: Message, state: FSMContext):
    from aiogram.fsm.context import FSMContext
    await state.update_data(name=message.text)
    await message.answer("Введите тег клана (2-5 символов, например [SF]):")
    await state.set_state(CreateClan.tag)


@router.message(CreateClan.tag)
async def clan_tag(message: Message, state: FSMContext):
    tag = message.text.strip("[] ")
    if len(tag) < 2 or len(tag) > 5:
        await message.answer("Тег должен быть 2-5 символов:")
        return
    await state.update_data(tag=tag)
    await message.answer("Введите описание клана (или 'пропустить'):")
    await state.set_state(CreateClan.description)


@router.message(CreateClan.description)
async def clan_desc(message: Message, state: FSMContext):
    desc = message.text if message.text.lower() != "пропустить" else ""
    await state.update_data(description=desc)

    data = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать", callback_data="confirm_clan"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_clan"),
        ]
    ])
    await message.answer(
        f"Создать клан?\n\n"
        f"Название: {data['name']}\n"
        f"Тег: [{data['tag']}]\n"
        f"Описание: {data['description'] or 'нет'}",
        reply_markup=kb
    )
    await state.set_state(CreateClan.confirm)


@router.callback_query(F.data == "confirm_clan", CreateClan.confirm)
async def confirm_clan(callback: CallbackQuery, state: FSMContext):
    from aiogram.fsm.context import FSMContext
    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    data = await state.get_data()
    user_id = callback.from_user.id

    existing = await get_user_clan(user_id, chat_id)
    if existing:
        await callback.message.answer("Вы уже в клане! Сначала покиньте его.")
        await callback.answer()
        return

    clan_id = await create_clan(
        name=data['name'],
        tag=data['tag'],
        chat_id=chat_id,
        leader_id=user_id,
        description=data['description']
    )

    if clan_id:
        await state.clear()
        await callback.message.answer(f"Клан [{data['tag']}] {data['name']} создан!")
    else:
        await callback.message.answer("Ошибка при создании клана. Возможно, клан с таким названием уже есть.")

    await callback.answer()


@router.callback_query(F.data == "cancel_clan")
async def cancel_clan(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Создание клана отменено.")
    await callback.answer()


@router.message(Command("clan_join"))
async def clan_join_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /clan_join <ID клана>")
        return

    try:
        clan_id = int(args[1])
    except ValueError:
        await message.answer("Неверный ID клана.")
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    existing = await get_user_clan(user_id, chat_id)
    if existing:
        await message.answer("Вы уже в клане! Сначала покиньте /clan_leave.")
        return

    clan = await get_clan(clan_id)
    if not clan:
        await message.answer("Клан не найден.")
        return

    if clan['chat_id'] != chat_id:
        await message.answer("Этот клан не в этом чате.")
        return

    success = await join_clan(clan_id, user_id)
    if success:
        await message.answer(f"Вы вступили в клан [{clan['tag']}] {clan['name']}!")
    else:
        await message.answer("Не удалось вступить в клан.")


@router.message(Command("clan_leave"))
async def clan_leave_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    clan = await get_user_clan(user_id, chat_id)
    if not clan:
        await message.answer("Вы не в клане.")
        return

    if clan['leader_id'] == user_id:
        await message.answer("Лидер не может покинуть клан. Передайте лидерство или удалите клан.")
        return

    success = await leave_clan(user_id, chat_id)
    if success:
        await message.answer("Вы покинули клан.")
    else:
        await message.answer("Не удалось покинуть клан.")


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
