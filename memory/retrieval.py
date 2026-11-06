
import time
import logging

from config import (
    MEMORY_MAX_CONTEXT_ITEMS,
    MEMORY_MAX_CONTEXT_CHARS
)


logger = logging.getLogger(__name__)


class MemoryRetrieval:

    def __init__(self, long_term_memory):

        self.memory = long_term_memory

    def retrieve(self):

        start = time.perf_counter()

        try:

            memories = self.memory.get_memories(
                limit=MEMORY_MAX_CONTEXT_ITEMS
            )

        except Exception:

            logger.exception(
                "Memory retrieval failed"
            )

            return []

        context = []
        total_chars = 0

        max_chars = MEMORY_MAX_CONTEXT_CHARS

        for memory in memories or []:

            if not isinstance(memory, dict):
                continue

            category = memory.get("category", "note")
            key = memory.get("key", "")
            value = memory.get("value", "")

            if not isinstance(value, str):
                continue

            entry = f"{category}: {key} = {value}"

            entry_length = len(entry)

            if entry_length > max_chars:
                continue

            if total_chars + entry_length > max_chars:
                continue

            context.append(entry)

            total_chars += entry_length

        elapsed = time.perf_counter() - start

        logger.debug(
            "Memory retrieval completed in %.4fs | %d memories | %d chars",
            elapsed,
            len(context),
            total_chars
        )

        return context

    def build_context(self):

        memories = self.retrieve()

        if not memories:
            return ""

        return (
            "Relevante opgeslagen informatie over de gebruiker:\n"
            + "\n".join(
                f"- {memory}"
                for memory in memories
            )
        )
