
from PySide6.QtCore import QThread, Signal
import threading
import time
import sys


class AssistantWorker(QThread):

    token = Signal(str)
    status = Signal(str)
    finished_response = Signal(str)
    error = Signal(str)

    def __init__(self, assistant, message, parent=None):
        super().__init__(parent)

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
