
import sqlite3

from contextlib import contextmanager
from config import MEMORY_DB_PATH


class MemoryDatabase:

    def __init__(self):
        MEMORY_DB_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(
            str(MEMORY_DB_PATH),
            timeout=10
        )

        connection.row_factory = sqlite3.Row

        try:
            connection.execute(
                "PRAGMA busy_timeout = 10000"
            )
            connection.execute(
                "PRAGMA synchronous = NORMAL"
            )

            yield connection

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def initialize(self):

        with self.connect() as connection:

            # Betere prestaties bij gelijktijdig lezen en schrijven
            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    importance INTEGER DEFAULT 1,
                    source TEXT DEFAULT 'automatic',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)

            # UNIQUE(category, key) heeft al een index.
            # Een extra index op category is daarom overbodig.
            connection.execute("""
                DROP INDEX IF EXISTS idx_memories_category
            """)
