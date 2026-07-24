from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from handlers.admin import is_admin
from database import (
    get_events, get_active_polls, get_poll, vote, get_poll_results,
    get_active_tournaments, get_tournament, join_tournament, leave_tournament,
    get_tournament_participants, get_participant_count, get_tournament_standings,
    get_setting, get_chat_id, track_chat_member,
    get_or_create_player, get_leaderboard, get_player_stats,
    create_clan, get_clan, get_user_clan, join_clan, leave_clan,
    get_clan_members, get_clans, get_clan_member_count,
    grant_clan_creation, has_clan_creation_permission, revoke_clan_creation,
    delete_clan, get_clan_leader,
    get_user_coins, claim_daily, place_bet, get_match_bets,
    add_quiz, get_random_quiz, place_prediction, get_leaderboard_coins,
    get_tournament_matches, get_tournament_analytics, get_match_stats,
    get_known_users_count, get_player_coefficient,
    check_match_exists, create_match, get_user_name, get_balance_history,
    get_user_recent_matches, get_pending_challenge_matches, get_unfought_opponents,
    get_tournaments_with_unfought, get_tournament_participants, ACHIEVEMENTS, aiosqlite, DB_NAME
)

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and configured and str(message.chat.id) != str(configured):
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
        "/new_clan - Создать клан (нужно разрешение)\n"
        "/clan_join <ID> - Вступить в клан\n"
        "/clan_leave - Покинуть клан\n"
        "/daily - Ежедневный бонус +50 монет\n"
        "/balance - Баланс монет\n"
        "/coins_top - Топ богачей\n"
        "/cancel - Отменить действие\n"
        "/help - Помощь"
    )


@router.message(Command("profile"))
async def profile_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    else:
        target_user = message.from_user

    user_id = target_user.id
    chat_id = message.chat.id

    player = await get_or_create_player(user_id, chat_id)

    total_games = player['wins'] + player['losses']
    winrate = (player['wins'] * 100 // total_games) if total_games > 0 else 0

    text = (
        f"Профиль: {target_user.full_name}\n\n"
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

    kb_buttons = [
        [InlineKeyboardButton(text="Последние бои", callback_data=f"recent_{user_id}")]
    ]

    if user_id == message.from_user.id:
        active_tournaments = await get_tournaments_with_unfought(user_id)
        if active_tournaments:
            kb_buttons.append([InlineKeyboardButton(text="Нужен поединок", callback_data=f"challenge_{active_tournaments[0]['id']}")])

    chat_id = await get_chat_id()
    if chat_id:
        clan = await get_user_clan(user_id, chat_id)
        if clan:
            kb_buttons.append([InlineKeyboardButton(text="Клан", callback_data=f"clan_info_{clan['id']}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await message.answer(text, reply_markup=kb)


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
        name = await get_user_name(p['user_id'])
        link = f'<a href="tg://user?id={p["user_id"]}">{name}</a>'
        text += f"{medal} {link} — ELO: {p['elo']} (W:{p['wins']} L:{p['losses']})\n"

    await message.answer(text, parse_mode="HTML")


class CreateClan(StatesGroup):
    name = State()
    tag = State()
    description = State()
    image = State()
    confirm = State()


class BetState(StatesGroup):
    amount = State()


class MatchScreenshot(StatesGroup):
    waiting = State()


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        return
    await state.clear()
    await message.answer("Действие отменено.")


@router.message(Command("clans"))
async def clans_cmd(message: Message):
    configured = await get_chat_id()
    if message.chat.type != "private" and str(message.chat.id) != str(configured):
        return

    chat_id = configured
    clans = await get_clans(chat_id)

    if not clans:
        await message.answer("Пока нет кланов.")
        return

    text = "Кланы:\n\n"
    for c in clans:
        count = await get_clan_member_count(c['id'])
        leader_name = await get_user_name(c['leader_id'])
        leader_link = f'<a href="tg://user?id={c["leader_id"]}">{leader_name}</a>'
        text += f"[{c['tag']}] {c['name']} — ELO: {c['elo']} ({count} чел.) Лидер: {leader_link}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мой клан", callback_data="my_clan")],
        [InlineKeyboardButton(text="Создать клан", callback_data="create_clan_start")],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


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
        name = await get_user_name(m['user_id'])
        link = f'<a href="tg://user?id={m["user_id"]}">{name}</a>'
        text += f"  {role} {link} (ELO: {m['elo'] or 1000})\n"

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "my_clan")
async def my_clan_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = await get_chat_id()

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
        name = await get_user_name(m['user_id'])
        link = f'<a href="tg://user?id={m["user_id"]}">{name}</a>'
        text += f"  {role} {link}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Покинуть клан", callback_data="leave_clan_confirm")]
    ])
    if clan['image']:
        await callback.message.answer_photo(photo=clan['image'], caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("clan_info_"))
