import sqlite3
from config import USER_DIR

DB_PATH = USER_DIR / "hailey.db"


def initialize():
    USER_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory TEXT NOT NULL
            )
        """)


def remember(text):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO memories (memory) VALUES (?)",
            (text,)
        )


def get_memories():
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute(
            "SELECT id, memory FROM memories ORDER BY id"
        ).fetchall()

    return rows


def forget(memory_id):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,)
        )


def clear_memory():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM memories")