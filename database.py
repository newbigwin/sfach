import aiosqlite
from datetime import datetime, timedelta
from config import DB_NAME


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT,
                image_file_id TEXT,
                created_by INTEGER,
                chat_id INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                poll_type TEXT DEFAULT 'general',
                event_id INTEGER,
                image_file_id TEXT,
                created_by INTEGER,
                chat_id INTEGER,
                message_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (poll_id) REFERENCES polls(id),
                UNIQUE(poll_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                max_participants INTEGER DEFAULT 16,
                prize_places INTEGER DEFAULT 1,
                participation_award INTEGER DEFAULT 0,
                status TEXT DEFAULT 'registration',
                image_file_id TEXT,
                created_by INTEGER,
                chat_id INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournament_prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                place INTEGER NOT NULL,
                prize_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
                UNIQUE(tournament_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_members (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                username TEXT,
                display_name TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournament_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                display_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
                UNIQUE(tournament_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                player1_id INTEGER NOT NULL,
                player2_id INTEGER,
                winner_id INTEGER,
                round_num INTEGER DEFAULT 1,
                match_num INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
                FOREIGN KEY (player1_id) REFERENCES tournament_participants(user_id),
                FOREIGN KEY (player2_id) REFERENCES tournament_participants(user_id),
                FOREIGN KEY (winner_id) REFERENCES tournament_participants(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                created_by INTEGER,
                sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                tournaments_played INTEGER DEFAULT 0,
                tournaments_won INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                description TEXT,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, achievement_type)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tag TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                leader_id INTEGER NOT NULL,
                description TEXT DEFAULT '',
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans(id),
                UNIQUE(clan_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS recurring_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                photo TEXT,
                day_of_week INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER,
                last_created TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_coins (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 100,
                last_daily TIMESTAMP,
                total_won INTEGER DEFAULT 0,
                total_lost INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                bet_on_user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                resolved INTEGER DEFAULT 0,
                won INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_index INTEGER NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tournament_id INTEGER NOT NULL,
                predicted_winner_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                resolved INTEGER DEFAULT 0,
                won INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS known_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS balance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # Migration: add new columns to existing tables
        try:
            await db.execute("ALTER TABLE tournaments ADD COLUMN prize_places INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE tournaments ADD COLUMN participation_award INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE recurring_events ADD COLUMN photo TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE tournaments ADD COLUMN winner_id INTEGER")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE quizzes ADD COLUMN is_closed INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE quizzes ADD COLUMN image TEXT")
        except Exception:
            pass
        await db.commit()


async def set_setting(key, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        await db.commit()


async def get_setting(key, default=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default


async def get_chat_id():
    return await get_setting("chat_id")


async def add_reminder(chat_id, title, remind_at, created_by=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (chat_id, title, remind_at, created_by) VALUES (?, ?, ?, ?)",
            (chat_id, title, remind_at, created_by)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_reminders():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= datetime('now') ORDER BY remind_at"
        )
        return await cursor.fetchall()


async def mark_reminder_sent(reminder_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()


async def get_active_reminders(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE chat_id = ? AND sent = 0 ORDER BY remind_at",
            (chat_id,)
        )
        return await cursor.fetchall()


async def delete_reminder(reminder_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()


async def get_or_create_player(user_id, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM player_stats WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO player_stats (user_id, chat_id) VALUES (?, ?)",
                (user_id, chat_id)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM player_stats WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
        return row


async def update_player_stats(user_id, chat_id, elo_change, is_win):
    async with aiosqlite.connect(DB_NAME) as db:
        await get_or_create_player(user_id, chat_id)
        if is_win:
            await db.execute("""
                UPDATE player_stats SET 
                    elo = elo + ?,
                    wins = wins + 1,
                    current_streak = current_streak + 1,
                    best_streak = MAX(best_streak, current_streak + 1),
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (elo_change, user_id))
        else:
            await db.execute("""
                UPDATE player_stats SET 
                    elo = MAX(100, elo + ?),
                    losses = losses + 1,
                    current_streak = 0,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (elo_change, user_id))
        await db.commit()


async def update_tournament_stats(user_id, chat_id, won):
    async with aiosqlite.connect(DB_NAME) as db:
        await get_or_create_player(user_id, chat_id)
        if won:
            await db.execute("""
                UPDATE player_stats SET tournaments_played = tournaments_played + 1,
                    tournaments_won = tournaments_won + 1
                WHERE user_id = ?
            """, (user_id,))
        else:
            await db.execute("""
                UPDATE player_stats SET tournaments_played = tournaments_played + 1
                WHERE user_id = ?
            """, (user_id,))
        await db.commit()


async def get_leaderboard(chat_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM player_stats WHERE chat_id = ? ORDER BY elo DESC LIMIT ?",
            (chat_id, limit)
        )
        return await cursor.fetchall()


async def get_player_stats(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM player_stats WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def calculate_elo_change(winner_elo, loser_elo, k=32):
    expected = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    change = int(k * (1 - expected))
    return max(change, 8)


ACHIEVEMENTS = {
    "tournament_winner": ("Победитель турнира", "Выиграл турнир"),
    "tournament_finalist": ("Финалист", "Занял 2-3 место в турнире"),
    "tournament_participant": ("Участник турнира", "Участвовал в турнире"),
    "win_streak_3": ("Серия x3", "3 победы подряд"),
    "win_streak_5": ("Серия x5", "5 побед подряд"),
    "win_streak_10": ("Серия x10", "10 побед подряд"),
    "first_win": ("Первая победа", "Первая победа в матче"),
    "veteran": ("Ветеран", "Сыграл 10+ турниров"),
    "champion": ("Чемпион", "Выиграл 3+ турнира"),
    "active_voter": ("Активный зритель", "Проголосовал в 5+ событиях"),
}


async def award_achievement(user_id, achievement_type):
    if achievement_type not in ACHIEVEMENTS:
        return False
    name, desc = ACHIEVEMENTS[achievement_type]
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO achievements (user_id, achievement_type, achievement_name, description) VALUES (?, ?, ?, ?)",
                (user_id, achievement_type, name, desc)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def get_user_achievements(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM achievements WHERE user_id = ? ORDER BY awarded_at DESC",
            (user_id,)
        )
        return await cursor.fetchall()


async def check_and_award_achievements(user_id, chat_id):
    from database import get_or_create_player
    player = await get_or_create_player(user_id, chat_id)
    if not player:
        return []

    awarded = []

    if player['wins'] >= 1:
        if await award_achievement(user_id, "first_win"):
            awarded.append("first_win")

    if player['tournaments_played'] >= 1:
        if await award_achievement(user_id, "tournament_participant"):
            awarded.append("tournament_participant")

    if player['tournaments_won'] >= 1:
        if await award_achievement(user_id, "tournament_winner"):
            awarded.append("tournament_winner")

    if player['tournaments_won'] >= 3:
        if await award_achievement(user_id, "champion"):
            awarded.append("champion")

    if player['tournaments_played'] >= 10:
        if await award_achievement(user_id, "veteran"):
            awarded.append("veteran")

    if player['best_streak'] >= 3:
        if await award_achievement(user_id, "win_streak_3"):
            awarded.append("win_streak_3")

    if player['best_streak'] >= 5:
        if await award_achievement(user_id, "win_streak_5"):
            awarded.append("win_streak_5")

    if player['best_streak'] >= 10:
        if await award_achievement(user_id, "win_streak_10"):
            awarded.append("win_streak_10")

    return awarded


async def create_recurring_event(chat_id, title, description, day_of_week, hour, minute, created_by, photo=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO recurring_events (chat_id, title, description, photo, day_of_week, hour, minute, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, title, description, photo, day_of_week, hour, minute, created_by)
        )
        await db.commit()
        return cursor.lastrowid


async def update_recurring_event(event_id, title=None, description=None, photo=None, day_of_week=None, hour=None, minute=None):
    async with aiosqlite.connect(DB_NAME) as db:
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if photo is not None:
            updates.append("photo = ?")
            params.append(photo)
        if day_of_week is not None:
            updates.append("day_of_week = ?")
            params.append(day_of_week)
        if hour is not None:
            updates.append("hour = ?")
            params.append(hour)
        if minute is not None:
            updates.append("minute = ?")
            params.append(minute)
        if not updates:
            return
        params.append(event_id)
        await db.execute(
            f"UPDATE recurring_events SET {', '.join(updates)} WHERE id = ?",
            params
        )
        await db.commit()


async def get_recurring_event(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM recurring_events WHERE id = ?", (event_id,))
        return await cursor.fetchone()


async def get_recurring_events(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM recurring_events WHERE chat_id = ? AND is_active = 1",
            (chat_id,)
        )
        return await cursor.fetchall()


async def get_all_active_recurring_events():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM recurring_events WHERE is_active = 1"
        )
        return await cursor.fetchall()


async def delete_recurring_event(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM recurring_events WHERE id = ?", (event_id,))
        await db.commit()


async def mark_recurring_event_created(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE recurring_events SET last_created = CURRENT_TIMESTAMP WHERE id = ?",
            (event_id,)
        )
        await db.commit()


async def get_user_coins(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM user_coins WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await db.execute("INSERT INTO user_coins (user_id, balance) VALUES (?, 100)", (user_id,))
            await db.commit()
            return {"user_id": user_id, "balance": 100, "last_daily": None, "total_won": 0, "total_lost": 0}
        return dict(row)


async def claim_daily(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM user_coins WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        now = datetime.now()
        if row:
            last = row['last_daily']
            if last:
                last_dt = datetime.fromisoformat(last)
                elapsed = (now - last_dt).total_seconds()
                if elapsed < 86400:
                    remaining = 86400 - elapsed
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    return None, row['balance'], f"{hours}ч {minutes}м"
            new_balance = row['balance'] + 50
            await db.execute(
                "UPDATE user_coins SET balance = ?, last_daily = CURRENT_TIMESTAMP WHERE user_id = ?",
                (new_balance, user_id)
            )
            await db.execute(
                "INSERT INTO balance_history (user_id, amount, reason) VALUES (?, ?, ?)",
                (user_id, 50, "Ежедневный бонус")
            )
        else:
            new_balance = 150
            await db.execute(
                "INSERT INTO user_coins (user_id, balance, last_daily) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (user_id, new_balance)
            )
            await db.execute(
                "INSERT INTO balance_history (user_id, amount, reason) VALUES (?, ?, ?)",
                (user_id, 150, "Первый вход + бонус")
            )
        await db.commit()
        return new_balance, None, None


async def add_coins(user_id, amount, reason="Пополнение"):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO user_coins (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
            (user_id, amount, amount)
        )
        await db.execute(
            "INSERT INTO balance_history (user_id, amount, reason) VALUES (?, ?, ?)",
            (user_id, amount, reason)
        )
        await db.commit()


async def remove_coins(user_id, amount, reason="Списание"):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT balance FROM user_coins WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row or row[0] < amount:
            return False
        await db.execute(
            "UPDATE user_coins SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.execute(
            "INSERT INTO balance_history (user_id, amount, reason) VALUES (?, ?, ?)",
            (user_id, -amount, reason)
        )
        await db.commit()
        return True


async def place_bet(user_id, match_id, bet_on_user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        ok = await remove_coins(user_id, amount)
        if not ok:
            return False
        await db.execute(
            "INSERT INTO bets (user_id, match_id, bet_on_user_id, amount) VALUES (?, ?, ?, ?)",
            (user_id, match_id, bet_on_user_id, amount)
        )
        await db.commit()
        return True


async def resolve_bets(match_id, winner_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM bets WHERE match_id = ? AND resolved = 0", (match_id,))
        bets = await cursor.fetchall()
        total_pool = sum(b['amount'] for b in bets)
        winners = [b for b in bets if b['bet_on_user_id'] == winner_id]
        losers = [b for b in bets if b['bet_on_user_id'] != winner_id]
        total_loser_amount = sum(b['amount'] for b in losers)

        prize_per_winner = total_loser_amount // len(winners) if winners else 0

        for b in winners:
            payout = b['amount'] + prize_per_winner
            await add_coins(b['user_id'], payout)
            await db.execute(
                "UPDATE bets SET resolved = 1, won = 1 WHERE id = ?", (b['id'],)
            )
            await db.execute(
                "UPDATE user_coins SET total_won = total_won + ? WHERE user_id = ?",
                (prize_per_winner, b['user_id'])
            )

        for b in losers:
            await db.execute(
                "UPDATE bets SET resolved = 1, won = 0 WHERE id = ?", (b['id'],)
            )
            await db.execute(
                "UPDATE user_coins SET total_lost = total_lost + ? WHERE user_id = ?",
                (b['amount'], b['user_id'])
            )

        await db.commit()
        return total_pool, len(winners), prize_per_winner


async def get_match_bets(match_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bets WHERE match_id = ? ORDER BY amount DESC",
            (match_id,)
        )
        return await cursor.fetchall()


async def get_player_coefficient(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT COUNT(*) as total_bets, SUM(CASE WHEN won = 1 THEN amount ELSE 0 END) as total_won "
            "FROM bets WHERE bet_on_user_id = ? AND resolved = 1",
            (user_id,)
        )
        row = await cursor.fetchone()
        total = row['total_bets'] or 0
        won = row['total_won'] or 0

        cursor = await db.execute(
            "SELECT COUNT(*) as total_matches FROM matches "
            "WHERE (player1_id = ? OR player2_id = ?) AND winner_id IS NOT NULL",
            (user_id, user_id)
        )
        mrow = await cursor.fetchone()
        total_matches = mrow['total_matches'] or 0

        if total == 0:
            return 1.05

        win_rate = won / max(1, won + (total - won))
        match_participation = total_matches

        coeff = 1.05 + (win_rate * 0.3) + (match_participation * 0.01)
        coeff = max(1.05, min(5.0, coeff))
        return round(coeff, 2)


async def add_quiz(chat_id, question, options, correct_index, created_by, image=None):
    async with aiosqlite.connect(DB_NAME) as db:
        import json
        cursor = await db.execute(
            "INSERT INTO quizzes (chat_id, question, options, correct_index, created_by, image) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, question, json.dumps(options), correct_index, created_by, image)
        )
        await db.commit()
        return cursor.lastrowid


async def get_random_quiz(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quizzes WHERE chat_id = ? AND is_closed = 0 ORDER BY RANDOM() LIMIT 1",
            (chat_id,)
        )
        row = await cursor.fetchone()
        if row:
            import json
            row = dict(row)
            row['options'] = json.loads(row['options'])
        return row


async def close_quiz(quiz_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE quizzes SET is_closed = 1 WHERE id = ?", (quiz_id,))
        await db.commit()


async def place_prediction(user_id, tournament_id, predicted_winner_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        ok = await remove_coins(user_id, amount)
        if not ok:
            return False
        await db.execute(
            "INSERT INTO predictions (user_id, tournament_id, predicted_winner_id, amount) VALUES (?, ?, ?, ?)",
            (user_id, tournament_id, predicted_winner_id, amount)
        )
        await db.commit()
        return True


async def resolve_predictions(tournament_id, winner_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM predictions WHERE tournament_id = ? AND resolved = 0",
            (tournament_id,)
        )
        preds = await cursor.fetchall()
        winners = [p for p in preds if p['predicted_winner_id'] == winner_id]
        losers = [p for p in preds if p['predicted_winner_id'] != winner_id]
        total_loser = sum(p['amount'] for p in losers)

        for p in winners:
            share = int(total_loser * (p['amount'] / max(1, sum(x['amount'] for x in winners)))) if winners else 0
            await add_coins(p['user_id'], p['amount'] + share)
            await db.execute("UPDATE predictions SET resolved = 1, won = 1 WHERE id = ?", (p['id'],))

        for p in losers:
            await db.execute("UPDATE predictions SET resolved = 1, won = 0 WHERE id = ?", (p['id'],))

        await db.commit()
        return len(winners)


async def get_leaderboard_coins(limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, balance FROM user_coins ORDER BY balance DESC LIMIT ?",
            (limit,)
        )
        return await cursor.fetchall()


async def track_known_user(user_id, username=None, first_name=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO known_users (user_id, username, first_name, last_seen) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(user_id) DO UPDATE SET username = ?, first_name = ?, last_seen = CURRENT_TIMESTAMP",
            (user_id, username, first_name, username, first_name)
        )
        await db.commit()


async def get_all_known_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id FROM known_users")
        return await cursor.fetchall()


async def get_user_name(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT username, first_name FROM known_users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return row['first_name'] or row['username'] or str(user_id)
        return str(user_id)


async def get_balance_history(user_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT amount, reason, created_at FROM balance_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        return await cursor.fetchall()


async def get_known_users_count():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM known_users")
        row = await cursor.fetchone()
        return row[0]


async def get_bot_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        stats = {}
        cursor = await db.execute("SELECT COUNT(*) FROM known_users")
        row = await cursor.fetchone()
        stats['total_users'] = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM tournaments")
        row = await cursor.fetchone()
        stats['total_tournaments'] = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM matches")
        row = await cursor.fetchone()
        stats['total_matches'] = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM events")
        row = await cursor.fetchone()
        stats['total_events'] = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM polls")
        row = await cursor.fetchone()
        stats['total_polls'] = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM bets WHERE resolved = 1")
        row = await cursor.fetchone()
        stats['total_bets'] = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM clans")
        row = await cursor.fetchone()
        stats['total_clans'] = row[0]

        return stats


async def get_tournament_analytics():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        try:
            cursor = await db.execute(
                "SELECT winner_id, COUNT(*) as wins FROM tournaments WHERE winner_id IS NOT NULL GROUP BY winner_id ORDER BY wins DESC LIMIT 10"
            )
            winners = await cursor.fetchall()
        except Exception:
            winners = []

        cursor = await db.execute(
            "SELECT user_id, COUNT(*) as count FROM tournament_participants GROUP BY user_id ORDER BY count DESC LIMIT 10"
        )
        participants = await cursor.fetchall()

        return {"top_winners": winners, "top_participants": participants}


async def get_match_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT winner_id, COUNT(*) as wins FROM matches WHERE winner_id IS NOT NULL GROUP BY winner_id ORDER BY wins DESC LIMIT 10"
        )
        winners = await cursor.fetchall()
        return {"top_match_winners": winners}


async def create_clan(name, tag, chat_id, leader_id, description=""):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO clans (name, tag, chat_id, leader_id, description) VALUES (?, ?, ?, ?, ?)",
                (name, tag, chat_id, leader_id, description)
            )
            clan_id = cursor.lastrowid
            await db.execute(
                "INSERT INTO clan_members (clan_id, user_id, role) VALUES (?, ?, 'leader')",
                (clan_id, leader_id)
            )
            await db.commit()
            return clan_id
        except Exception:
            return None


async def get_clan(clan_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
        return await cursor.fetchone()


async def get_user_clan(user_id, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT c.* FROM clans c
            JOIN clan_members cm ON cm.clan_id = c.id
            WHERE cm.user_id = ? AND c.chat_id = ?
        """, (user_id, chat_id))
        return await cursor.fetchone()


async def join_clan(clan_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO clan_members (clan_id, user_id) VALUES (?, ?)",
                (clan_id, user_id)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def leave_clan(user_id, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        clan = await get_user_clan(user_id, chat_id)
        if not clan:
            return False
        await db.execute(
            "DELETE FROM clan_members WHERE user_id = ? AND clan_id = ?",
            (user_id, clan['id'])
        )
        await db.commit()
        return True


async def get_clan_members(clan_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT cm.*, ps.elo, ps.wins, ps.losses
            FROM clan_members cm
            LEFT JOIN player_stats ps ON ps.user_id = cm.user_id
            WHERE cm.clan_id = ?
            ORDER BY cm.role = 'leader' DESC, ps.elo DESC
        """, (clan_id,))
        return await cursor.fetchall()


async def get_clans(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM clans WHERE chat_id = ? ORDER BY elo DESC",
            (chat_id,)
        )
        return await cursor.fetchall()


async def get_clan_member_count(clan_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM clan_members WHERE clan_id = ?",
            (clan_id,)
        )
        row = await cursor.fetchone()
        return row[0]


async def update_clan_stats(clan_id, won):
    async with aiosqlite.connect(DB_NAME) as db:
        if won:
            await db.execute(
                "UPDATE clans SET elo = elo + 20, wins = wins + 1 WHERE id = ?",
                (clan_id,)
            )
        else:
            await db.execute(
                "UPDATE clans SET elo = MAX(100, elo - 15), losses = losses + 1 WHERE id = ?",
                (clan_id,)
            )
        await db.commit()


async def track_chat_member(user_id, chat_id, username=None, display_name=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chat_members (user_id, chat_id, username, display_name, last_seen) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, chat_id, username, display_name)
        )
        await db.commit()


async def get_chat_members(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM chat_members WHERE chat_id = ? ORDER BY last_seen DESC",
            (chat_id,)
        )
        return await cursor.fetchall()


async def get_active_polls_for_event(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM polls WHERE event_id = ? AND is_active = 1",
            (event_id,)
        )
        return await cursor.fetchall()


async def add_event(title, description, event_date, created_by, chat_id, message_id=None, image_file_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO events (title, description, event_date, created_by, chat_id, message_id, image_file_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, description, event_date, created_by, chat_id, message_id, image_file_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_events(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM events WHERE chat_id = ? ORDER BY event_date ASC",
            (chat_id,)
        )
        return await cursor.fetchall()


async def get_event(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return await cursor.fetchone()


async def delete_event(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        await db.commit()


async def get_event_poll(event_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM polls WHERE event_id = ? AND poll_type = 'event' LIMIT 1",
            (event_id,)
        )
        return await cursor.fetchone()


async def update_event_message_id(event_id, message_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE events SET message_id = ? WHERE id = ?", (message_id, event_id))
        await db.commit()


async def update_poll_message_id(poll_id, message_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE polls SET message_id = ? WHERE id = ?", (message_id, poll_id))
        await db.commit()


async def update_tournament_message_id(tournament_id, message_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tournaments SET message_id = ? WHERE id = ?", (message_id, tournament_id))
        await db.commit()


async def add_poll(question, options, poll_type, created_by, chat_id, event_id=None, message_id=None, image_file_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        options_str = "|".join(options)
        cursor = await db.execute(
            "INSERT INTO polls (question, options, poll_type, event_id, created_by, chat_id, message_id, image_file_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (question, options_str, poll_type, event_id, created_by, chat_id, message_id, image_file_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_polls(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM polls WHERE chat_id = ? AND is_active = 1",
            (chat_id,)
        )
        return await cursor.fetchall()


async def get_poll(poll_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
        return await cursor.fetchone()


async def vote(poll_id, user_id, option_index):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO poll_votes (poll_id, user_id, option_index) VALUES (?, ?, ?)",
                (poll_id, user_id, option_index)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_poll_results(poll_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT option_index, COUNT(*) as count FROM poll_votes WHERE poll_id = ? GROUP BY option_index",
            (poll_id,)
        )
        return await cursor.fetchall()


async def get_poll_votes(poll_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, option_index, voted_at FROM poll_votes WHERE poll_id = ? ORDER BY voted_at",
            (poll_id,)
        )
        return await cursor.fetchall()


async def close_poll(poll_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE polls SET is_active = 0 WHERE id = ?", (poll_id,))
        await db.commit()


async def create_tournament(name, description, max_participants, created_by, chat_id, image_file_id=None, prize_places=1, participation_award=0):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO tournaments (name, description, max_participants, created_by, chat_id, image_file_id, prize_places, participation_award) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, description, max_participants, created_by, chat_id, image_file_id, prize_places, participation_award)
        )
        await db.commit()
        return cursor.lastrowid


async def get_tournament(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
        return await cursor.fetchone()


async def set_tournament_prize(tournament_id, user_id, place, prize_name=None):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO tournament_prizes (tournament_id, user_id, place, prize_name) VALUES (?, ?, ?, ?)",
                (tournament_id, user_id, place, prize_name)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def get_tournament_prizes(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tournament_prizes WHERE tournament_id = ? ORDER BY place",
            (tournament_id,)
        )
        return await cursor.fetchall()


async def remove_tournament_prize(tournament_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM tournament_prizes WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        await db.commit()


async def get_active_tournaments(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tournaments WHERE chat_id = ? AND status IN ('registration', 'in_progress')",
            (chat_id,)
        )
        return await cursor.fetchall()


async def join_tournament(tournament_id, user_id, username, display_name):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO tournament_participants (tournament_id, user_id, username, display_name) VALUES (?, ?, ?, ?)",
                (tournament_id, user_id, username, display_name)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def leave_tournament(tournament_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM tournament_participants WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        await db.commit()


async def get_tournament_participants(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tournament_participants WHERE tournament_id = ?",
            (tournament_id,)
        )
        return await cursor.fetchall()


async def get_participant_count(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tournament_participants WHERE tournament_id = ?",
            (tournament_id,)
        )
        row = await cursor.fetchone()
        return row[0]


async def start_tournament(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE tournaments SET status = 'in_progress' WHERE id = ?",
            (tournament_id,)
        )
        await db.commit()


async def finish_tournament(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE tournaments SET status = 'finished' WHERE id = ?",
            (tournament_id,)
        )
        await db.commit()


async def check_match_exists(tournament_id, player1_id, player2_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """SELECT id FROM matches WHERE tournament_id = ? AND 
               ((player1_id = ? AND player2_id = ?) OR (player1_id = ? AND player2_id = ?))""",
            (tournament_id, player1_id, player2_id, player2_id, player1_id)
        )
        return await cursor.fetchone()


async def create_match(tournament_id, player1_id, player2_id, round_num, match_num):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO matches (tournament_id, player1_id, player2_id, round_num, match_num) VALUES (?, ?, ?, ?, ?)",
            (tournament_id, player1_id, player2_id, round_num, match_num)
        )
        await db.commit()
        return cursor.lastrowid


async def auto_generate_bracket(tournament_id):
    participants = await get_tournament_participants(tournament_id)
    if len(participants) < 2:
        return None, "Недостаточно участников"

    sorted_players = sorted(participants, key=lambda p: p['elo'] if 'elo' in p.keys() else 1000, reverse=True)

    matches_created = []
    round_num = 1

    for i in range(0, len(sorted_players) - 1, 2):
        match_num = (i // 2) + 1
        match_id = await create_match(
            tournament_id=tournament_id,
            player1_id=sorted_players[i]['user_id'],
            player2_id=sorted_players[i + 1]['user_id'],
            round_num=round_num,
            match_num=match_num
        )
        matches_created.append(match_id)

    return matches_created, None


async def get_match(match_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        return await cursor.fetchone()


async def get_pending_matches(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM matches WHERE tournament_id = ? AND status = 'pending' ORDER BY round_num, match_num",
            (tournament_id,)
        )
        return await cursor.fetchall()


async def get_tournament_matches(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM matches WHERE tournament_id = ? ORDER BY round_num, match_num",
            (tournament_id,)
        )
        return await cursor.fetchall()


async def set_match_winner(match_id, winner_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE matches SET winner_id = ?, status = 'finished' WHERE id = ?",
            (winner_id, match_id)
        )
        await db.commit()


async def mark_match_notified(match_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE matches SET notified = 1 WHERE id = ?",
            (match_id,)
        )
        await db.commit()


async def get_tournament_standings(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT
                tp.user_id,
                tp.username,
                tp.display_name,
                COALESCE(ps.elo, 1000) as elo,
                COUNT(CASE WHEN m.winner_id = tp.user_id THEN 1 END) as wins,
                COUNT(CASE WHEN (m.player1_id = tp.user_id OR m.player2_id = tp.user_id) AND m.winner_id != tp.user_id THEN 1 END) as losses
            FROM tournament_participants tp
            LEFT JOIN matches m ON (m.player1_id = tp.user_id OR m.player2_id = tp.user_id) AND m.tournament_id = tp.tournament_id AND m.status = 'finished'
            LEFT JOIN player_stats ps ON ps.user_id = tp.user_id
            WHERE tp.tournament_id = ?
            GROUP BY tp.user_id
            ORDER BY wins DESC
        """, (tournament_id,))
        return await cursor.fetchall()


async def delete_tournament(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM matches WHERE tournament_id = ?", (tournament_id,))
        await db.execute("DELETE FROM tournament_participants WHERE tournament_id = ?", (tournament_id,))
        await db.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
        await db.commit()


async def get_user_recent_matches(user_id, limit=5):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT m.*, t.name as tournament_name
               FROM matches m
               JOIN tournaments t ON m.tournament_id = t.id
               WHERE (m.player1_id = ? OR m.player2_id = ?) AND m.winner_id IS NOT NULL
               ORDER BY m.id DESC LIMIT ?""",
            (user_id, user_id, limit)
        )
        return await cursor.fetchall()


async def get_pending_challenge_matches(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT m.*, t.name as tournament_name
               FROM matches m
               JOIN tournaments t ON m.tournament_id = t.id
               WHERE (m.player1_id = ? OR m.player2_id = ?) AND m.winner_id IS NULL AND m.status != 'cancelled'
               ORDER BY m.id DESC""",
            (user_id, user_id)
        )
        return await cursor.fetchall()


async def get_unfought_opponents(user_id, tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id FROM tournament_participants WHERE tournament_id = ? AND user_id != ?",
            (tournament_id, user_id)
        )
        all_opponents = await cursor.fetchall()

        cursor = await db.execute(
            """SELECT player1_id, player2_id FROM matches
               WHERE tournament_id = ? AND winner_id IS NOT NULL
               AND (player1_id = ? OR player2_id = ?)""",
            (tournament_id, user_id, user_id)
        )
        fought = await cursor.fetchall()

        fought_ids = set()
        for m in fought:
            if m['player1_id'] == user_id:
                fought_ids.add(m['player2_id'])
            else:
                fought_ids.add(m['player1_id'])

        return [o for o in all_opponents if o['user_id'] not in fought_ids]
