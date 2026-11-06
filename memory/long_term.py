
import logging

from memory.database import MemoryDatabase


logger = logging.getLogger(__name__)


class LongTermMemory:

    def __init__(self):
        self.database = MemoryDatabase()

    # ==========================================
    # SAVE MEMORY
    # ==========================================

    def remember(
        self,
        category,
        key,
        value,
        importance=1,
        source="automatic"
    ):

        if not category or not key or not value:
            logger.warning("[MEMORY] Invalid memory data")
            return False

        try:

            with self.database.connect() as connection:

                connection.execute("""
                    INSERT INTO memories (
                        category,
                        key,
                        value,
                        importance,
                        source
                    )
                    VALUES (?, ?, ?, ?, ?)

                    ON CONFLICT(category, key)
                    DO UPDATE SET
                        value = excluded.value,
                        importance = excluded.importance,
                        source = excluded.source,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    category,
                    key,
                    value,
                    importance,
                    source
                ))

            logger.info(
                "[MEMORY] Saved: %s | %s",
                category,
                key
            )

            return True

        except Exception:

            logger.exception("[MEMORY] Save failed")

            return False

    # ==========================================
    # SAVE CLASSIFIER RESULT
    # ==========================================

    def save_classified_memory(self, memory):

        if not isinstance(memory, dict):
            return False

        action = memory.get("action")

        try:

            if action == "insert":

                return self.remember(
                    category=memory["category"],
                    key=memory["key"],
                    value=memory["value"],
                    importance=memory.get("importance", 1),
                    source="explicit"
                    if memory.get("key", "").startswith("explicit_")
                    else "automatic"
                )

            elif action == "update":

                target_id = memory.get("target_id")

                if not isinstance(target_id, int) or isinstance(target_id, bool):
                    return False

                return self.update_memory(
                    memory_id=target_id,
                    category=memory["category"],
                    key=memory["key"],
                    value=memory["value"],
                    importance=memory.get("importance", 1),
                    source="automatic"
                )

            logger.warning(
                "[MEMORY] Unknown action: %s",
                action
            )

            return False

        except (KeyError, TypeError, ValueError):

            logger.exception(
                "[MEMORY] Invalid classifier result"
            )

            return False

    # ==========================================
    # UPDATE MEMORY
    # ==========================================

    def update_memory(
        self,
        memory_id,
        category,
        key,
        value,
        importance=1,
        source="automatic"
    ):

        if not category or not key or not value:
            return False

        try:

            with self.database.connect() as connection:

                existing = connection.execute("""
                    SELECT id
                    FROM memories
                    WHERE category = ?
                    AND key = ?
                    AND id != ?
                    LIMIT 1
                """, (
                    category,
                    key,
                    memory_id
                )).fetchone()

                if existing:
                    logger.warning(
                        "[MEMORY] Duplicate memory key: %s",
                        key
                    )
                    return False

                cursor = connection.execute("""
                    UPDATE memories
                    SET
                        category = ?,
                        key = ?,
                        value = ?,
                        importance = ?,
                        source = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    category,
                    key,
                    value,
                    importance,
                    source,
                    memory_id
                ))

            if cursor.rowcount > 0:

                logger.info(
                    "[MEMORY] Updated memory ID: %s",
                    memory_id
                )

                return True

            logger.warning(
                "[MEMORY] Memory ID not found: %s",
                memory_id
            )

            return False

        except Exception:

            logger.exception("[MEMORY] Update failed")

            return False

    # ==========================================
    # GET MEMORIES
    # ==========================================

    def get_memories(self, category=None, limit=100):

        try:

            limit = max(1, min(int(limit), 1000))

            with self.database.connect() as connection:

                if category:

                    rows = connection.execute("""
                        SELECT *
                        FROM memories
                        WHERE category = ?
                        ORDER BY importance DESC, updated_at DESC
                        LIMIT ?
                    """, (
                        category,
                        limit
                    )).fetchall()

                else:

                    rows = connection.execute("""
                        SELECT *
                        FROM memories
                        ORDER BY importance DESC, updated_at DESC
                        LIMIT ?
                    """, (
                        limit,
                    )).fetchall()

            return [
                dict(row)
                for row in rows
            ]

        except Exception:

            logger.exception("[MEMORY] Retrieval failed")

            return []

    # ==========================================
    # GET SINGLE MEMORY
    # ==========================================

    def get_memory(self, category, key):

        try:

            with self.database.connect() as connection:

                row = connection.execute("""
                    SELECT *
                    FROM memories
                    WHERE category = ?
                    AND key = ?
                    LIMIT 1
                """, (
                    category,
                    key
                )).fetchone()

            return dict(row) if row else None

        except Exception:

            logger.exception("[MEMORY] Get memory failed")

            return None

    # ==========================================
    # DELETE MEMORY
    # ==========================================

    def forget(self, memory_id):

        try:

            with self.database.connect() as connection:

                cursor = connection.execute("""
                    DELETE FROM memories
                    WHERE id = ?
                """, (
                    memory_id,
                ))

            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(
                    "[MEMORY] Deleted ID: %s",
                    memory_id
                )

            return deleted

        except Exception:

            logger.exception("[MEMORY] Delete failed")

            return False

    # ==========================================
    # CLEAR ALL MEMORIES
    # ==========================================

    def clear_memory(self):

        try:

            with self.database.connect() as connection:

                connection.execute("""
                    DELETE FROM memories
                """)

            logger.warning(
                "[MEMORY] All memories cleared"
            )

            return True

        except Exception:

            logger.exception("[MEMORY] Clear failed")

            return False

    # ==========================================
    # COUNT MEMORIES
    # ==========================================

    def count_memories(self):

        try:

            with self.database.connect() as connection:

                result = connection.execute("""
                    SELECT COUNT(*)
                    FROM memories
                """).fetchone()

            return result[0]

        except Exception:

            logger.exception("[MEMORY] Count failed")

            return 0
