
from memory.long_term import LongTermMemory
from memory.memory_classifier import MemoryClassifier
from memory.retrieval import MemoryRetrieval

from config import (
    MEMORY_ENABLED,
    MEMORY_AUTO_SAVE,
    MEMORY_MIN_IMPORTANCE
)


class MemoryManager:

    def __init__(self):

        self.enabled = MEMORY_ENABLED
        self.auto_save = MEMORY_AUTO_SAVE

        self.long_term = LongTermMemory()

        self.classifier = MemoryClassifier()

        self.retrieval = MemoryRetrieval(
            self.long_term
        )

    def remember(
        self,
        category,
        key,
        value,
        importance=3,
        source="manual"
    ):

        if not self.enabled:
            return False

        return self.long_term.remember(
            category=category,
            key=key,
            value=value,
            importance=importance,
            source=source
        )

    def observe_user_message(
        self,
        message,
        model,
        conversation_history=None
    ):

        if not self.enabled or not self.auto_save:
            return False

        existing_memories = self.long_term.get_memories(
            limit=30
        )

        candidate = self.classifier.classify(
            message=message,
            model=model,
            conversation_history=conversation_history,
            existing_memories=existing_memories
        )

        if not candidate:
            return False

        if candidate["importance"] < MEMORY_MIN_IMPORTANCE:
            return False

        action = candidate["action"]

        if action == "update":

            updated = self.long_term.update_memory(
                memory_id=candidate["target_id"],
                category=candidate["category"],
                key=candidate["key"],
                value=candidate["value"],
                importance=candidate["importance"],
                source="automatic"
            )

            if updated:
                print("[Hailey memory: existing memory updated]")

            return updated

        if action == "insert":

            saved = self.remember(
                category=candidate["category"],
                key=candidate["key"],
                value=candidate["value"],
                importance=candidate["importance"],
                source="automatic"
            )

            return saved

        return False

    def get_memories(self):

        return self.long_term.get_memories()

    def forget(self, memory_id):

        return self.long_term.forget(memory_id)

    def clear(self):

        return self.long_term.clear_memory()

    def get_context(self):

        if not self.enabled:
            return ""

        return self.retrieval.build_context()
