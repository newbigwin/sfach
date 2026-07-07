from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import (
    add_event, get_events, delete_event, add_poll, get_active_polls,
    get_poll, vote, get_poll_results, close_poll, get_event,
    create_tournament, get_tournament, get_active_tournaments, start_tournament,
    get_tournament_participants, get_participant_count, finish_tournament,
    create_match, get_match, set_match_winner, get_tournament_matches,
    get_tournament_standings, delete_tournament, set_setting, get_setting
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


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def get_chat_id():
    return await get_setting("chat_id")


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="События", callback_data="admin_events")],
        [InlineKeyboardButton(text="Голосования", callback_data="admin_polls")],
        [InlineKeyboardButton(text="Турниры", callback_data="admin_tournaments")],
        [InlineKeyboardButton(text="Утихомирить всех", callback_data="mute_all")],
        [InlineKeyboardButton(text="Созвать всех", callback_data="summon_all")],
        [InlineKeyboardButton(text="Мануал", callback_data="admin_manual")],
    ])


async def check_chat_id(message_or_callback):
    chat_id = await get_chat_id()
    if not chat_id:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer("Сначала настройте чат командой /setchat в группе!")
        else:
            await message_or_callback.message.answer("Сначала настройте чат командой /setchat в группе!")
            await message_or_callback.answer()
        return False
    return True


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.chat.type != "private":
        return

    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "Панель администратора\n\n"
        "Все действия выполняются здесь, в личных сообщениях.\n"
        "Результаты публикуются в чате автоматически.",
        reply_markup=admin_keyboard()
    )


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


@router.callback_query(F.data == "admin_manual")
async def admin_manual(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await callback.message.answer(
        "Мануал администратора\n\n"
        "ПЕРВЫЙ ШАГ\n"
        "1. Добавьте бота в группу\n"
        "2. Напишите /setchat в группе\n"
        "3. Бот запомнит чат для публикаций\n\n"
        "СОБЫТИЯ\n"
        "- Создать событие — создаёт пост в чате\n"
        "- Список событий — просмотр и удаление\n\n"
        "ГОЛОСОВАНИЯ\n"
        "- Создать голосование — опрос для участников\n"
        "  Типы: за событие, за время, общее\n"
        "  Варианты указываются своими\n"
        "- Активные голосования — просмотр и закрытие\n\n"
        "ТУРНИРЫ\n"
        "- Создать турнир — настройка нового турнира\n"
        "- Начать турнир — открытие записи\n"
        "- Создать поединок — выбор двух бойцов\n"
        "- Указать победителя — фиксация результата\n"
        "- Турнирная сетка — таблица побед/поражений\n"
        "- Завершить турнир — объявление победителя\n\n"
        "МОДЕРАЦИЯ\n"
        "- Утихомирить всех — мут не-админов\n"
        "- Созвать всех — упомянуть всех\n\n"
        "СМЕНА ЧАТА\n"
        "Чтобы сменить чат, напишите /setchat в новом чате.",
        reply_markup=admin_keyboard()
    )
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
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="confirm_event"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_event"),
        ]
    ])

    await message.answer(
        f"Подтвердите:\n\n"
        f"Название: {data['title']}\n"
        f"Описание: {data['description']}\n"
        f"Дата: {data['event_date']}",
        reply_markup=kb
    )
    await state.set_state(CreateEvent.confirm)


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
        chat_id=chat_id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проголосовать", callback_data=f"vote_event_{event_id}")]
    ])

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"{data['title']}\n\n"
            f"{data['description']}\n\n"
            f"Дата: {data['event_date']}\n\n"
            f"Голосуйте, если хотите участвовать:"
        ),
        reply_markup=kb
    )

    await state.clear()
    await callback.message.answer("Событие опубликовано в чате!")
    await callback.answer()


