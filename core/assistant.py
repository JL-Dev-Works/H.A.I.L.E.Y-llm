
from PySide6.QtCore import QThread, Signal

import threading
import time
import sys

from core.model import HaileyModel
from core.conversation import Conversation
from core.memory_manager import MemoryManager

from tools.internet_access.web_intent import should_search
from tools.internet_access.web_search import WebResearchTool


class HaileyAssistant:

    def __init__(self):
        self.model = HaileyModel()
        self.conversation = Conversation()
        self.memory = MemoryManager()
        self.web = WebResearchTool()

    def reset_conversation(self):
        self.conversation.clear()

    def respond(self, message, on_token=None, on_status=None):

        self.conversation.add_user(message)

        try:
            if on_status:
                on_status("Checking memory...")

            self.memory.observe_user_message(
                message=message,
                model=self.model,
                conversation_history=self.conversation.get_history()
            )

            memory_context = self.memory.get_context()

            web_context = ""

            if should_search(message):

                if on_status:
                    on_status("Searching the web...")

                research = self.web.research(
                    message,
                    max_results=3,
                    pages_to_read=1
                )

                web_context = self.web.format_for_prompt(research)

            messages = self.conversation.get_messages(
                memory_context=memory_context,
                extra_context=web_context
            )

            if on_status:
                on_status("Generating response...")

            response = self.model.generate(
                messages,
                on_token=on_token
            )

            self.conversation.add_assistant(response)

            return response

        except Exception:
            if (
                self.conversation.messages
                and self.conversation.messages[-1]["role"] == "user"
            ):
                self.conversation.messages.pop()

            raise


class AssistantWorker(QThread):

    token = Signal(str)
    status = Signal(str)
    finished_response = Signal(str)
    error = Signal(str)

    def __init__(self, assistant, message):
        super().__init__()

        self.assistant = assistant
        self.message = message
        self.response = ""

    @staticmethod
    def format_elapsed(seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)

        return f"{minutes:02d}:{seconds:02d}"

    def run(self):

        start_time = time.monotonic()
        stop_timer = threading.Event()

        def print_timer():

            while not stop_timer.wait(1):

                elapsed = time.monotonic() - start_time

                sys.stdout.write(
                    f"\r[Hailey] Bezig... "
                    f"{self.format_elapsed(elapsed)}"
                )

                sys.stdout.flush()

        timer_thread = threading.Thread(
            target=print_timer,
            daemon=True
        )

        timer_thread.start()

        try:

            self.response = self.assistant.respond(
                self.message,
                on_token=self.token.emit,
                on_status=self.status.emit
            )

            self.finished_response.emit(self.response)

        except Exception as exc:

            self.error.emit(str(exc))

        finally:

            elapsed = time.monotonic() - start_time

            stop_timer.set()
            timer_thread.join()

            sys.stdout.write(
                f"\r[Hailey] Klaar in "
                f"{self.format_elapsed(elapsed)}       \n"
            )

            sys.stdout.flush()
