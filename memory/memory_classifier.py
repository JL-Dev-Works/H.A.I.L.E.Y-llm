
import json
import re
import hashlib
import logging


logger = logging.getLogger(__name__)


class MemoryClassifier:

    ALLOWED_CATEGORIES = {
        "personal",
        "preference",
        "project",
        "goal",
        "fact",
        "note"
    }

    SENSITIVE_PATTERNS = [
        r"\bpassword\b",
        r"\bwachtwoord\b",
        r"\bpaswoord\b",
        r"\bapi[_ -]?key\b",
        r"\bsecret[_ -]?key\b",
        r"\bcreditcard\b",
        r"\bcredit card\b",
        r"\bbankrekening\b",
        r"\bbank account\b"
    ]

    EXPLICIT_PATTERN = re.compile(
        r"\b("
        r"onthoud|onthou|onthouden|"
        r"remember|"
        r"sla op|save this"
        r")\b",
        re.IGNORECASE
    )

    EXPLICIT_PREFIX = re.compile(
        r"^\s*(?:"
        r"onthoud(?:en)?|onthou|"
        r"remember|"
        r"sla\s+op|"
        r"save\s+this"
        r")\s*(?:dat\s+)?",
        re.IGNORECASE
    )

    MEMORY_INDICATORS = (
        "ik ben",
        "ik werk",
        "ik bouw",
        "ik maak",
        "ik gebruik",
        "ik vind",
        "ik hou van",
        "ik houd van",
        "mijn doel",
        "mijn voorkeur",
        "ik wil",
        "ik heb",
        "ik studeer",
        "ik woon",
        "i am",
        "i work",
        "i build",
        "i use",
        "i prefer",
        "my goal",
        "i like"
    )

    def is_sensitive(self, message):

        text = message.lower()

        return any(
            re.search(pattern, text)
            for pattern in self.SENSITIVE_PATTERNS
        )

    def is_explicit_request(self, message):

        return bool(
            self.EXPLICIT_PATTERN.search(message)
        )

    def extract_explicit_value(self, message):

        value = self.EXPLICIT_PREFIX.sub(
            "",
            message.strip(),
            count=1
        )

        value = value.strip(" \t\n.,!?")

        if not value:
            return None

        if len(value) > 500:
            return None

        return value

    def should_analyze(self, message):

        message = message.strip().lower()

        if len(message) < 8:
            return False

        if self.is_sensitive(message):
            return False

        if self.is_explicit_request(message):
            return True

        return any(
            indicator in message
            for indicator in self.MEMORY_INDICATORS
        )

    def parse_json(self, raw_result):

        if not isinstance(raw_result, str):
            return None

        raw_result = raw_result.strip()

        raw_result = re.sub(
            r"^```(?:json)?\s*",
            "",
            raw_result,
            flags=re.IGNORECASE
        )

        raw_result = re.sub(
            r"\s*```$",
            "",
            raw_result
        )

        decoder = json.JSONDecoder()

        for index, character in enumerate(raw_result):

            if character != "{":
                continue

            try:
                result, _ = decoder.raw_decode(
                    raw_result[index:]
                )

                return result

            except json.JSONDecodeError:
                continue

        return None

    def create_explicit_memory(self, message):

        value = self.extract_explicit_value(message)

        if not value:
            return None

        digest = hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:16]

        return {
            "action": "insert",
            "target_id": None,
            "category": "note",
            "key": f"explicit_{digest}",
            "value": value,
            "importance": 3
        }

    def validate_result(self, result, existing_memories):

        if not isinstance(result, dict):
            return None

        if result.get("should_remember") is not True:
            return None

        action = result.get("action")
        category = result.get("category")
        key = result.get("key")
        value = result.get("value")
        importance = result.get("importance")
        target_id = result.get("target_id")

        if category not in self.ALLOWED_CATEGORIES:
            return None

        if not isinstance(key, str):
            return None

        key = key.strip()

        if not key or len(key) > 80:
            return None

        if not isinstance(value, str):
            return None

        value = value.strip()

        if not value or len(value) > 500:
            return None

        if (
            not isinstance(importance, int)
            or isinstance(importance, bool)
            or importance not in (1, 2, 3)
        ):
            return None

        valid_ids = {
            item["id"]
            for item in existing_memories
            if isinstance(item, dict) and "id" in item
        }

        if action == "skip":
            return None

        if action == "insert":
            target_id = None

        elif action == "update":

            if (
                not isinstance(target_id, int)
                or isinstance(target_id, bool)
                or target_id not in valid_ids
            ):
                return None

        else:
            return None

        return {
            "action": action,
            "target_id": target_id,
            "category": category,
            "key": key,
            "value": value,
            "importance": importance
        }

    def classify(
        self,
        message,
        model,
        conversation_history=None,
        existing_memories=None
    ):

        conversation_history = conversation_history or []
        existing_memories = existing_memories or []

        if self.is_sensitive(message):
            return None

        if not self.should_analyze(message):
            return None

        # ROUTE 1:
        # Expliciete verzoeken hebben GEEN LLM-call nodig.

        if self.is_explicit_request(message):

            memory = self.create_explicit_memory(message)

            logger.info(
                "Explicit memory request processed without LLM"
            )

            return memory

        # ROUTE 2:
        # Alleen impliciete memory-detectie gebruikt het model.

        try:

            raw_result = model.analyze_memory(
                message=message,
                conversation_history=conversation_history,
                existing_memories=existing_memories
            )

            result = self.parse_json(raw_result)

            if not isinstance(result, dict):
                return None

            return self.validate_result(
                result,
                existing_memories
            )

        except Exception:

            logger.exception(
                "Memory analysis failed"
            )

            return None
