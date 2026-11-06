
from config import SHORT_TERM_MAX_MESSAGES


class ShortTermMemory:

    def __init__(self, max_messages=SHORT_TERM_MAX_MESSAGES):

        self.max_messages = max_messages
        self.messages = []

    def add_message(self, role, content):

        self.messages.append({
            "role": role,
            "content": content
        })

        self.trim()

    def trim(self):

        if len(self.messages) > self.max_messages:

            self.messages = self.messages[
                -self.max_messages:
            ]

    def get_messages(self):

        return list(self.messages)

    def clear(self):

        self.messages.clear()
