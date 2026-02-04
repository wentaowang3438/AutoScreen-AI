"""
应用全局 QSS - 简约精致浅色
- 轻边框、小圆角、适度留白、字重克制
"""
_BG = "#ffffff"
_SURFACE = "#fafafa"
_BORDER = "#f1f5f9"
_BORDER_FOCUS = "#e2e8f0"
_TEXT = "#0f172a"
_MUTED = "#64748b"
_PRIMARY = "#2563eb"
_CTA = "#16a34a"
_SUCCESS = "#16a34a"
_DANGER = "#dc2626"
_HOVER_BG = "#f8fafc"
_INPUT_BG = "#ffffff"
_DISABLED = "#94a3b8"
_SELECTION = "#eff6ff"

_FONT = '"Fira Sans", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif'

STYLESHEET = f"""
QWidget {{
    color: {_TEXT};
    font-size: 10px;
    font-family: {_FONT};
}}

QMainWindow {{ background-color: transparent; }}

#MainFrame {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}

#TitleBar {{
    background-color: {_BG};
    border-bottom: 1px solid {_BORDER};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

#TitleLabel {{
    color: {_TEXT};
    font-size: 10px;
    font-weight: 500;
    font-family: {_FONT};
    padding-left: 12px;
    letter-spacing: 0.02em;
}}

#TitleBtn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {_MUTED};
    font-weight: 500;
    font-size: 9px;
    min-width: 32px;
    min-height: 32px;
}}
#TitleBtn:hover {{
    background-color: {_HOVER_BG};
    color: {_TEXT};
}}
#TitleBtn_Close {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {_MUTED};
    font-weight: 500;
    min-width: 32px;
    min-height: 32px;
}}
#TitleBtn_Close:hover {{
    background-color: #fef2f2;
    color: {_DANGER};
}}

QGroupBox {{
    border: 1px solid {_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    padding-top: 14px;
    background-color: transparent;
    font-weight: 500;
    color: {_MUTED};
    font-size: 9px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
    color: {_TEXT};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    padding: 8px 10px;
    selection-background-color: {_SELECTION};
    min-height: 1.2em;
    font-size: 10px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {_PRIMARY};
    background-color: {_INPUT_BG};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {_HOVER_BG};
    color: {_DISABLED};
}}
QLineEdit::placeholder, QPlainTextEdit::placeholder {{ color: {_DISABLED}; }}

QListWidget {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {_BORDER};
}}
QListWidget::item:selected {{
    background-color: {_SELECTION};
    color: {_TEXT};
}}
QListWidget::item:hover {{
    background-color: {_HOVER_BG};
}}
QListWidget:focus {{ border: 1px solid {_PRIMARY}; }}

QPushButton {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    min-height: 1.2em;
    font-size: 10px;
}}
QPushButton:hover {{
    background-color: {_HOVER_BG};
    border-color: {_BORDER_FOCUS};
}}
QPushButton:pressed {{
    background-color: {_BORDER};
}}
QPushButton:focus {{
    outline: none;
    border: 1px solid {_PRIMARY};
}}
QPushButton:disabled {{
    background-color: {_SURFACE};
    color: {_DISABLED};
    border-color: {_BORDER};
}}

QPushButton#PrimaryBtn {{
    background-color: {_PRIMARY};
    color: #fff;
    border-color: {_PRIMARY};
}}
QPushButton#PrimaryBtn:hover {{
    background-color: #1d4ed8;
    border-color: #1d4ed8;
}}

QPushButton#DangerBtn {{
    background-color: #fff;
    color: {_DANGER};
    border-color: #fecaca;
}}
QPushButton#DangerBtn:hover {{
    background-color: #fef2f2;
    border-color: #fca5a5;
}}
QPushButton#DangerBtn:disabled {{
    background-color: {_SURFACE};
    color: {_DISABLED};
    border-color: {_BORDER};
}}

QPushButton#SuccessBtn {{
    background-color: {_CTA};
    color: #fff;
    border-color: {_CTA};
}}
QPushButton#SuccessBtn:hover {{
    background-color: #15803d;
    border-color: #15803d;
}}

QPushButton#SmallBtn {{
    padding: 4px 8px;
    font-size: 9px;
    font-weight: 500;
    min-height: 1.1em;
}}

QProgressBar {{
    border: 1px solid {_BORDER};
    border-radius: 6px;
    text-align: center;
    color: {_MUTED};
    background-color: {_SURFACE};
    font-weight: 500;
    font-size: 9px;
    min-height: 14px;
}}
QProgressBar::chunk {{
    background-color: {_PRIMARY};
    border-radius: 4px;
}}

QTabWidget::pane {{
    border: 1px solid {_BORDER};
    border-radius: 8px;
    top: -1px;
    padding: 8px;
}}
QTabBar::tab {{
    background: transparent;
    color: {_MUTED};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 14px;
    margin-right: 4px;
    font-weight: 500;
    font-size: 10px;
}}
QTabBar::tab:selected {{
    color: {_PRIMARY};
    border-bottom: 2px solid {_PRIMARY};
}}
QTabBar::tab:hover:!selected {{
    color: {_TEXT};
}}

QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER};
    min-height: 32px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none; background: none; height: 0;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER};
    min-width: 32px;
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none; background: none; width: 0;
}}

QScrollArea {{ border: none; background: transparent; outline: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QSplitter::handle {{
    background: {_BORDER};
    width: 1px;
}}
QSplitter::handle:hover {{ background: {_MUTED}; }}

QSizeGrip {{ background: transparent; width: 12px; height: 12px; }}

QLabel#StatusIcon {{
    font-size: 10px;
    font-weight: 500;
    min-width: 24px;
    min-height: 24px;
    border-radius: 12px;
}}

QLabel#HintLabel {{
    color: {_MUTED};
    font-size: 9px;
    font-weight: 400;
}}

QLabel#CountLabel {{
    color: {_MUTED};
    font-size: 9px;
    font-weight: 400;
}}

QComboBox {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    padding: 8px 12px;
    selection-background-color: {_SELECTION};
    min-height: 1.3em;
    font-size: 10px;
}}
QComboBox:hover {{ border: 1px solid {_BORDER_FOCUS}; }}
QComboBox:focus {{ border: 1px solid {_PRIMARY}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 5px solid {_MUTED};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    selection-background-color: {_SELECTION};
    selection-color: {_TEXT};
}}
"""