@router.callback_query(F.data == "cancel_event")
async def cancel_event(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.message.answer("Создание отменено.")
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
        [InlineKeyboardButton(text="Буду участвовать", callback_data=f"vote_{poll_id}_0")],
        [InlineKeyboardButton(text="Не смогу", callback_data=f"vote_{poll_id}_1")],
        [InlineKeyboardButton(text="Посмотрю", callback_data=f"vote_{poll_id}_2")],
    ])

    await callback.message.edit_reply_markup(reply_markup=kb)
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
                text=f"Удалить: {event['title'][:20]}",
                callback_data=f"delete_event_{event['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_events")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("События:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    await delete_event(event_id)
    await callback.message.answer("Событие удалено.")
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
        chat_id=chat_id
    )

    kb_buttons = []
    for i, opt in enumerate(data['options']):
        kb_buttons.append([InlineKeyboardButton(text=opt, callback_data=f"vote_{poll_id}_{i}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    await bot.send_message(
        chat_id=chat_id,
        text=f"Голосование: {data['question']}",
        reply_markup=kb
    )

    await state.clear()
    await callback.message.answer("Голосование опубликовано в чате!")
    await callback.answer()


@router.callback_query(F.data == "cancel_poll")
async def cancel_poll(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.message.answer("Создание отменено.")
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


@router.callback_query(F.data == "list_polls")
async def list_polls(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    polls = await get_active_polls(0)

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

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_polls")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Голосования:", reply_markup=kb)
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


@router.callback_query(F.data == "mute_all")
async def mute_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    muted_count = 0

    async for member in bot.get_chat_members(chat_id):
        if member.user.id == ADMIN_ID:
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

    chat_id = await get_chat_id()
    if not chat_id:
        await callback.message.answer("Сначала настройте чат командой /setchat в группе!")
        await callback.answer()
        return

    members = []

    async for member in bot.get_chat_members(chat_id):
        if member.user.id == ADMIN_ID:
            continue
        if member.user.is_bot:
            continue
        if member.status in ("creator", "administrator"):
            continue

        members.append(member.user.id)

    if not members:
        await callback.message.answer("Нет участников.")
        await callback.answer()
        return

    mentions = " ".join([f"[user](tg://user?id={uid})" for uid in members[:50]])

    await bot.send_message(
        chat_id=chat_id,
        text=f"Созыв!\n\n{mentions}\n\nПриглашаем принять участие!",
        parse_mode="Markdown"
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
        f"Макс: {data['max_participants']}",
        reply_markup=kb
    )
    await state.set_state(CreateTournament.confirm)


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
        chat_id=chat_id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Записаться", callback_data=f"join_tournament_{tournament_id}")]
    ])

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"{data['name']}\n\n"
            f"{data['description']}\n\n"
            f"Макс. участников: {data['max_participants']}\n\n"
            f"Записывайтесь!"
        ),
        reply_markup=kb
    )

    await state.clear()
    await callback.message.answer("Турнир опубликован в чате!")
    await callback.answer()


@router.callback_query(F.data == "cancel_tournament")
async def cancel_tournament(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.message.answer("Создание отменено.")
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
                callback_data=f"tournament_{t['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_tournaments")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer("Турниры:", reply_markup=kb)
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
        kb_buttons.append([InlineKeyboardButton(text="Удалить", callback_data=f"delete_tournament_{tournament_id}")])
    elif tournament['status'] == 'in_progress':
        kb_buttons.append([InlineKeyboardButton(text="Создать поединок", callback_data=f"create_match_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Результаты", callback_data=f"match_list_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Сетка", callback_data=f"standings_{tournament_id}")])
        kb_buttons.append([InlineKeyboardButton(text="Завершить", callback_data=f"finish_tournament_{tournament_id}")])

    kb_buttons.append([InlineKeyboardButton(text="Назад", callback_data="list_tournaments")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


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

    mentions = " ".join([f"[user](tg://user?id={p['user_id']})" for p in participants])

    await bot.send_message(
        chat_id=chat_id,
        text=f"Турнир \"{tournament['name']}\" начат!\n\nУчастники:\n{mentions}",
        parse_mode="Markdown"
    )
    await callback.message.answer("Турнир начат и объявлен в чате!")
    await callback.answer()


@router.callback_query(F.data.startswith("delete_tournament_"))
async def delete_tournament_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    tournament_id = int(callback.data.split("_")[2])
    await delete_tournament(tournament_id)
    await callback.message.answer("Турнир удален.")
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

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p1_name} победил", callback_data=f"set_winner_{match_id}_{data['player1_id']}")],
        [InlineKeyboardButton(text=f"{p2_name} победил", callback_data=f"set_winner_{match_id}_{data['player2_id']}")],
    ])

    await bot.send_message(
        chat_id=chat_id,
        text=f"Поединок!\n\n{p1_name} vs {p2_name}\n\nКто победил?",
        reply_markup=kb
    )

    await state.clear()
    await callback.message.answer("Поединок опубликован в чате!")
    await callback.answer()


@router.callback_query(F.data == "cancel_match")
async def cancel_match(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return

    await state.clear()
    await callback.message.answer("Создание отменено.")
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

        p1_name = (p1['display_name'] or p1['username'] or str(m['player1_id'])) if p1 else "TBD"
        p2_name = (p2['display_name'] or p2['username'] or str(m['player2_id'])) if p2 else "TBD"

        if m['status'] == 'finished':
            winner = next((p for p in participants if p['user_id'] == m['winner_id']), None)
            winner_name = winner['display_name'] or winner['username'] if winner else "TBD"
            text += f"Р{m['round_num']} П{m['match_num']}: {p1_name} vs {p2_name} -> {winner_name}\n"
        else:
            text += f"Р{m['round_num']} П{m['match_num']}: {p1_name} vs {p2_name} (ожидает)\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"tournament_{tournament_id}")]
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
        [InlineKeyboardButton(text="Назад", callback_data=f"tournament_{tournament_id}")]
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("finish_tournament_"))
async def finish_tournament_handler(callback: CallbackQuery, bot: Bot):
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
    standings_data = await get_tournament_standings(tournament_id)

    if standings_data:
        winner = standings_data[0]
        winner_name = winner['display_name'] or winner['username'] or str(winner['user_id'])

        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"Турнир \"{tournament['name']}\" завершен!\n\n"
                f"Победитель: {winner_name}\n"
                f"Побед: {winner['wins']}"
            )
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Турнир \"{tournament['name']}\" завершен!"
        )

    await callback.message.answer("Турнир завершен и объявлен в чате!")
    await callback.answer()
