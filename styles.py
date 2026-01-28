"""
应用全局 QSS 样式表 - 浅色白 (Light White)
- 白色为主背景，深色文字，蓝/绿/红为点缀，适合日常办公与数据工具
- 适配高 DPI，强化焦点与可读性
"""
# 配色常量（便于后续微调）
_BG = "#ffffff"         # 主背景 纯白
_SURFACE = "#f8fafc"    # 卡片/区块 slate-50
_BORDER = "#e2e8f0"     # 边框 slate-200
_TEXT = "#0f172a"      # 主文字 slate-900
_MUTED = "#64748b"     # 次要文字 slate-500
_PRIMARY = "#0284c7"   # 主色/焦点 sky-600
_SUCCESS = "#16a34a"   # 成功 green-600
_DANGER = "#dc2626"    # 危险 red-600
_HOVER_BG = "#f1f5f9"  # 悬停 slate-100
_INPUT_BG = "#ffffff"
_DISABLED = "#94a3b8"  # 禁用 slate-400

STYLESHEET = f"""
/* === 基底与字体 === */
QWidget {{
    color: {_TEXT};
    font-size: 13px;
}}

QMainWindow {{
    background-color: transparent;
}}

#MainFrame {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}

/* === 标题栏 === */
#TitleBar {{
    background-color: {_BG};
    border-bottom: 1px solid {_BORDER};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

#TitleLabel {{
    color: {_TEXT};
    font-size: 14px;
    font-weight: bold;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    padding-left: 5px;
}}

#TitleBtn {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: {_MUTED};
    font-weight: 600;
    min-width: 36px;
    min-height: 36px;
}}
#TitleBtn:hover {{
    background-color: {_HOVER_BG};
    color: {_TEXT};
    border-color: {_HOVER_BG};
}}
#TitleBtn:focus {{ outline: none; }}

#TitleBtn_Close {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: {_MUTED};
    font-weight: 600;
    min-width: 36px;
    min-height: 36px;
}}
#TitleBtn_Close:hover {{
    background-color: {_DANGER};
    color: #ffffff;
    border-color: {_DANGER};
}}
#TitleBtn_Close:focus {{ outline: none; }}

/* === 分组框 === */
QGroupBox {{
    border: 2px solid {_BORDER};
    border-radius: 8px;
    margin-top: 20px;
    padding-top: 8px;
    background-color: {_SURFACE};
    font-weight: bold;
    color: {_PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    left: 10px;
}}

/* === 输入框 === */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    padding: 8px 10px;
    selection-background-color: #bae6fd;
    min-height: 1.2em;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {_PRIMARY};
    background-color: {_INPUT_BG};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {_HOVER_BG};
    color: {_DISABLED};
}}
QLineEdit::placeholder, QPlainTextEdit::placeholder {{
    color: {_DISABLED};
}}

/* === 列表 === */
QListWidget {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {_BORDER};
}}
QListWidget::item:selected {{
    background-color: #e0f2fe;
    color: {_TEXT};
}}
QListWidget::item:hover {{
    background-color: {_HOVER_BG};
}}
QListWidget:focus {{
    border: 1px solid {_PRIMARY};
}}

/* === 按钮 === */
QPushButton {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    min-height: 1.4em;
}}
QPushButton:hover {{
    background-color: {_HOVER_BG};
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
}}

QPushButton#PrimaryBtn {{
    background-color: {_PRIMARY};
    color: #ffffff;
    border-color: {_PRIMARY};
}}
QPushButton#PrimaryBtn:hover {{
    background-color: #0369a1;
    border-color: #0369a1;
}}

QPushButton#DangerBtn {{
    background-color: {_DANGER};
    color: #ffffff;
    border-color: {_DANGER};
}}
QPushButton#DangerBtn:hover {{
    background-color: #b91c1c;
    border-color: #b91c1c;
}}
QPushButton#DangerBtn:disabled {{
    background-color: {_SURFACE};
    color: {_DISABLED};
    border-color: {_BORDER};
}}

QPushButton#SuccessBtn {{
    background-color: {_SUCCESS};
    color: #ffffff;
    border-color: {_SUCCESS};
}}
QPushButton#SuccessBtn:hover {{
    background-color: #15803d;
    border-color: #15803d;
}}

QPushButton#SmallBtn {{
    padding: 4px 10px;
    font-size: 12px;
    min-height: 1.2em;
}}

/* === 进度条 === */
QProgressBar {{
    border: 2px solid {_BORDER};
    border-radius: 6px;
    text-align: center;
    color: {_TEXT};
    background-color: {_SURFACE};
    font-weight: bold;
    min-height: 22px;
}}
QProgressBar::chunk {{
    background-color: {_PRIMARY};
    border-radius: 4px;
}}

/* === Tab === */
QTabWidget::pane {{
    border: 1px solid {_BORDER};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: {_SURFACE};
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-bottom-color: {_BORDER};
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 14px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {_BG};
    color: {_PRIMARY};
    border-bottom-color: {_BG};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background: {_HOVER_BG};
}}

/* === 滚动条 === */
QScrollBar:vertical {{
    border: none;
    background: {_SURFACE};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none; background: none; height: 0;
}}

QScrollBar:horizontal {{
    border: none;
    background: {_SURFACE};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER};
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none; background: none; width: 0;
}}

QScrollArea {{
    border: none;
    background: transparent;
    outline: none;
}}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* === 分割器 === */
QSplitter::handle {{
    background: {_BORDER};
    width: 2px;
}}
QSplitter::handle:hover {{
    background: {_PRIMARY};
}}

QSizeGrip {{ background: transparent; width: 16px; height: 16px; }}

QLabel#StatusIcon {{
    font-size: 16px;
    font-weight: bold;
    min-width: 28px;
    min-height: 28px;
    border-radius: 14px;
}}

QLabel#HintLabel {{
    color: {_MUTED};
    font-size: 12px;
}}

QLabel#CountLabel {{
    color: {_MUTED};
    font-size: 12px;
}}

/* === 下拉框 === */
QComboBox {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    padding: 6px 8px;
    selection-background-color: #bae6fd;
    min-height: 1.4em;
}}
QComboBox:hover {{
    border: 1px solid {_PRIMARY};
}}
QComboBox:focus {{
    border: 1px solid {_PRIMARY};
    background-color: {_INPUT_BG};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {_MUTED};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background-color: {_INPUT_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    selection-background-color: #bae6fd;
    selection-color: {_TEXT};
}}
"""
