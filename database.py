import aiosqlite
from config import DB_NAME


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
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
        await db.commit()


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
