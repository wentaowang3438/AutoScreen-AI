import sys
import os
import time
import json
import base64
import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QGroupBox, QListWidget, QListWidgetItem, QSplitter, QFrame, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QPoint
from PySide6.QtGui import QIcon, QFont, QColor, QPalette, QMouseEvent

# ======================================================
# ==================   UI 样式表 (QSS)   ================
# ======================================================

STYLESHEET = """
/* === 核心框架样式 === */
QMainWindow {
    background-color: transparent; /* 设为透明，由 MainFrame 接管背景 */
}

/* 主背景容器 (带圆角和边框) */
#MainFrame {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 10px;
}

/* === 自定义标题栏样式 === */
#TitleBar {
    background-color: #1e1e2e;
    border-bottom: 1px solid #313244;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

#TitleLabel {
    color: #cdd6f4;
    font-size: 14px;
    font-weight: bold;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    padding-left: 5px;
}

/* 窗口控制按钮 (最小化/关闭) */
#TitleBtn {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    color: #a6adc8;
    font-weight: bold;
    font-size: 14px;
}
#TitleBtn:hover {
    background-color: #313244;
    color: #ffffff;
}

/* 关闭按钮特化 - 红色悬停 */
#TitleBtn_Close:hover {
    background-color: #f38ba8;
    color: #1e1e2e;
}

/* === 常规控件样式 === */
QWidget {
    color: #cdd6f4;
}

/* 分组框 */
QGroupBox {
    border: 2px solid #313244;
    border-radius: 8px;
    margin-top: 24px;
    background-color: #242536;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    left: 10px;
}

/* 输入框 */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    color: #cdd6f4;
    padding: 8px;
    selection-background-color: #585b70;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
    background-color: #353749;
}
QLineEdit:disabled {
    background-color: #282938;
    color: #6c7086;
}

/* 列表控件 */
QListWidget {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #3e4050;
}
QListWidget::item:selected {
    background-color: #45475a;
    color: #ffffff;
}
QListWidget::item:hover {
    background-color: #3a3c4e;
}

/* 按钮 - 通用 */
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    border: none;
}
QPushButton:hover {
    background-color: #585b70;
}
QPushButton:pressed {
    background-color: #313244;
}

/* 按钮 - 主要操作 (蓝色) */
QPushButton#PrimaryBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QPushButton#PrimaryBtn:hover {
    background-color: #b4befe;
}

/* 按钮 - 危险操作 (红色) */
QPushButton#DangerBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#DangerBtn:hover {
    background-color: #eba0ac;
}
QPushButton#DangerBtn:disabled {
    background-color: #45475a;
    color: #6c7086;
}

/* 按钮 - 成功/绿色 */
QPushButton#SuccessBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
}
QPushButton#SuccessBtn:hover {
    background-color: #94e2d5;
}

/* 进度条 */
QProgressBar {
    border: 2px solid #45475a;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
    background-color: #313244;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 6px;
    top: -1px; 
}
QTabBar::tab {
    background: #313244;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-bottom-color: #45475a;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 12px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1e1e2e;
    color: #89b4fa;
    border-bottom-color: #1e1e2e;
    font-weight: bold;
}

/* 滚动条美化 */
QScrollBar:vertical {
    border: none;
    background: #1e1e2e;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""

# ======================================================
# ============  Core Logic (Backend)  ============
# ======================================================

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".deepseek_config.json")


def encode_key(key: str) -> str:
    return base64.b64encode(key.encode("utf-8")).decode("utf-8")


def decode_key(data: str) -> str:
    try:
        return base64.b64decode(data.encode("utf-8")).decode("utf-8")
    except:
        return ""


def save_api_key(key: str):
    try:
        data = {"api_key": encode_key(key)}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"保存 API Key 失败：{e}")


def load_api_key() -> str:
    if not os.path.exists(CONFIG_PATH):
        return ""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return decode_key(data.get("api_key", ""))
    except:
        return ""


client = None


def call_model(prompt: str, max_retries: int = 3) -> str:
    global client
    if client is None:
        raise RuntimeError("Client 未初始化")

    backoff_base = 2
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.warning(f"模型调用重试 ({attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff_base ** attempt)
            else:
                return ""
    return ""


def process_row(row_index, merged_text, delimiter, prompt_template, cache_key):
    prompt = prompt_template.replace("{merged_text}", merged_text).replace("{delimiter}", delimiter)
    result = call_model(prompt)

    error = False
    error_msg = ""

    if not result:
        error = True
        error_msg = "API 返回空"
        result = f"FAIL{delimiter}FAIL"
    elif delimiter not in result:
        error = True
        error_msg = "缺少分隔符"
        result = f"FAIL{delimiter}FAIL"

    return {
        "index": row_index,
        "output": result,
        "cache_key": cache_key,
        "error": error,
        "error_msg": error_msg,
    }


def run_processing(input_path, cols, delimiter, output_path, prompt, progress_cb, log_cb, stop_flag):
    try:
        df = pd.read_excel(input_path)
    except Exception as e:
        return False, f"读取 Excel 失败: {e}"

    df["AI_Output"] = ""
    total = len(df)
    cache = {}
    results = []
    error_rows = []
    done_cnt = 0

    log_cb(f"开始处理 {total} 行数据...")

    with ThreadPoolExecutor(max_workers=20) as pool:
        tasks = []
        for idx, row in df.iterrows():
            if stop_flag(): break

            # 安全地将列转换为字符串
            row_vals = []
            for c in cols:
                val = row.get(c, "")
                row_vals.append(str(val) if pd.notna(val) else "")

            merged_text = "\n".join(row_vals)
            key = f"{merged_text}|{delimiter}|{prompt}"

            if key in cache:
                cached = cache[key]
                r = {
                    "index": idx,
                    "output": cached["output"],
                    "cache_key": key,
                    "error": cached["error"],
                    "error_msg": cached["error_msg"],
                }
                results.append(r)
                if r["error"]: error_rows.append(idx)
                done_cnt += 1
                progress_cb(done_cnt, total)
            else:
                future = pool.submit(process_row, idx, merged_text, delimiter, prompt, key)
                tasks.append(future)

        for future in as_completed(tasks):
            if stop_flag(): break
            r = future.result()
            results.append(r)
            cache[r["cache_key"]] = {
                "output": r["output"],
                "error": r["error"],
                "error_msg": r["error_msg"],
            }
            if r["error"]:
                error_rows.append(r['index'])
                log_cb(f"[警告] 行 {r['index']} 失败: {r['error_msg']}")

            done_cnt += 1
            progress_cb(done_cnt, total)

    for r in results:
        df.at[r["index"], "AI_Output"] = r["output"]

    try:
        df.to_excel(output_path, index=False)
        log_cb(f"文件已保存至: {output_path}")
    except Exception as e:
        return False, f"保存文件失败: {e}"

    processed_count = len(results)
    if stop_flag():
        return False, f"用户中断。处理 {processed_count}/{total} 行。"
    else:
        status = f"完成。共 {total} 行，失败 {len(error_rows)} 行。"
        return True, status


# ======================================================
# =================       Threads      =================
# ======================================================

class Worker(QThread):
    progress = Signal(int, int, float)
    log_signal = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, input_path, cols, delimiter, output_path, prompt):
        super().__init__()
        self.input_path = input_path
        self.cols = cols
        self.delimiter = delimiter
        self.output_path = output_path
        self.prompt = prompt
        self._stop_flag = False
        self._start_time = None

    def stop(self):
        self._stop_flag = True

    def is_stopped(self):
        return self._stop_flag

    def run(self):
        self._start_time = time.time()

        def prog_cb(done, total):
            elapsed = time.time() - self._start_time if self._start_time else 0
            eta = (total - done) * (elapsed / done) if done > 0 else -1
            self.progress.emit(done, total, eta)

        def log_cb(msg):
            self.log_signal.emit(msg)

        ok, msg = run_processing(
            self.input_path, self.cols, self.delimiter, self.output_path,
            self.prompt, prog_cb, log_cb, self.is_stopped
        )
        self.finished.emit(ok, msg)


class ApiTestThread(QThread):
    finished = Signal(bool, str)

    def __init__(self, client_obj):
        super().__init__()
        self.client = client_obj

    def run(self):
        try:
            resp = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0
            )
            if resp:
                self.finished.emit(True, "API 连接成功！延迟正常。")
            else:
                self.finished.emit(False, "API 返回内容为空。")
        except Exception as e:
            self.finished.emit(False, f"API 连接异常: {str(e)}")


# ======================================================
# ==================   Log Handler   ===================
# ======================================================

class QEditTextLogger(logging.Handler, QObject):
    log_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__()
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)


# ======================================================
# ============  自定义标题栏 (New Feature)  =============
# ======================================================

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(10)

        # 1. 标题文字
        self.title_label = QLabel("DeepSeek Excel 智能批处理工具 Pro")
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label)

        layout.addStretch()  # 弹簧

        # 2. 窗口控制按钮
        self.min_btn = QPushButton("─")
        self.min_btn.setObjectName("TitleBtn")
        self.min_btn.setFixedSize(30, 30)
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.clicked.connect(parent.showMinimized)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("TitleBtn")
        self.close_btn.setObjectName("TitleBtn_Close")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(parent.close)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    # === 拖动逻辑 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent().window_pos = self.parent().pos()
            self.parent().mouse_pos = event.globalPosition().toPoint()
            self.parent().is_dragging = True

    def mouseMoveEvent(self, event):
        if self.parent().is_dragging:
            delta = event.globalPosition().toPoint() - self.parent().mouse_pos
            self.parent().move(self.parent().window_pos + delta)

    def mouseReleaseEvent(self, event):
        self.parent().is_dragging = False


# ======================================================
# ==================      Main UI    ===================
# ======================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. 核心修改：去除原生边框 + 设为透明
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(1100, 750)

        # 拖动状态变量
        self.is_dragging = False
        self.mouse_pos = None
        self.window_pos = None

        # 设置全局 Logging
        self.log_handler = QEditTextLogger()
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%H:%M:%S"))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

        self.worker = None
        self.api_test_thread = None

        self.setup_ui()

        self.log_handler.log_signal.connect(self.append_log)

        key = load_api_key()
        if key:
            self.api_key_edit.setText(key)
            self.append_log("已自动加载保存的 API Key")

    def setup_ui(self):
        # 2. 创建自定义的主背景容器
        self.main_frame = QFrame()
        self.main_frame.setObjectName("MainFrame")  # 对应 CSS 中的 MainFrame
        self.setCentralWidget(self.main_frame)

        # 主布局改用垂直布局，因为要放标题栏
        main_v_layout = QVBoxLayout(self.main_frame)
        main_v_layout.setContentsMargins(0, 0, 0, 0)
        main_v_layout.setSpacing(0)

        # 添加自定义标题栏
        self.title_bar = CustomTitleBar(self)
        main_v_layout.addWidget(self.title_bar)

        # 内容区域容器
        content_widget = QWidget()
        main_v_layout.addWidget(content_widget)

        # 原有的水平布局放入 content_widget
        main_layout = QHBoxLayout(content_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 10, 20, 20)

        # ============= 左侧边栏 (配置区) =============
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 1. API 设置
        api_box = QGroupBox("🔑 API 配置")
        api_layout = QVBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-...")

        self.test_api_btn = QPushButton("测试连接")
        self.test_api_btn.setObjectName("PrimaryBtn")
        self.test_api_btn.clicked.connect(self.test_api)

        api_layout.addWidget(QLabel("API Key:"))
        api_layout.addWidget(self.api_key_edit)
        api_layout.addWidget(self.test_api_btn)
        api_box.setLayout(api_layout)
        left_layout.addWidget(api_box)

        # 2. 文件与列设置
        file_box = QGroupBox("📂 数据源设置")
        file_layout = QVBoxLayout()

        # 输入文件
        file_layout.addWidget(QLabel("输入 Excel:"))
        h1 = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        btn_in = QPushButton("...")
        btn_in.setFixedWidth(30)
        btn_in.clicked.connect(self.choose_input)
        h1.addWidget(self.input_edit)
        h1.addWidget(btn_in)
        file_layout.addLayout(h1)

        # 输出文件
        file_layout.addWidget(QLabel("输出路径:"))
        h2 = QHBoxLayout()
        self.output_edit = QLineEdit("output.xlsx")
        btn_out = QPushButton("...")
        btn_out.setFixedWidth(30)
        btn_out.clicked.connect(self.choose_output)
        h2.addWidget(self.output_edit)
        h2.addWidget(btn_out)
        file_layout.addLayout(h2)

        # 列选择列表
        file_layout.addWidget(QLabel("选择用于合并的列:"))
        self.col_list = QListWidget()
        self.col_list.setSelectionMode(QListWidget.NoSelection)
        file_layout.addWidget(self.col_list)

        file_box.setLayout(file_layout)
        left_layout.addWidget(file_box)

        left_layout.addStretch()

        # ============= 右侧主控区 (操作区) =============
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Tab 页
        self.tabs = QTabWidget()

        # Tab 1: Prompt
        prompt_tab = QWidget()
        p_layout = QVBoxLayout(prompt_tab)

        prompt_header = QHBoxLayout()
        prompt_header.addWidget(QLabel("Prompt 模板 (使用 {merged_text} 和 {delimiter} 占位)"))
        prompt_header.addStretch()
        prompt_header.addWidget(QLabel("输出分隔符:"))
        self.delim_edit = QLineEdit("|")
        self.delim_edit.setFixedWidth(50)
        self.delim_edit.setAlignment(Qt.AlignCenter)
        prompt_header.addWidget(self.delim_edit)

        p_layout.addLayout(prompt_header)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("在此输入你的 Prompt...")
        # 默认 Prompt
        default_prompt = (
            "你是一名专业领域的文献筛选专家。\n\n" "【任务目标】\n" "根据提供的文章内容，判断其是否属于【研究类型名称】类文献，并给出是否保留与匹配评分。\n\n" "【判定标准】\n" "1. 若文章具备以下任意特征，可判断为【研究类型名称】：\n" " - 【特征1】\n" " - 【特征2】\n" " - 【特征3】\n" " - （可自行添加更多特征）\n" "2. 若文章具备以下任意情况，则不属于【研究类型名称】：\n" " - 【排除条件1】\n" " - 【排除条件2】\n" " - 【排除条件3】\n" " - （可自行添加更多排除条件）\n\n" "【输出要求 —— 必须严格遵守】\n" "你必须只输出一行内容，包含以下 3 个字段，严格按顺序输出：\n\n" "① 是否属于【研究类型名称】（只能输出：是 / 否）\n" "② 是否应该保留（只能输出：保留 / 不保留）\n" "③ 匹配评分（0–100 的整数）\n\n" "字段之间必须使用以下分隔符（不得添加空格，不得换行）：\n" "{delimiter}\n\n" "输出格式示例（请严格仿照示例格式输出，但替换为你的判断结果）：\n" "是{delimiter}保留{delimiter}85\n\n" "⚠️ 严格禁止：\n" "- 输出任何换行\n" "- 输出任何解释说明、理由、总结\n" "- 输出任何额外符号、标点、序号\n" "- 输出除三个字段外的任何文字\n" "- 输出前后空格或换行\n\n" "【文章内容】\n" "{merged_text}")
        self.prompt_edit.setPlainText(default_prompt)
        p_layout.addWidget(self.prompt_edit)

        # Tab 2: Logs
        log_tab = QWidget()
        l_layout = QVBoxLayout(log_tab)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("font-family: Consolas; font-size: 12px;")
        l_layout.addWidget(self.log_console)

        self.tabs.addTab(prompt_tab, "📝 Prompt 设置")
        self.tabs.addTab(log_tab, "📟 运行日志")

        right_layout.addWidget(self.tabs)

        # 底部控制条
        control_frame = QFrame()
        control_frame.setObjectName("ControlFrame")
        control_frame.setStyleSheet(
            "QFrame#ControlFrame { background-color: #242536; border-radius: 8px; padding: 10px; }")
        c_layout = QVBoxLayout(control_frame)

        # 进度信息
        info_layout = QHBoxLayout()
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("font-weight: bold; color: #a6adc8;")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        self.eta_label = QLabel("--:--")
        info_layout.addWidget(self.eta_label)
        c_layout.addLayout(info_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        c_layout.addWidget(self.progress_bar)

        # 按钮组
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 开始批量处理")
        self.start_btn.setObjectName("SuccessBtn")
        self.start_btn.setFixedHeight(45)
        self.start_btn.clicked.connect(self.start_processing)

        self.stop_btn = QPushButton("🛑 停止")
        self.stop_btn.setObjectName("DangerBtn")
        self.stop_btn.setFixedHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        c_layout.addLayout(btn_layout)

        right_layout.addWidget(control_frame)

        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    # ================= 逻辑功能实现 =================

    def append_log(self, text):
        self.log_console.append(text)
        if "Error" in text or "失败" in text:
            pass

    def get_client(self):
        global client
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key")
            return None
        save_api_key(api_key)
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        return client

    def test_api(self):
        c = self.get_client()
        if not c: return

        self.test_api_btn.setEnabled(False)
        self.test_api_btn.setText("连接中...")
        self.append_log("正在测试 API 连接...")

        self.api_test_thread = ApiTestThread(c)
        self.api_test_thread.finished.connect(self.on_api_test_finished)
        self.api_test_thread.start()

    def on_api_test_finished(self, ok, msg):
        self.test_api_btn.setEnabled(True)
        self.test_api_btn.setText("测试连接")
        if ok:
            QMessageBox.information(self, "成功", msg)
            self.append_log(f"[成功] {msg}")
        else:
            QMessageBox.warning(self, "失败", msg)
            self.append_log(f"[失败] {msg}")

    def choose_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Excel", "", "Excel Files (*.xlsx *.xls)")
        if path:
            self.input_edit.setText(path)
            self.load_columns(path)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存路径", "output.xlsx", "Excel Files (*.xlsx)")
        if path:
            self.output_edit.setText(path)

    def load_columns(self, path):
        try:
            df = pd.read_excel(path, nrows=5)
            cols = df.columns.tolist()
            self.col_list.clear()
            for c in cols:
                item = QListWidgetItem(str(c))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.col_list.addItem(item)
            self.append_log(f"已加载文件列: {len(cols)} 列")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取文件: {e}")

    def start_processing(self):
        if not self.get_client(): return

        input_path = self.input_edit.text()
        output_path = self.output_edit.text()
        prompt = self.prompt_edit.toPlainText()
        delimiter = self.delim_edit.text()

        selected_cols = []
        for index in range(self.col_list.count()):
            item = self.col_list.item(index)
            if item.checkState() == Qt.Checked:
                selected_cols.append(item.text())

        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "提示", "请输入有效的输入文件路径")
            return
        if not selected_cols:
            QMessageBox.warning(self, "提示", "请至少勾选一列数据")
            return
        if not delimiter:
            QMessageBox.warning(self, "提示", "分隔符不能为空")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_console.clear()
        self.tabs.setCurrentIndex(1)

        self.worker = Worker(input_path, selected_cols, delimiter, output_path, prompt)
        self.worker.progress.connect(self.on_progress)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def stop_processing(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("正在停止...")
            self.append_log("正在请求停止任务...")

    def on_progress(self, done, total, eta):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)

        if eta >= 0:
            m, s = divmod(int(eta), 60)
            h, m = divmod(m, 60)
            eta_str = f"{h:02d}:{m:02d}:{s:02d}"
            self.eta_label.setText(f"剩余时间: {eta_str}")

        self.status_label.setText(f"进度: {done}/{total}")

    def on_worker_finished(self, ok, msg):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("🛑 停止")
        self.status_label.setText("任务结束")
        self.eta_label.setText("--:--")

        if ok:
            QMessageBox.information(self, "完成", msg)
            self.append_log(f"✅ {msg}")
        else:
            if "用户中断" in msg:
                QMessageBox.warning(self, "中断", msg)
                self.append_log(f"⚠️ {msg}")
            else:
                QMessageBox.critical(self, "错误", msg)
                self.append_log(f"❌ {msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())