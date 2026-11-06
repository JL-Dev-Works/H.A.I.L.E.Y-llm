APP_STYLE = """
QMainWindow {
    background-color: #111318;
}

QWidget {
    color: #e8eaf0;
    font-family: Segoe UI;
    font-size: 14px;
}

QFrame#topbar {
    background-color: #191c24;
    border-bottom: 1px solid #303541;
}

QLabel#title {
    font-size: 21px;
    font-weight: bold;
}

QLabel#status {
    color: #929aaa;
    font-size: 12px;
}

QTextBrowser {
    background: transparent;
    border: none;
    color: #e8eaf0;
}

QPlainTextEdit {
    background-color: #20242e;
    border: 1px solid #393f4c;
    border-radius: 14px;
    padding: 12px;
    color: white;
}

QPlainTextEdit:focus {
    border: 1px solid #7186a8;
}

QPushButton {
    background-color: #dce6f5;
    color: #171b23;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: white;
}

QPushButton:disabled {
    background-color: #555c68;
}
"""