import sys

from PySide6.QtWidgets import QApplication
from gui.window import HaileyWindow
from core.assistant import HaileyAssistant


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("Hailey")

    assistant = HaileyAssistant()
    window = HaileyWindow(assistant)

    window.show()

    sys.exit(app.exec())