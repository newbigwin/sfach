import aiosqlite
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


async def create_match(tournament_id, player1_id, player2_id, round_num, match_num):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO matches (tournament_id, player1_id, player2_id, round_num, match_num) VALUES (?, ?, ?, ?, ?)",
            (tournament_id, player1_id, player2_id, round_num, match_num)
        )
        await db.commit()
        return cursor.lastrowid


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
