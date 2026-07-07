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
                status TEXT DEFAULT 'registration',
                created_by INTEGER,
                chat_id INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


async def add_event(title, description, event_date, created_by, chat_id, message_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO events (title, description, event_date, created_by, chat_id, message_id) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, event_date, created_by, chat_id, message_id)
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


async def add_poll(question, options, poll_type, created_by, chat_id, event_id=None, message_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        options_str = "|".join(options)
        cursor = await db.execute(
            "INSERT INTO polls (question, options, poll_type, event_id, created_by, chat_id, message_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (question, options_str, poll_type, event_id, created_by, chat_id, message_id)
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


async def close_poll(poll_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE polls SET is_active = 0 WHERE id = ?", (poll_id,))
        await db.commit()


async def create_tournament(name, description, max_participants, created_by, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO tournaments (name, description, max_participants, created_by, chat_id) VALUES (?, ?, ?, ?, ?)",
            (name, description, max_participants, created_by, chat_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_tournament(tournament_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
        return await cursor.fetchone()


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
                COUNT(CASE WHEN m.winner_id = tp.user_id THEN 1 END) as wins,
                COUNT(CASE WHEN (m.player1_id = tp.user_id OR m.player2_id = tp.user_id) AND m.winner_id != tp.user_id THEN 1 END) as losses
            FROM tournament_participants tp
            LEFT JOIN matches m ON (m.player1_id = tp.user_id OR m.player2_id = tp.user_id) AND m.tournament_id = tp.tournament_id AND m.status = 'finished'
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
