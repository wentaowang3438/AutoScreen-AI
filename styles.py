"""
应用全局 QSS - 简约精致浅色，对比度优化
- 更深边框与次要文字，层次更清晰、可读性更好
- get_stylesheet(scale) 支持按 DPI/缩放比例动态放大字号（4K 等高分屏）
"""
# 主背景与表面：背景略深、表面与边框对比更强
_BG = "#f0f2f5"
_SURFACE = "#e4e7eb"
_BORDER = "#cbd5e1"
_BORDER_FOCUS = "#94a3b8"
_TEXT = "#0f172a"
_MUTED = "#334155"
_PRIMARY = "#2563eb"
_CTA = "#16a34a"
_SUCCESS = "#16a34a"
_DANGER = "#dc2626"
_HOVER_BG = "#dde1e6"
_INPUT_BG = "#ffffff"
_DISABLED = "#64748b"
_SELECTION = "#dbeafe"

_FONT = '"Fira Sans", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif'


def get_stylesheet(scale=1.0):
    """
    根据缩放比例生成 QSS。scale=1.0 为 96 DPI 基准；4K 高 DPI 下可传入 >1 以放大字号与控件高度。
    """
    scale = max(1.0, min(2.0, float(scale)))
    fs10 = max(9, round(10 * scale))
    fs9 = max(8, round(9 * scale))
    mh28 = max(24, round(28 * scale))
    mh14 = max(12, round(14 * scale))
    mh32 = max(28, round(32 * scale))
    sb = max(6, round(8 * scale))
    return f"""
QWidget {{
    color: {_TEXT};
    font-size: {fs10}px;
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
    font-size: {fs10}px;
    font-weight: 500;
    font-family: {_FONT};
    padding-left: 12px;
    letter-spacing: 0.02em;
}}

/* 标题栏窗口控制：文字按钮，兼容 PyQt5 */
#TitleBtn {{
    background: transparent;
    border: none;
    border-radius: 4px;
    color: {_MUTED};
    font-weight: 400;
    font-size: {fs10}px;
    min-height: {mh28}px;
    padding: 0 8px;
}}
#TitleBtn:hover {{
    background-color: {_HOVER_BG};
    color: {_TEXT};
}}
#TitleBtn:pressed {{
    background-color: {_BORDER};
}}
#TitleBtn_Close {{
    background: transparent;
    border: none;
    border-radius: 4px;
    color: {_MUTED};
    font-weight: 400;
    font-size: {fs10}px;
    min-height: {mh28}px;
    padding: 0 8px;
}}
#TitleBtn_Close:hover {{
    background-color: {_HOVER_BG};
    color: {_TEXT};
}}
#TitleBtn_Close:pressed {{
    background-color: {_BORDER};
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
    font-size: {fs9}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
    color: {_TEXT};
}}

/* API 配置区：字段标签与内容层级 */
QLabel#ApiFieldLabel {{
    color: {_MUTED};
    font-size: {fs9}px;
    font-weight: 500;
    letter-spacing: 0.02em;
    margin-bottom: 2px;
}}
QLabel#ApiFieldValue {{
    color: {_TEXT};
    font-size: {fs10}px;
    font-weight: 600;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    padding: 8px 10px;
    selection-background-color: {_SELECTION};
    min-height: 1.2em;
    font-size: {fs10}px;
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
    font-size: {fs10}px;
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
    font-size: {fs9}px;
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
    font-size: {fs9}px;
    min-height: {mh14}px;
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
    font-size: {fs10}px;
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
    width: {sb}px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER};
    min-height: {mh32}px;
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
    height: {sb}px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER};
    min-width: {mh32}px;
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

QLabel#HintLabel {{
    color: {_MUTED};
    font-size: {fs9}px;
    font-weight: 400;
}}

QLabel#CountLabel {{
    color: {_MUTED};
    font-size: {fs9}px;
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
    font-size: {fs10}px;
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


# 默认 1.0 缩放，兼容直接 import STYLESHEET 的用法
STYLESHEET = get_stylesheet(1.0)