async def clan_info_callback(callback: CallbackQuery):
    clan_id = int(callback.data.split("_")[2])
    clan = await get_clan(clan_id)
    if not clan:
        await callback.answer("Клан не найден!", show_alert=True)
        return

    members = await get_clan_members(clan_id)
    count = await get_clan_member_count(clan_id)

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
        name = await get_user_name(m['user_id'])
        link = f'<a href="tg://user?id={m["user_id"]}">{name}</a>'
        text += f"  {role} {link} (ELO: {m['elo'] or 1000})\n"

    if clan['image']:
        await callback.message.answer_photo(photo=clan['image'], caption=text, parse_mode="HTML")
    else:
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "create_clan_start")
async def create_clan_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название клана:")
    await state.set_state(CreateClan.name)
    await callback.answer()


@router.message(CreateClan.name)
async def clan_name(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    await state.update_data(name=message.text)
    await message.answer("Введите тег клана (2-5 символов, например [SF]):")
    await state.set_state(CreateClan.tag)


@router.message(CreateClan.tag)
async def clan_tag(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    tag = message.text.strip("[] ")
    if len(tag) < 2 or len(tag) > 5:
        await message.answer("Тег должен быть 2-5 символов:")
        return
    await state.update_data(tag=tag)
    await message.answer("Введите описание клана (или 'пропустить'):")
    await state.set_state(CreateClan.description)


@router.message(CreateClan.description)
async def clan_desc(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    desc = message.text if message.text.lower() != "пропустить" else ""
    await state.update_data(description=desc)
    await message.answer("Отправьте фото клана (или 'пропустить'):")
    await state.set_state(CreateClan.image)


@router.message(CreateClan.image)
async def clan_image(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    if message.photo:
        image = message.photo[-1].file_id
    elif message.text and message.text.lower() == "пропустить":
        image = None
    else:
        await message.answer("Отправьте фото или 'пропустить':")
        return
    await state.update_data(image=image)

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
        description=data['description'],
        image=data.get('image')
    )

    if clan_id:
        await revoke_clan_creation(user_id)
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
    if not configured:
        await message.answer("Чат не настроен!")
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
    chat_id = configured

    existing = await get_user_clan(user_id, chat_id)
    if existing:
        await message.answer("Вы уже в клане! Сначала покиньте /clan_leave.")
        return

    clan = await get_clan(clan_id)
    if not clan:
        await message.answer("Клан не найден.")
        return

    if str(clan['chat_id']) != str(chat_id):
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


@router.message(Command("new_clan"))
async def new_clan_cmd(message: Message, state: FSMContext):
    configured = await get_chat_id()
    if not configured:
        await message.answer("Чат не настроен!")
        return

    user_id = message.from_user.id
    chat_id = configured

    existing = await get_user_clan(user_id, chat_id)
    if existing:
        await message.answer("Вы уже в клане! Сначала покиньте его.")
        return

    has_perm = await has_clan_creation_permission(user_id)
    if not has_perm:
        await message.answer("У вас нет разрешения на создание клана. Попросите администратора выдать разрешение.")
        return

    await message.answer("Введите название клана:")
    await state.set_state(CreateClan.name)


@router.message(Command("grant_clan"))
async def grant_clan_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("Ответьте на сообщение пользователя, чтобы выдать разрешение на создание клана.")
        return

    target_id = message.reply_to_message.from_user.id
    await grant_clan_creation(target_id, message.from_user.id)

    from database import get_user_name
    name = await get_user_name(target_id)
    link = f'<a href="tg://user?id={target_id}">{name}</a>'
    await message.answer(f"Разрешение на создание клана выдано: {link}", parse_mode="HTML")


@router.message(Command("addcoins"))
async def addcoins_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("Ответьте на сообщение пользователя командой /addcoins <сумма>")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите сумму: /addcoins 100")
        return

    try:
        amount = int(args[1])
        if amount <= 0:
            await message.answer("Сумма должна быть > 0")
            return
    except ValueError:
        await message.answer("Неверная сумма.")
        return

    target_id = message.reply_to_message.from_user.id
    from database import add_coins
    await add_coins(target_id, amount, f"Выдано админом {message.from_user.id}")

    name = await get_user_name(target_id)
    link = f'<a href="tg://user?id={target_id}">{name}</a>'
    await message.answer(f"+{amount} монет → {link}", parse_mode="HTML")


@router.message(Command("removecoins"))
async def removecoins_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("Ответьте на сообщение пользователя командой /removecoins <сумма>")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите сумму: /removecoins 100")
        return

    try:
        amount = int(args[1])
        if amount <= 0:
            await message.answer("Сумма должна быть > 0")
            return
    except ValueError:
        await message.answer("Неверная сумма.")
        return

    target_id = message.reply_to_message.from_user.id
    from database import remove_coins
    ok = await remove_coins(target_id, amount, f"Списано админом {message.from_user.id}")

    name = await get_user_name(target_id)
    link = f'<a href="tg://user?id={target_id}">{name}</a>'
    if ok:
        await message.answer(f"-{amount} монет → {link}", parse_mode="HTML")
    else:
        await message.answer("Недостаточно монет у пользователя.")


@router.message(Command("clan_delete"))
async def clan_delete_cmd(message: Message):
    configured = await get_chat_id()
    if not configured:
        await message.answer("Чат не настроен!")
        return

    user_id = message.from_user.id
    chat_id = configured

    clan = await get_user_clan(user_id, chat_id)
    if not clan:
        await message.answer("Вы не в клане.")
        return

    is_leader = clan['leader_id'] == user_id
    if not is_leader and not is_admin(user_id):
        await message.answer("Только лидер клана или администратор может удалить клан.")
        return

    await delete_clan(clan['id'])
    await message.answer(f"Клан [{clan['tag']}] {clan['name']} удалён.")


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
        "- Просматривать события и голосования\n"
        "- Записываться на турниры\n"
        "- Смотреть турнирную сетку\n"
        "- Ставить монеты на победителей матчей\n"
        "- Ежедневный бонус +50 монет\n"
        "- Создавать кланы"
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

    if tournament['status'] == 'in_progress':
        user_id = callback.from_user.id
        is_joined = any(p['user_id'] == user_id for p in participants)
        if is_joined:
            kb_buttons.append([InlineKeyboardButton(text="Вызвать соперника", callback_data=f"challenge_{tournament_id}")])

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


@router.callback_query(F.data.startswith("challenge_"))
async def challenge_opponent(callback: CallbackQuery, state: FSMContext):
    tournament_id = int(callback.data.split("_")[1])
    tournament = await get_tournament(tournament_id)

    if not tournament or tournament['status'] != 'in_progress':
        await callback.answer("Турнир не активен!", show_alert=True)
        return

    user_id = callback.from_user.id
    participants = await get_tournament_participants(tournament_id)
    is_joined = any(p['user_id'] == user_id for p in participants)
    if not is_joined:
        await callback.answer("Вы не участвуете в этом турнире!", show_alert=True)
        return

    matches = await get_tournament_matches(tournament_id)
    fought_ids = set()
    for m in matches:
        if m['player1_id'] == user_id and m['winner_id'] is not None:
            fought_ids.add(m['player2_id'])
        elif m['player2_id'] == user_id and m['winner_id'] is not None:
            fought_ids.add(m['player1_id'])

    available = [p for p in participants if p['user_id'] != user_id and p['user_id'] not in fought_ids]
    if not available:
        await callback.answer("Нет доступных соперников! Вы уже со всеми сыграли.", show_alert=True)
        return

    await state.update_data(challenge_tournament_id=tournament_id)
    kb_buttons = []
    for p in available:
        name = p['display_name'] or p['username'] or str(p['user_id'])
        kb_buttons.append([InlineKeyboardButton(text=name, callback_data=f"chall_{tournament_id}_{p['user_id']}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Выберите соперника:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("chall_"))
async def confirm_challenge(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    tournament_id = int(parts[1])
    opponent_id = int(parts[2])
    user_id = callback.from_user.id

    participants = await get_tournament_participants(tournament_id)
    me = next((p for p in participants if p['user_id'] == user_id), None)
    opp = next((p for p in participants if p['user_id'] == opponent_id), None)

    if not me or not opp:
        await callback.answer("Участник не найден!", show_alert=True)
        return

    existing = await check_match_exists(tournament_id, user_id, opponent_id)
    if existing:
        await callback.answer("Вы уже сражались!", show_alert=True)
        return

    matches = await get_tournament_matches(tournament_id)
    round_num = 1
    match_num = len([m for m in matches if m['round_num'] == round_num]) + 1

    match_id = await create_match(
        tournament_id=tournament_id,
        player1_id=user_id,
        player2_id=opponent_id,
        round_num=round_num,
        match_num=match_num
    )

    my_name = me['display_name'] or me['username'] or str(user_id)
    opp_name = opp['display_name'] or opp['username'] or str(opponent_id)

    my_link = f'<a href="tg://user?id={user_id}">{my_name}</a>'
    opp_link = f'<a href="tg://user?id={opponent_id}">{opp_name}</a>'

    chat_id = await get_chat_id()
    if chat_id:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{my_name} победил", callback_data=f"set_winner_{match_id}_{user_id}")],
            [InlineKeyboardButton(text=f"{opp_name} победил", callback_data=f"set_winner_{match_id}_{opponent_id}")],
            [InlineKeyboardButton(text=f"Ставка на {my_name}", callback_data=f"betch_{match_id}_{user_id}")],
            [InlineKeyboardButton(text=f"Ставка на {opp_name}", callback_data=f"betch_{match_id}_{opponent_id}")],
            [InlineKeyboardButton(text="Отправить скриншот", callback_data=f"send_screenshot_{match_id}")],
        ])

        await bot.send_message(
            chat_id=chat_id,
            text=f"Поединок (вызов)!\n\n{my_link} vs {opp_link}\n\nКто победил?",
            reply_markup=kb,
            parse_mode="HTML"
        )

    tournament = await get_tournament(tournament_id)
    tournament_name = tournament['name'] if tournament else "Неизвестный турнир"
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Вызов на поединок!\n\n{my_link} vs {opp_link}\n\nТурнир: {tournament_name}",
        parse_mode="HTML"
    )

    await callback.answer("Поединок создан!", show_alert=True)


@router.callback_query(F.data.startswith("send_screenshot_"))
async def send_screenshot_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    match_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    from database import get_match
    match = await get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return

    if user_id != match['player1_id'] and user_id != match['player2_id']:
        await callback.answer("Вы не участник этого матча!", show_alert=True)
        return

    if user_id == match['player1_id'] and match['screenshot1']:
        await callback.answer("Вы уже отправили скриншот!", show_alert=True)
        return

    if user_id == match['player2_id'] and match['screenshot2']:
        await callback.answer("Вы уже отправили скриншот!", show_alert=True)
        return

    await state.update_data(match_id=match_id)
    await state.set_state(MatchScreenshot.waiting)

    try:
        await bot.send_message(
            chat_id=user_id,
            text="Отправьте скриншот результата матча (одно фото):"
        )
        await callback.answer()
    except Exception:
        await callback.answer("Начните диалог с ботом, чтобы отправить скриншот!", show_alert=True)


@router.message(MatchScreenshot.waiting, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    match_id = data['match_id']
    user_id = message.from_user.id
    file_id = message.photo[-1].file_id

    from database import save_match_screenshot, get_match, get_tournament, get_user_name
    ok = await save_match_screenshot(match_id, user_id, file_id)
    if not ok:
        await message.answer("Ошибка при сохранении скриншота.")
        await state.clear()
        return

    match = await get_match(match_id)
    tournament = await get_tournament(match['tournament_id'])

    p1_name = await get_user_name(match['player1_id'])
    p2_name = await get_user_name(match['player2_id'])
    p1_link = f'<a href="tg://user?id={match["player1_id"]}">{p1_name}</a>'
    p2_link = f'<a href="tg://user?id={match["player2_id"]}">{p2_name}</a>'
    sender_name = await get_user_name(user_id)
    sender_link = f'<a href="tg://user?id={user_id}">{sender_name}</a>'

    caption = (
        f"Скриншот матча!\n\n"
        f"{p1_link} vs {p2_link}\n"
        f"Турнир: {tournament['name']}\n\n"
        f"Отправил: {sender_link}"
    )

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await message.answer("Скриншот отправлен администратору!")
    await state.clear()


@router.message(MatchScreenshot.waiting)
async def receive_screenshot_wrong(message: Message):
    await message.answer("Отправьте именно одно фото (скриншот):")


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


@router.message(Command("daily"))
async def cmd_daily(message: Message):
    balance, already, time_left = await claim_daily(message.from_user.id)
    if already is not None:
        await message.answer(
            f"Ты уже получал бонус сегодня!\n"
            f"Баланс: {already} монет\n"
            f"Доступно через: {time_left}"
        )
    else:
        await message.answer(
            f"Ежедневный бонус получен! +50 монет\n"
            f"Баланс: {balance} монет"
        )


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    target_id = message.from_user.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id

    coins = await get_user_coins(target_id)
    name = await get_user_name(target_id)
    link = f'<a href="tg://user?id={target_id}">{name}</a>'

    text = (
        f"Профиль: {link}\n\n"
        f"Баланс: {coins['balance']} монет\n"
        f"Выиграно: {coins['total_won']} | Проиграно: {coins['total_lost']}"
    )

    kb_buttons = []
    if target_id == message.from_user.id:
        kb_buttons.append([InlineKeyboardButton(text="Ежедневный бонус", callback_data="daily_btn")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons) if kb_buttons else None
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "daily_btn")
async def daily_button(callback: CallbackQuery):
    balance, already, time_left = await claim_daily(callback.from_user.id)
    if already is not None:
        await callback.answer(f"Уже получал сегодня! Доступно через: {time_left}", show_alert=True)
    else:
        await callback.answer(f"Бонус получен! +50 монет. Баланс: {balance}", show_alert=True)


@router.message(Command("coins"))
async def cmd_coins(message: Message):
    coins = await get_user_coins(message.from_user.id)
    await message.answer(
        f"Монеты: {coins['balance']}\n\n"
        f"Команды:\n"
        f"/daily - бонус +50\n"
        f"/balance - баланс\n"
        f"/coins_top - рейтинг"
    )


@router.message(Command("quiz"))
async def cmd_quiz(message: Message):
    chat_id = message.chat.id
    quiz = await get_random_quiz(chat_id)
    if not quiz:
        await message.answer("Пока нет вопросов. Админ может добавить через /addquiz")
        return

    kb_buttons = []
    for i, opt in enumerate(quiz['options']):
        cb = f"qz{quiz['id']}x{i}"
        kb_buttons.append([InlineKeyboardButton(text=opt, callback_data=cb)])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    await message.answer(f"Викторина:\n\n{quiz['question']}", reply_markup=kb)


@router.callback_query(F.data.startswith("qz"))
async def quiz_answer(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("x")
    quiz_id = int(parts[0][2:])
    chosen = int(parts[1])

    from database import aiosqlite, DB_NAME, close_quiz
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT correct_index, is_closed FROM quizzes WHERE id = ?", (quiz_id,))
        row = await cursor.fetchone()
        if not row:
            await callback.answer("Вопрос не найден")
            return
        correct, is_closed = row

    if is_closed:
        await callback.answer("Этот вопрос уже закрыт!", show_alert=True)
        return

    if chosen == correct:
        from database import add_coins, get_user_name
        await add_coins(callback.from_user.id, 20, "Викторина")
        await close_quiz(quiz_id)
        await callback.message.edit_text("Правильно! +20 монет")
        await callback.answer()

        user = callback.from_user
        name = user.first_name or user.username or str(user.id)
        link = f'<a href="tg://user?id={user.id}">{name}</a>'
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f'{link} правильно ответил на вопрос викторины и получил +20 монет!',
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("Неверно! Попробуй следующий раз.")
        await callback.answer()


@router.message(Command("coins_top"))
async def cmd_coins_top(message: Message):
    leaders = await get_leaderboard_coins(10)
    if not leaders:
        await message.answer("Пока нет данных.")
        return

    from database import get_user_name
    text = "Топ по монетам:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, l in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = await get_user_name(l['user_id'])
        link = f'<a href="tg://user?id={l["user_id"]}">{name}</a>'
        text += f"{medal} {link} - {l['balance']} монет\n"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("bet"))
async def cmd_bet(message: Message):
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("Формат: /bet [сумма] [match_id] [user_id]")
        return

    try:
        amount = int(parts[1])
        match_id = int(parts[2])
        bet_on = int(parts[3])
    except ValueError:
        await message.answer("Неверный формат. Используйте числа.")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть положительной.")
        return

    ok = await place_bet(message.from_user.id, match_id, bet_on, amount)
    if ok:
        coins = await get_user_coins(message.from_user.id)
        bet_name = await get_user_name(bet_on)
        bet_link = f'<a href="tg://user?id={bet_on}">{bet_name}</a>'
        await message.answer(
            f"Ставка принята!\n"
            f"Поставлено: {amount} монет\n"
            f"На игрока: {bet_link}\n"
            f"Остаток: {coins['balance']} монет",
            parse_mode="HTML"
        )
    else:
        await message.answer("Недостаточно монет или ошибка!")


@router.callback_query(F.data.startswith("betch_"))
async def bet_by_button(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    match_id = int(parts[1])
    bet_on = int(parts[2])

    coins = await get_user_coins(callback.from_user.id)
    if not coins or coins['balance'] <= 0:
        await callback.answer("Недостаточно монет!", show_alert=True)
        return

    await state.update_data(
        bet_match_id=match_id,
        bet_on=bet_on,
        bet_balance=coins['balance'],
        bet_user_id=callback.from_user.id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 монет", callback_data="bset_10")],
        [InlineKeyboardButton(text="25 монет", callback_data="bset_25")],
        [InlineKeyboardButton(text="50 монет", callback_data="bset_50")],
        [InlineKeyboardButton(text="100 монет", callback_data="bset_100")],
        [InlineKeyboardButton(text="Все монеты", callback_data=f"bset_{coins['balance']}")],
    ])

    await callback.message.answer(
        f"Ваш баланс: {coins['balance']} монет\n\nВыберите сумму ставки:",
        reply_markup=kb
    )
    await state.set_state(BetState.amount)
    await callback.answer()


@router.callback_query(F.data.startswith("bset_"), BetState.amount)
async def set_bet_amount(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    if callback.from_user.id != data.get('bet_user_id'):
        await callback.answer("Это не ваша ставка!", show_alert=True)
        return

    amount = int(callback.data.split("_")[1])

    if amount > data.get('bet_balance', 0):
        await callback.answer("Недостаточно монет!", show_alert=True)
        return

    ok = await place_bet(callback.from_user.id, data['bet_match_id'], data['bet_on'], amount)
    if ok:
        new_coins = await get_user_coins(callback.from_user.id)
        await callback.message.delete()
        await callback.message.answer(
            f"Ставка принята!\n"
            f"Поставлено: {amount} монет\n"
            f"Баланс: {new_coins['balance']} монет"
        )

        user = callback.from_user
        name = user.first_name or user.username or str(user.id)
        link = f'<a href="tg://user?id={user.id}">{name}</a>'
        from database import get_user_name
        bet_on_name = await get_user_name(data['bet_on'])
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f'{link} сделал ставку <b>{amount}</b> монет на <b>{bet_on_name}</b>',
            parse_mode="HTML"
        )
    else:
        await callback.answer("Ошибка ставки!", show_alert=True)

    await state.clear()
    await callback.answer()


@router.message(Command("mystats"))
async def cmd_mystats(message: Message):
    user_id = message.from_user.id
    stats = await get_player_stats(user_id)
    coins = await get_user_coins(user_id)
    elo_player = await get_or_create_player(user_id, message.chat.id)

    if not stats:
        await message.answer("Пока нет статистики. Сыграй хотя бы один турнир!")
        return

    text = (
        f"Статистика {message.from_user.first_name}:\n\n"
        f"ELO: {elo_player['elo']}\n"
        f"Побед: {stats['wins']} | Поражений: {stats['losses']}\n"
        f"Серия побед: {stats['win_streak']} (макс: {stats['max_win_streak']})\n"
        f"Турниров сыграно: {stats['tournaments_played']}\n"
        f"Турниров выиграно: {stats['tournaments_won']}\n"
        f"Монеты: {coins['balance']}"
    )
    await message.answer(text)


@router.message(Command("top"))
async def cmd_top(message: Message):
    leaders = await get_leaderboard(10)
    if not leaders:
        await message.answer("Пока нет данных.")
        return

    text = "Топ по ELO:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, l in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {l['display_name'] or l['username'] or l['user_id']} - ELO {l['elo']}\n"
    await message.answer(text)


@router.message(Command("tournament_stats"))
async def cmd_tournament_stats(message: Message):
    t_stats = await get_tournament_analytics()
    m_stats = await get_match_stats()

    text = "Статистика турниров:\n\n"

    if t_stats['top_winners']:
        text += "Победители турниров:\n"
        for i, w in enumerate(t_stats['top_winners'][:5], 1):
            name = await get_user_name(w['winner_id'])
            link = f'<a href="tg://user?id={w["winner_id"]}">{name}</a>'
            text += f"  {i}. {link} — {w['wins']} побед\n"

    if m_stats['top_match_winners']:
        text += "\nПобедители матчей:\n"
        for i, w in enumerate(m_stats['top_match_winners'][:5], 1):
            name = await get_user_name(w['winner_id'])
            link = f'<a href="tg://user?id={w["winner_id"]}">{name}</a>'
            text += f"  {i}. {link} — {w['wins']} побед\n"

    if not t_stats['top_winners'] and not m_stats['top_match_winners']:
        text += "Пока нет данных."

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("upf"))
async def user_profile(callback: CallbackQuery):
    user_id = int(callback.data[3:])

    from database import aiosqlite, DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT * FROM player_stats WHERE user_id = ?", (user_id,))
        stats = await cursor.fetchone()

        cursor = await db.execute("SELECT balance FROM user_coins WHERE user_id = ?", (user_id,))
        coins = await cursor.fetchone()

        cursor = await db.execute("SELECT * FROM achievements WHERE user_id = ?", (user_id,))
        achievements = await cursor.fetchall()

    name = await get_user_name(user_id)
    link = f'<a href="tg://user?id={user_id}">{name}</a>'
    text = f"Профиль: {link}\n\n"

    if stats:
        text += (
            f"ELO: {stats['elo']}\n"
            f"Побед: {stats['wins']} | Поражений: {stats['losses']}\n"
            f"Серия побед: {stats['win_streak']} (макс: {stats['max_win_streak']})\n"
            f"Турниров: {stats['tournaments_played']} (побед: {stats['tournaments_won']})\n"
        )
    else:
        text += "Нет статистики\n"

    if coins:
        text += f"Монеты: {coins['balance']}\n"

    if achievements:
        text += "\nДостижения:\n"
        from database import ACHIEVEMENTS
        for a in achievements:
            key = a['achievement']
            if key in ACHIEVEMENTS:
                text += f"  {ACHIEVEMENTS[key][0]}\n"

    kb_buttons = [
        [InlineKeyboardButton(text="Последние бои", callback_data=f"recent_{user_id}")]
    ]

    if user_id == callback.from_user.id:
        active_tournaments = await get_tournaments_with_unfought(user_id)
        if active_tournaments:
            kb_buttons.append([InlineKeyboardButton(text="Нужен поединок", callback_data=f"challenge_{active_tournaments[0]['id']}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("recent_"))
async def recent_matches(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    matches = await get_user_recent_matches(user_id, 5)

    name = await get_user_name(user_id)
    link = f'<a href="tg://user?id={user_id}">{name}</a>'
    text = f"Последние бои {link}:\n\n"

    if not matches:
        text += "Пока нет завершённых поединков."
    else:
        for m in matches:
            is_p1 = m['player1_id'] == user_id
            opponent_id = m['player2_id'] if is_p1 else m['player1_id']
            opponent_name = await get_user_name(opponent_id)
            result = "Победа" if m['winner_id'] == user_id else "Поражение"
            icon = "+" if m['winner_id'] == user_id else "-"
            text += f"{icon} vs {opponent_name} — {result} ({m['tournament_name']})\n"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


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
