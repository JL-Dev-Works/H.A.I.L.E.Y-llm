from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QTextBrowser,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QSizePolicy,
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen


from .worker import AssistantWorker


class ThinkingSpinner(QWidget):
    """Kleine draaiende laadindicator voor naast de naam van Hailey."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

    def start(self):
        self.show()
        if not self.timer.isActive():
            self.timer.start(70)

    def stop(self):
        self.timer.stop()
        self.hide()

    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        if not self.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = 6
        dot_radius = 1.7

        for index in range(8):
            angle = (self.angle + index * 45) * 3.141592653589793 / 180
            x = center_x + radius * __import__("math").cos(angle)
            y = center_y + radius * __import__("math").sin(angle)
            opacity = 45 + int(210 * ((index + 1) / 8))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(220, 220, 220, opacity))
            painter.drawEllipse(
                int(x - dot_radius),
                int(y - dot_radius),
                int(dot_radius * 2),
                int(dot_radius * 2)
            )


class ChatInput(QPlainTextEdit):

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.window().send_message()
            return

        super().keyPressEvent(event)


class ChatMessage(QWidget):

    def __init__(self, role, content=""):
        super().__init__()

        self.role = role
        self.content = content

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(8)

        self.name = QLabel(
            "Jij" if role == "user" else "H.A.I.L.E.Y"
        )
        self.name.setObjectName("messageName")

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(8)
        name_row.addWidget(self.name)

        self.spinner = ThinkingSpinner()
        self.spinner.hide()
        name_row.addWidget(self.spinner)
        name_row.addStretch()

        self.text = QTextBrowser()
        self.text.setObjectName("messageText")
        self.text.setMarkdown(content)
        self.text.setOpenExternalLinks(True)
        self.text.setFrameShape(QTextBrowser.NoFrame)

        self.text.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.text.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.text.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

        layout.addLayout(name_row)
        layout.addWidget(self.text)

        self.text.document().contentsChanged.connect(
            self.update_height
        )

        self.update_height()

    def update_height(self):
        document = self.text.document()
        document.setTextWidth(
            self.text.viewport().width()
        )

        height = int(document.size().height()) + 12

        self.text.setMinimumHeight(height)
        self.text.setMaximumHeight(height)

    def set_content(self, content):
        self.content = content
        self.text.setMarkdown(content)
        self.update_height()

    def set_thinking(self, active):
        if active:
            self.spinner.start()
        else:
            self.spinner.stop()


class HaileyWindow(QMainWindow):

    def __init__(self, assistant):
        super().__init__()

        self.assistant = assistant
        self.worker = None
        self.current_message = None


        self.setWindowTitle("H.A.I.L.E.Y")
        self.resize(1100, 800)
        self.setMinimumSize(700, 500)

        self.build_ui()
        self.apply_style()

        self.input.setFocus()

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Bovenbalk
        header = QWidget()
        header.setObjectName("header")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("H.A.I.L.E.Y")
        title.setObjectName("appTitle")

        subtitle = QLabel("Local AI Assistant")
        subtitle.setObjectName("subtitle")

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Chatgebied
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.scroll.setFrameShape(
            QScrollArea.NoFrame
        )

        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(
            self.chat_container
        )

        self.chat_layout.setContentsMargins(
            100, 25, 100, 25
        )

        self.chat_layout.setSpacing(4)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_container)

        main_layout.addWidget(self.scroll, 1)

        # Invoergebied
        input_area = QWidget()
        input_area.setObjectName("inputArea")

        input_layout = QVBoxLayout(input_area)

        input_layout.setContentsMargins(
            100, 15, 100, 20
        )

        self.input = ChatInput()
        self.input.setObjectName("chatInput")

        self.input.setPlaceholderText(
            "Stel een vraag"
        )

        self.input.setFixedHeight(85)
        self.input.setTabChangesFocus(False)

        buttons = QHBoxLayout()

        self.status = QLabel("Klaar")
        self.status.setObjectName("status")

        buttons.addWidget(self.status)
        buttons.addStretch()

        self.send_button = QPushButton("Versturen")
        self.send_button.setObjectName("sendButton")

        self.send_button.clicked.connect(
            self.send_message
        )

        buttons.addWidget(self.send_button)

        self.activity_info = QLabel(
            "Enter om te versturen · Shift + Enter voor een nieuwe regel"
        )
        self.activity_info.setObjectName("activityInfo")

        input_layout.addWidget(self.input)
        input_layout.addLayout(buttons)
        input_layout.addWidget(self.activity_info)

        main_layout.addWidget(input_area)

    # Berichten toevoegen
    def add_message(self, role, content=""):

        message = ChatMessage(role, content)

        index = self.chat_layout.count() - 1

        self.chat_layout.insertWidget(
            index, message
        )

        QTimer.singleShot(
            50, self.scroll_to_bottom
        )

        return message

    def scroll_to_bottom(self):

        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    # Bericht versturen
    def send_message(self):

        message = self.input.toPlainText().strip()

        if not message or self.worker:
            return

        self.input.clear()

        self.add_message("user", message)

        self.current_message = self.add_message(
            "assistant",
            ""
        )
        self.current_message.set_thinking(True)

        # Invoer tijdelijk uitschakelen
        self.input.setDisabled(True)
        self.send_button.setDisabled(True)

        self.status.setText("...")

# Controleer of er al een worker actief is
        if self.worker is not None and self.worker.isRunning():
          print("[Hailey] Worker is nog bezig.")
          return

# Worker aanmaken
        self.worker = AssistantWorker(
        self.assistant,
        message,
        self
        )

# Signalen verbinden
        self.worker.token.connect(self.receive_token)
        self.worker.status.connect(self.update_status)
        self.worker.finished_response.connect(self.response_finished)
        self.worker.error.connect(self.show_error)

# Worker opruimen na afloop
        self.worker.finished.connect(self.worker.deleteLater)

# Worker starten
        self.worker.start()
     # Tokens ontvangen
    def receive_token(self, token):

        if not self.current_message:
            return

        if self.current_message.spinner.isVisible():
            self.current_message.set_thinking(False)
            self.current_message.set_content(token)
        else:
            self.current_message.set_content(
                self.current_message.content + token
            )

        QTimer.singleShot(
            20, self.scroll_to_bottom
        )

    # Status bijwerken
    def update_status(self, status):

        self.status.setText(status)
        self.activity_info.setText(status)

    # Definitief antwoord ontvangen
    def response_finished(self, response):

        if self.current_message:
            self.current_message.set_content(
                response
            )

        self.finish_worker()

    # Fouten weergeven
    def show_error(self, error):

        if self.current_message:
            self.current_message.set_content(
                f"Er is een fout opgetreden:\n\n{error}"
            )

        self.finish_worker()

    # Worker afsluiten
    def finish_worker(self):

        if self.current_message:
            self.current_message.set_thinking(False)

        self.worker = None
        self.current_message = None

        self.input.setDisabled(False)
        self.send_button.setDisabled(False)

        self.status.setText("Klaar")

        self.input.setFocus()

    # Styling
    def apply_style(self):

        self.setStyleSheet("""
            QMainWindow {
                background: #181818;
            }

            QWidget {
                color: #eeeeee;
                font-family: Segoe UI;
                font-size: 14px;
            }

            #header {
                background: #202020;
                border-bottom: 1px solid #303030;
            }

            #appTitle {
                font-size: 20px;
                font-weight: 600;
            }

            #subtitle {
                color: #888888;
                font-size: 11px;
            }

            #messageName {
                color: #aaaaaa;
                font-size: 13px;
                font-weight: 600;
            }

            #messageText {
                background: transparent;
                border: none;
                color: #eeeeee;
                font-size: 14px;
                padding: 0;
            }

            #messageText a {
                color: #8ab4f8;
            }

            #inputArea {
                background: #181818;
                border-top: 1px solid #303030;
            }

            #chatInput {
                background: #252525;
                border: 1px solid #404040;
                border-radius: 12px;
                padding: 12px;
                color: white;
                font-size: 14px;
            }

            #chatInput:focus {
                border: 1px solid #777777;
            }

            #sendButton {
                background: #eeeeee;
                color: #181818;
                border: none;
                border-radius: 8px;
                padding: 9px 20px;
                font-weight: 600;
            }

            #sendButton:hover {
                background: #cccccc;
            }

            #sendButton:disabled {
                background: #555555;
                color: #999999;
            }

            #status {
                color: #888888;
                font-size: 12px;
            }

            #activityInfo {
                color: #777777;
                font-size: 11px;
                padding-left: 2px;
            }

            QScrollArea {
                border: none;
                background: #181818;
            }

            QScrollBar:vertical {
                background: #181818;
                width: 8px;
            }

            QScrollBar::handle:vertical {
                background: #444444;
                border-radius: 4px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)