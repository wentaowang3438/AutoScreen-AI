"""
主窗口：界面布局、事件与业务逻辑入口
- 使用 QSplitter + QScrollArea 提升适配性与小窗口体验
- API Key 显隐、列全选/取消全选、快捷键与状态提示
"""
import os
import sys
import json
import time
import logging
import subprocess

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QTabWidget,
    QInputDialog,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QShortcut,
    QMenu,
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

from config import (
    TEMPLATE_DIR,
    load_api_profile,
    load_current_profile_id,
    save_api_profile,
    clear_api_profile,
    load_max_workers,
    save_max_workers,
)
from api import init_client
from widgets import CustomTitleBar, QEditTextLogger
from workers import Worker, ApiTestThread


# 布局常量，便于统一调整
LEFT_PANEL_WIDTH = 320
LEFT_PANEL_MIN = 260
LEFT_PANEL_MAX = 460

# 硅基流动 API 配置（模型名可在界面中修改，如 THUDM/GLM-4-9B-0414）
SILICONFLOW_PROFILE = {
    "id": "siliconflow",
    "label": "硅基流动 SiliconFlow",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "THUDM/GLM-4-9B-0414",
}

# 默认 Prompt 模板（文献筛选示例）
DEFAULT_PROMPT = (
    "你是一名专业领域的文献筛选专家。\n\n"
    "【任务目标】\n"
    "根据提供的文章内容，判断其是否属于【研究类型名称】类文献，并给出是否保留与匹配评分。\n\n"
    "【判定标准】\n"
    "1. 若文章具备以下任意特征，可判断为【研究类型名称】：\n"
    " - 【特征1】\n - 【特征2】\n - 【特征3】\n - （可自行添加更多特征）\n"
    "2. 若文章具备以下任意情况，则不属于【研究类型名称】：\n"
    " - 【排除条件1】\n - 【排除条件2】\n - 【排除条件3】\n - （可自行添加更多排除条件）\n\n"
    "【输出要求 —— 必须严格遵守】\n"
    "你必须只输出一行内容，包含以下 3 个字段，严格按顺序输出：\n\n"
    "① 是否属于【研究类型名称】（只能输出：是 / 否）\n"
    "② 是否应该保留（只能输出：保留 / 不保留）\n"
    "③ 匹配评分（0–100 的整数）\n\n"
    "字段之间必须使用以下分隔符（不得添加空格，不得换行）：\n"
    "{delimiter}\n\n"
    "输出格式示例（请严格仿照示例格式输出，但替换为你的判断结果）：\n"
    "是{delimiter}保留{delimiter}85\n\n"
    "⚠️ 严格禁止：\n"
    "- 输出任何换行\n- 输出任何解释说明、理由、总结\n"
    "- 输出任何额外符号、标点、序号\n- 输出除三个字段外的任何文字\n- 输出前后空格或换行\n\n"
    "【文章内容】\n"
    "{merged_text}"
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(960, 640)
        self.setMinimumSize(640, 420)

        os.makedirs(TEMPLATE_DIR, exist_ok=True)

        self.log_handler = QEditTextLogger(self)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
        )
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

        self.worker = None
        self.api_test_thread = None

        self.setup_ui()

        self.log_handler.log_signal.connect(self.append_log)

        # === 从本地配置恢复 API Key 与模型名 ===
        if hasattr(self, "api_key_edit") and hasattr(self, "model_name_edit"):
            profile = SILICONFLOW_PROFILE
            cfg = load_api_profile(
                profile_id=profile["id"],
                default_base_url=profile["base_url"],
                default_model=profile["model"],
            )
            key = cfg.get("api_key") or ""
            if key:
                self.api_key_edit.setText(key)
                self.append_log(f"已自动加载保存的 API Key")
            model = cfg.get("model") or profile["model"]
            self.model_name_edit.setText(model)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.update_max_button()
        super(MainWindow, self).changeEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(1000)
        if hasattr(self, "api_test_thread") and self.api_test_thread and self.api_test_thread.isRunning():
            self.api_test_thread.terminate()
            self.api_test_thread.wait(1000)
        for attr in ("left_panel_animation", "content_animation"):
            if hasattr(self, attr):
                o = getattr(self, attr, None)
                if o:
                    try:
                        o.stop()
                    except Exception:
                        pass
        if hasattr(self, "log_handler") and self.log_handler:
            try:
                self.log_handler.log_signal.disconnect()
            except Exception:
                pass
            try:
                logging.getLogger().removeHandler(self.log_handler)
            except Exception:
                pass
        event.accept()

    def setup_ui(self):
        self.main_frame = QFrame()
        self.main_frame.setObjectName("MainFrame")
        self.setCentralWidget(self.main_frame)

        main_v_layout = QVBoxLayout(self.main_frame)
        main_v_layout.setContentsMargins(0, 0, 0, 0)
        main_v_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        main_v_layout.addWidget(self.title_bar)

        content_widget = QWidget()
        main_v_layout.addWidget(content_widget)

        main_layout = QHBoxLayout(content_widget)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(0)

        # 左侧边栏（可折叠、可拖拽分割）
        left_panel = QWidget()
        left_panel.setMinimumWidth(LEFT_PANEL_MIN)
        left_panel.setMaximumWidth(LEFT_PANEL_MAX)
        left_panel.setObjectName("LeftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.left_content = QWidget()
        left_content_layout = QVBoxLayout(self.left_content)
        left_content_layout.setContentsMargins(4, 2, 6, 6)
        left_content_layout.setSpacing(10)

        # 1) API 配置
        api_box = QGroupBox("API 配置")
        api_layout = QVBoxLayout()
        api_layout.setSpacing(6)

        # 平台（固定为硅基流动）+ 模型名：标签与内容分行、样式区分
        platform_row = QHBoxLayout()
        platform_row.setSpacing(8)
        lbl_platform = QLabel("平台")
        lbl_platform.setObjectName("ApiFieldLabel")
        platform_row.addWidget(lbl_platform)
        lbl_platform_value = QLabel("硅基流动 SiliconFlow")
        lbl_platform_value.setObjectName("ApiFieldValue")
        platform_row.addWidget(lbl_platform_value, 1, Qt.AlignLeft)
        api_layout.addLayout(platform_row)

        lbl_model = QLabel("模型名")
        lbl_model.setObjectName("ApiFieldLabel")
        api_layout.addWidget(lbl_model)
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("如 THUDM/GLM-4-9B-0414")
        self.model_name_edit.setToolTip("硅基流动支持的模型名，修改后即可使用该模型")
        self.model_name_edit.setMinimumHeight(24)
        api_layout.addWidget(self.model_name_edit)

        # API Key
        lbl_key = QLabel("API Key")
        lbl_key.setObjectName("ApiFieldLabel")
        api_layout.addWidget(lbl_key)
        api_key_row = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-...（必填）")
        self.api_key_edit.setToolTip(
            "平台提供的 API Key"
        )
        self.api_key_edit.setMinimumHeight(24)
        self._api_key_visible = False
        self.api_key_toggle_btn = QPushButton("显示")
        self.api_key_toggle_btn.setObjectName("SmallBtn")
        self.api_key_toggle_btn.setFixedWidth(36)
        self.api_key_toggle_btn.setToolTip("切换显示/隐藏 API Key")
        self.api_key_toggle_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_row.addWidget(self.api_key_edit)
        api_key_row.addWidget(self.api_key_toggle_btn)
        api_layout.addLayout(api_key_row)

        self.test_api_btn = QPushButton("测试连接")
        self.test_api_btn.setObjectName("PrimaryBtn")
        self.test_api_btn.setToolTip("验证当前平台和模型下 API Key 是否可用")
        self.test_api_btn.clicked.connect(self.test_api)
        api_layout.addWidget(self.test_api_btn)

        self.clear_api_btn = QPushButton("清除保存的 API")
        self.clear_api_btn.setObjectName("DangerBtn")
        self.clear_api_btn.setToolTip("清除当前平台保存的 API Key")
        self.clear_api_btn.clicked.connect(self.clear_saved_api)
        api_layout.addWidget(self.clear_api_btn)

        # 并发设置
        lbl_workers = QLabel("并发线程数")
        lbl_workers.setObjectName("ApiFieldLabel")
        api_layout.addWidget(lbl_workers)
        workers_row = QHBoxLayout()
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setMinimum(1)
        self.max_workers_spin.setMaximum(100)
        self.max_workers_spin.setValue(load_max_workers())
        self.max_workers_spin.setToolTip("设置同时处理的线程数（1-100），影响处理速度")
        self.max_workers_spin.setMinimumWidth(80)
        self.max_workers_spin.valueChanged.connect(self._on_max_workers_changed)
        workers_row.addWidget(self.max_workers_spin)
        workers_row.addWidget(QLabel("（建议值：10-30）"))
        workers_row.addStretch()
        api_layout.addLayout(workers_row)

        api_box.setLayout(api_layout)
        left_content_layout.addWidget(api_box)

        # 2) 数据源
        file_box = QGroupBox("数据源")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(6)
        file_layout.addWidget(QLabel("输入 Excel"))
        h1 = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        self.input_edit.setPlaceholderText("未选择")
        self.input_edit.setToolTip("支持 .xlsx / .xls")
        self.input_edit.setMinimumHeight(24)
        btn_in = QPushButton("…")
        btn_in.setObjectName("SmallBtn")
        btn_in.setFixedWidth(30)
        btn_in.setToolTip("选择文件 (Ctrl+O)")
        btn_in.clicked.connect(self.choose_input)
        h1.addWidget(self.input_edit)
        h1.addWidget(btn_in)
        file_layout.addLayout(h1)
        file_layout.addWidget(QLabel("输出路径"))
        h2 = QHBoxLayout()
        self.output_edit = QLineEdit("output.xlsx")
        self.output_edit.setToolTip("结果将写入该文件，并增加 AI_Output 列")
        self.output_edit.setMinimumHeight(24)
        btn_out = QPushButton("…")
        btn_out.setObjectName("SmallBtn")
        btn_out.setFixedWidth(30)
        btn_out.setToolTip("选择保存位置")
        btn_out.clicked.connect(self.choose_output)
        h2.addWidget(self.output_edit)
        h2.addWidget(btn_out)
        file_layout.addLayout(h2)
        file_layout.addWidget(QLabel("参与合并的列"))
        col_header = QHBoxLayout()
        self.col_select_all_btn = QPushButton("全选")
        self.col_select_all_btn.setObjectName("SmallBtn")
        self.col_select_all_btn.setToolTip("勾选全部列")
        self.col_select_all_btn.clicked.connect(self._col_select_all)
        self.col_select_none_btn = QPushButton("取消")
        self.col_select_none_btn.setObjectName("SmallBtn")
        self.col_select_none_btn.setToolTip("取消全部勾选")
        self.col_select_none_btn.clicked.connect(self._col_select_none)
        self.col_count_label = QLabel("已选 0 列")
        self.col_count_label.setObjectName("CountLabel")
        col_header.addWidget(self.col_select_all_btn)
        col_header.addWidget(self.col_select_none_btn)
        col_header.addStretch()
        col_header.addWidget(self.col_count_label)
        file_layout.addLayout(col_header)
        self.col_list = QListWidget()
        self.col_list.setSelectionMode(QListWidget.NoSelection)
        self.col_list.setMinimumHeight(72)
        self.col_list.setToolTip("勾选要参与合并的列，多选")
        self.col_list.itemChanged.connect(self._on_col_selection_changed)
        file_layout.addWidget(self.col_list)
        self.col_hint = QLabel("请先选择 Excel 文件以加载列")
        self.col_hint.setObjectName("HintLabel")
        self.col_hint.setWordWrap(True)
        file_layout.addWidget(self.col_hint)
        file_box.setLayout(file_layout)
        left_content_layout.addWidget(file_box)
        left_content_layout.addStretch()
        left_scroll.setWidget(self.left_content)
        left_layout.addWidget(left_scroll, 1)  # 滚动区占满剩余空间

        # 分割器：左 | 右
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(left_panel)

        # 右侧主控区
        right_panel = QWidget()
        right_panel.setMinimumWidth(360)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()

        prompt_tab = QWidget()
        p_layout = QVBoxLayout(prompt_tab)
        p_layout.setSpacing(8)
        prompt_header = QHBoxLayout()
        prompt_header.addWidget(
            QLabel("Prompt 模板（占位符: {merged_text}、{delimiter}）")
        )
        prompt_header.addStretch()
        prompt_header.addWidget(QLabel("输出分隔符"))
        self.delim_edit = QLineEdit("|")
        self.delim_edit.setFixedWidth(48)
        self.delim_edit.setAlignment(Qt.AlignCenter)
        self.delim_edit.setToolTip("AI 返回字段间的分隔符，如 | 或 \\t")
        prompt_header.addWidget(self.delim_edit)
        p_layout.addLayout(prompt_header)

        template_header = QHBoxLayout()
        template_header.addWidget(QLabel("模板"))
        self.template_btn = QPushButton("-- 选择模板 --")
        self.template_btn.setMinimumWidth(150)
        self.template_btn.setToolTip("点击选择已保存的 Prompt 模板")
        self.template_btn.clicked.connect(self._show_template_menu)
        self._current_template_name = None
        self._template_list = []
        template_header.addWidget(self.template_btn)
        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.setObjectName("PrimaryBtn")
        self.save_template_btn.setToolTip("将当前 Prompt 保存为模板")
        self.save_template_btn.clicked.connect(self.save_prompt_template)
        template_header.addWidget(self.save_template_btn)
        self.delete_template_btn = QPushButton("删除")
        self.delete_template_btn.setObjectName("DangerBtn")
        self.delete_template_btn.setToolTip("删除选中的模板")
        self.delete_template_btn.clicked.connect(self.delete_prompt_template)
        self.refresh_templates_btn = QPushButton("刷新")
        self.refresh_templates_btn.setToolTip("重新从磁盘加载模板列表")
        self.refresh_templates_btn.clicked.connect(self.refresh_template_list)
        template_header.addWidget(self.refresh_templates_btn)
        self.reset_template_btn = QPushButton("重置为默认")
        self.reset_template_btn.setToolTip("将 Prompt 与分隔符恢复为内置默认模板")
        self.reset_template_btn.clicked.connect(self.reset_to_default_template)
        template_header.addWidget(self.reset_template_btn)
        template_header.addStretch()
        p_layout.addLayout(template_header)
        self.refresh_template_list()

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("在此输入你的 Prompt...")
        self.prompt_edit.setToolTip(
            "输入 AI Prompt 模板\n使用 {merged_text} 占位符表示合并后的列内容\n使用 {delimiter} 占位符表示输出分隔符"
        )
        self.prompt_edit.setMinimumHeight(100)
        self.prompt_edit.setPlainText(DEFAULT_PROMPT)
        p_layout.addWidget(self.prompt_edit)

        log_tab = QWidget()
        l_layout = QVBoxLayout(log_tab)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(88)
        self.log_console.setStyleSheet("font-family: 'Fira Code', 'Consolas', monospace; font-size: 9px; color: #334155;")
        l_layout.addWidget(self.log_console)

        self.tabs.addTab(prompt_tab, "Prompt")
        self.tabs.addTab(log_tab, "日志")
        self.tabs.setMinimumHeight(160)
        right_layout.addWidget(self.tabs)

        control_frame = QFrame()
        control_frame.setObjectName("ControlFrame")
        control_frame.setStyleSheet(
            "QFrame#ControlFrame { background-color: #eef0f2; border-radius: 8px; padding: 10px 14px; border: 1px solid #e4e7eb; }"
        )
        c_layout = QVBoxLayout(control_frame)
        c_layout.setSpacing(8)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignVCenter)
        self.status_label = QLabel("准备就绪 · 请先配置 API、选择文件与列")
        self.status_label.setStyleSheet("font-family: 'Fira Sans', 'Microsoft YaHei UI', sans-serif; font-weight: 500; color: #64748b; font-size: 10px;")
        self.status_label.setToolTip("当前状态与下一步提示")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        self.eta_label = QLabel("\u2014\u2014:\u2014\u2014")  # --:--
        self.eta_label.setStyleSheet("font-family: 'Fira Code', 'Consolas', monospace; font-size: 9px; color: #64748b; min-width: 72px;")
        self.eta_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.eta_label.setToolTip("预计剩余时间")
        info_layout.addWidget(self.eta_label)
        c_layout.addLayout(info_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setToolTip("显示处理进度")
        c_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.start_btn = QPushButton("开始批量处理")
        self.start_btn.setObjectName("SuccessBtn")
        self.start_btn.setFixedHeight(30)
        self.start_btn.setToolTip("开始处理 (F5)")
        self.start_btn.clicked.connect(self.start_processing)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("DangerBtn")
        self.stop_btn.setFixedHeight(30)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("停止当前任务")
        self.stop_btn.clicked.connect(self.stop_processing)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        c_layout.addLayout(btn_layout)
        right_layout.addWidget(control_frame)

        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([LEFT_PANEL_WIDTH, 680])
        main_layout.addWidget(self.main_splitter)

        # 设计系统: 所有可点击元素手型光标 (MASTER: cursor-pointer)
        for btn in self.main_frame.findChildren(QPushButton):
            btn.setCursor(Qt.PointingHandCursor)
        for w in [self.model_name_edit, self.template_btn, self.col_list]:
            w.setCursor(Qt.PointingHandCursor)

        self._setup_shortcuts()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self.choose_input)
        QShortcut(QKeySequence("F5"), self, self._shortcut_start)

    def _shortcut_start(self):
        if hasattr(self, "start_btn") and self.start_btn and self.start_btn.isEnabled():
            self.start_processing()

    def _toggle_api_key_visibility(self):
        self._api_key_visible = not self._api_key_visible
        self.api_key_edit.setEchoMode(
            QLineEdit.Normal if self._api_key_visible else QLineEdit.Password
        )
        self.api_key_toggle_btn.setText("隐藏" if self._api_key_visible else "显示")

    def _col_select_all(self):
        for i in range(self.col_list.count()):
            it = self.col_list.item(i)
            if it:
                it.setCheckState(Qt.Checked)
        self._on_col_selection_changed()

    def _col_select_none(self):
        for i in range(self.col_list.count()):
            it = self.col_list.item(i)
            if it:
                it.setCheckState(Qt.Unchecked)
        self._on_col_selection_changed()

    def _on_col_selection_changed(self):
        n = sum(
            1
            for i in range(self.col_list.count())
            if self.col_list.item(i) and self.col_list.item(i).checkState() == Qt.Checked
        )
        self.col_count_label.setText(f"已选 {n} 列")
        if hasattr(self, "col_hint") and self.col_list.count() > 0:
            self.col_hint.setText("勾选需要参与合并并发送给 AI 的列")

    # ===== API Profile & Client =====

    def _get_current_profile(self) -> dict:
        """返回当前使用的硅基流动 profile。"""
        return SILICONFLOW_PROFILE

    def _get_current_model(self) -> str:
        """返回当前使用的模型名（从输入框读取，空则用默认）。"""
        model = self.model_name_edit.text().strip() if hasattr(self, "model_name_edit") else ""
        return model or SILICONFLOW_PROFILE["model"]

    def refresh_template_list(self):
        if not hasattr(self, "template_btn") or not self.template_btn:
            return
        template_dir = os.path.abspath(os.path.normpath(TEMPLATE_DIR))
        self._template_list = []
        if os.path.isdir(template_dir):
            for filename in os.listdir(template_dir):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(template_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._template_list.append({
                            "name": data.get("name", filename[:-5]),
                            "filename": filename,
                            "created_time": data.get("created_time", ""),
                        })
                except (json.JSONDecodeError, OSError) as e:
                    logging.warning(f"无法加载模板 {filename}: {e}")
            self._template_list.sort(key=lambda x: x["name"])
        names = [t["name"] for t in self._template_list]
        if self._current_template_name not in names:
            self._current_template_name = None
        self.template_btn.setText(self._current_template_name or "-- 选择模板 --")

    def _sanitize_template_filename(self, name):
        """将模板名称转为安全文件名（避免 Windows 非法字符）。"""
        invalid = r'\/:*?"<>|'
        return "".join(c if c not in invalid else "_" for c in name.strip()) or "template"

    def _find_template_file_by_name(self, template_name):
        """
        根据模板显示名称查找对应的模板文件路径。
        先按 data['name'] 匹配，再按文件名「名称.json」匹配，避免编码或时序问题。
        返回: (filepath, filename) 或 (None, None)。
        """
        if not template_name or not template_name.strip():
            return None, None
        name = template_name.strip()
        template_dir = os.path.abspath(os.path.normpath(TEMPLATE_DIR))
        if not os.path.isdir(template_dir):
            return None, None
        # 1) 按 JSON 内 name 字段匹配
        for filename in sorted(os.listdir(template_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(template_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if (data.get("name") or "").strip() == name:
                    return filepath, filename
            except (json.JSONDecodeError, OSError):
                continue
        # 2) 备用：按「安全文件名.json」直接匹配
        safe = self._sanitize_template_filename(name)
        candidate = os.path.join(template_dir, f"{safe}.json")
        if os.path.isfile(candidate):
            return candidate, f"{safe}.json"
        return None, None

    def save_prompt_template(self):
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "提示", "Prompt 内容不能为空")
            return
        default_name = self._current_template_name or ""
        name, ok = QInputDialog.getText(self, "保存模板", "请输入模板名称:", text=default_name)
        if not ok or not name.strip():
            return
        name = name.strip()
        safe_filename = self._sanitize_template_filename(name)
        filepath = os.path.join(TEMPLATE_DIR, f"{safe_filename}.json")
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    old = json.load(f)
                created_time = old.get("created_time", created_time)
            except (json.JSONDecodeError, OSError):
                pass
            reply = QMessageBox.question(
                self, "确认覆盖",
                f"已存在同名模板「{name}」，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        template_data = {
            "name": name,
            "content": prompt_text,
            "delimiter": self.delim_edit.text(),
            "created_time": created_time,
            "updated_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            os.makedirs(TEMPLATE_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", f"模板「{name}」已保存")
            self.refresh_template_list()
            self._current_template_name = name
            self.template_btn.setText(name)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模板失败: {e}")

    def _show_template_menu(self):
        """在模板按钮下方弹出菜单：选择模板、刷新、打开文件夹、重命名/删除当前。"""
        self.refresh_template_list()
        menu = QMenu(self)
        if not self._template_list:
            action = menu.addAction("（暂无已保存的模板）")
            action.setEnabled(False)
        else:
            for t in self._template_list:
                name, created = t["name"], t.get("created_time", "")
                label = f"{name}  ·  {created}" if created else name
                action = menu.addAction(label)
                action.setToolTip(f"加载模板：{name}")
                action.triggered.connect(lambda checked, n=name: self._on_template_chosen(n))
        menu.addSeparator()
        menu.addAction("另存为...", self.duplicate_prompt_template)
        menu.addAction("刷新列表", self.refresh_template_list)
        menu.addAction("打开模板文件夹", self._open_templates_folder)
        if self._current_template_name:
            menu.addSeparator()
            menu.addAction(f"重命名「{self._current_template_name}」", self.rename_prompt_template)
            menu.addAction(f"删除「{self._current_template_name}」", self.delete_prompt_template)
        menu.exec_(self.template_btn.mapToGlobal(self.template_btn.rect().bottomLeft()))

    def _on_template_chosen(self, template_name):
        """菜单选中某项后加载该模板并更新按钮文字。"""
        self.load_prompt_template(template_name)

    def reset_to_default_template(self):
        """将 Prompt 与分隔符恢复为内置默认模板，并清除当前模板选中。"""
        self.prompt_edit.setPlainText(DEFAULT_PROMPT)
        self.delim_edit.setText("|")
        self._current_template_name = None
        self.template_btn.setText("-- 选择模板 --")
        self.append_log("已重置为默认模板")

    def load_prompt_template(self, template_name=None):
        """根据模板名称加载内容到编辑框，并更新当前模板名与按钮文字。"""
        name = (template_name or self._current_template_name or "").strip()
        if not name:
            return
        filepath, _ = self._find_template_file_by_name(name)
        if not filepath or not os.path.isfile(filepath):
            QMessageBox.warning(self, "错误", "未找到该模板文件，请刷新后重试")
            self.refresh_template_list()
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.prompt_edit.setPlainText(data.get("content", ""))
            if "delimiter" in data:
                self.delim_edit.setText(data["delimiter"])
            self._current_template_name = name
            self.template_btn.setText(name)
            self.append_log(f"已加载模板: {name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板失败: {e}")

    def delete_prompt_template(self):
        template_name = (self._current_template_name or "").strip()
        if not template_name:
            QMessageBox.warning(self, "提示", "请先通过「模板」按钮选择并加载要删除的模板")
            return
        filepath, _ = self._find_template_file_by_name(template_name)
        if not filepath:
            QMessageBox.warning(self, "提示", "未找到该模板文件，请刷新模板列表后重试")
            self.refresh_template_list()
            return
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 '{template_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    QMessageBox.information(self, "成功", f"模板 '{template_name}' 已删除")
                    if self._current_template_name == template_name:
                        self._current_template_name = None
                        self.template_btn.setText("-- 选择模板 --")
                    self.refresh_template_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除模板失败: {e}")

    def _open_templates_folder(self):
        """在系统文件管理器中打开模板目录。"""
        folder = os.path.abspath(os.path.normpath(TEMPLATE_DIR))
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)

    def rename_prompt_template(self):
        """重命名当前选中的模板。"""
        name = (self._current_template_name or "").strip()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择要重命名的模板")
            return
        filepath, filename = self._find_template_file_by_name(name)
        if not filepath or not os.path.isfile(filepath):
            QMessageBox.warning(self, "提示", "未找到该模板文件")
            self.refresh_template_list()
            return
        new_name, ok = QInputDialog.getText(self, "重命名模板", "新名称:", text=name)
        if not ok or not new_name.strip() or new_name.strip() == name:
            return
        new_name = new_name.strip()
        new_safe = self._sanitize_template_filename(new_name)
        new_filepath = os.path.join(TEMPLATE_DIR, f"{new_safe}.json")
        if os.path.isfile(new_filepath):
            QMessageBox.warning(self, "提示", f"已存在名为「{new_name}」的模板，请换一个名称")
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["name"] = new_name
            data["updated_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(new_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.remove(filepath)
            self._current_template_name = new_name
            self.template_btn.setText(new_name)
            self.refresh_template_list()
            self.append_log(f"已重命名: {name} → {new_name}")
            QMessageBox.information(self, "成功", f"已重命名为「{new_name}」")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重命名失败: {e}")

    def duplicate_prompt_template(self):
        """将当前 Prompt 另存为新模板（不覆盖当前选中）。"""
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "提示", "Prompt 内容不能为空")
            return
        new_name, ok = QInputDialog.getText(self, "另存为", "新模板名称:")
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        safe_filename = self._sanitize_template_filename(new_name)
        filepath = os.path.join(TEMPLATE_DIR, f"{safe_filename}.json")
        if os.path.isfile(filepath):
            reply = QMessageBox.question(
                self, "确认覆盖",
                f"已存在同名模板「{new_name}」，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        template_data = {
            "name": new_name,
            "content": prompt_text,
            "delimiter": self.delim_edit.text(),
            "created_time": created_time,
            "updated_time": created_time,
        }
        try:
            os.makedirs(TEMPLATE_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            self.refresh_template_list()
            self.append_log(f"已另存为模板: {new_name}")
            QMessageBox.information(self, "成功", f"已另存为「{new_name}」")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"另存为失败: {e}")

    def append_log(self, text):
        if not hasattr(self, "log_console") or not self.log_console:
            return
        try:
            self.log_console.append(text)
            sb = self.log_console.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())
        except (AttributeError, RuntimeError):
            pass

    def get_client(self):
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key")
            return None

        model = self._get_current_model()
        if not model:
            QMessageBox.warning(self, "提示", "请输入模型名")
            return None

        profile = self._get_current_profile()
        base_url = profile["base_url"]

        # 初始化 client
        client = init_client(api_key, base_url=base_url, model=model)

        # 保存 API Key 与模型名，供下次自动恢复
        save_api_profile(
            profile_id=profile["id"],
            api_key=api_key,
            base_url=base_url,
            model=model,
            set_current=True,
        )
        return client

    def test_api(self):
        c = self.get_client()
        if not c:
            return
        if hasattr(self, "api_test_thread") and self.api_test_thread and self.api_test_thread.isRunning():
            self.api_test_thread.terminate()
            self.api_test_thread.wait(1000)
        if hasattr(self, "test_api_btn") and self.test_api_btn:
            self.test_api_btn.setEnabled(False)
            self.test_api_btn.setText("连接中...")
        self.append_log("正在测试 API 连接...")
        if hasattr(self, "api_test_thread") and self.api_test_thread:
            try:
                self.api_test_thread.finished.disconnect()
            except Exception:
                pass
        self.api_test_thread = ApiTestThread(c)
        self.api_test_thread.finished.connect(self.on_api_test_finished)
        self.api_test_thread.start()

    def on_api_test_finished(self, ok, msg):
        try:
            if hasattr(self, "test_api_btn") and self.test_api_btn:
                self.test_api_btn.setEnabled(True)
                self.test_api_btn.setText("测试连接")
            if ok:
                QMessageBox.information(self, "成功", msg)
                self.append_log(f"[成功] {msg}")
            else:
                QMessageBox.warning(self, "失败", msg)
                self.append_log(f"[失败] {msg}")
        except (AttributeError, RuntimeError):
            pass

    def clear_saved_api(self):
        """清除保存的 API Key"""
        profile = self._get_current_profile()
        reply = QMessageBox.question(
            self,
            "确认清除",
            f"确定要清除保存的 API Key 吗？\n清除后需要重新输入 API Key。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                clear_api_profile(profile["id"])
                self.api_key_edit.clear()
                self.append_log("已清除保存的 API Key")
                QMessageBox.information(self, "成功", "已清除保存的 API Key")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清除失败: {e}")
                self.append_log(f"清除 API Key 失败: {e}")

    def _on_max_workers_changed(self, value):
        """并发数改变时保存设置"""
        try:
            save_max_workers(value)
            self.append_log(f"并发线程数已设置为: {value}")
        except Exception as e:
            logging.warning(f"保存并发设置失败: {e}")

    def choose_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self.input_edit.setText(path)
            self.load_columns(path)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存路径", "output.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            self.output_edit.setText(path)

    def load_columns(self, path):
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "错误", "文件路径无效")
            return
        try:
            import pandas as pd
            # 先仅读表头行取列名（nrows=0 只读表头，避免 df.empty 误判）
            try:
                df = pd.read_excel(path, nrows=0, header=0)
            except Exception:
                df = pd.read_excel(path, nrows=1, header=0)
            cols = df.columns.tolist()
            # 若第一行全是 Unnamed 或空，尝试用第二行做表头
            if cols and all(
                str(c).startswith("Unnamed") or str(c).strip() == ""
                for c in cols
            ):
                try:
                    df = pd.read_excel(path, nrows=0, header=1)
                except Exception:
                    df = pd.read_excel(path, nrows=2, header=1)
                if not df.empty or len(df.columns) > 0:
                    cols = df.columns.tolist()
            if not cols:
                QMessageBox.warning(self, "警告", "文件中没有找到列")
                return
            cols = [str(c) for c in cols]
            # 直接填充列列表（不依赖 hasattr，确保一定会刷新）
            self.col_list.blockSignals(True)
            self.col_list.clear()
            for c in cols:
                item = QListWidgetItem(str(c))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.col_list.addItem(item)
            self.col_list.blockSignals(False)
            self.col_count_label.setText("已选 0 列")
            self.col_hint.setText("勾选需要参与合并并发送给 AI 的列")
            self.col_list.viewport().update()
            self.col_list.updateGeometry()
            self.col_list.repaint()
            QApplication.processEvents()
            self.append_log(f"已加载文件列: {len(cols)} 列")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取文件时发生错误: {e}")
            logging.error(f"加载列时出错: {e}", exc_info=True)

    def start_processing(self):
        if not self.get_client():
            return
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "提示", "已有任务正在运行，请先停止当前任务")
            return
        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        delimiter = self.delim_edit.text().strip()
        selected_cols = []
        for i in range(self.col_list.count()):
            item = self.col_list.item(i)
            if item and item.checkState() == Qt.Checked:
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
        if not prompt:
            QMessageBox.warning(self, "提示", "Prompt 模板不能为空")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        if hasattr(self, "log_console"):
            self.log_console.clear()
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(1)
        if hasattr(self, "worker") and self.worker:
            try:
                self.worker.progress.disconnect()
                self.worker.log_signal.disconnect()
                self.worker.finished.disconnect()
            except Exception:
                pass
        max_workers = self.max_workers_spin.value() if hasattr(self, "max_workers_spin") else 20
        self.worker = Worker(
            input_path, selected_cols, delimiter, output_path, prompt, max_workers
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def stop_processing(self):
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("正在停止...")
            self.append_log("正在请求停止任务...")
        elif hasattr(self, "stop_btn"):
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("停止")

    def on_progress(self, done, total, eta):
        if not hasattr(self, "progress_bar") or not self.progress_bar:
            return
        try:
            self.progress_bar.setMaximum(max(total, 1))
            self.progress_bar.setValue(min(done, total))
            if eta >= 0:
                m, s = divmod(int(eta), 60)
                h, m = divmod(m, 60)
                eta_str = f"{h:02d}:{m:02d}:{s:02d}"
                if hasattr(self, "eta_label") and self.eta_label:
                    self.eta_label.setText(f"剩余时间: {eta_str}")
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.setText(f"进度: {done}/{total}")
        except (AttributeError, RuntimeError):
            pass

    def on_worker_finished(self, ok, msg):
        try:
            if hasattr(self, "start_btn"):
                self.start_btn.setEnabled(True)
            if hasattr(self, "stop_btn"):
                self.stop_btn.setEnabled(False)
                self.stop_btn.setText("停止")
            if hasattr(self, "status_label"):
                self.status_label.setText("任务结束")
            if hasattr(self, "eta_label"):
                self.eta_label.setText("--:--")
            if ok:
                QMessageBox.information(self, "完成", msg)
                self.append_log(f"[完成] {msg}")
            else:
                if "用户中断" in msg:
                    QMessageBox.warning(self, "中断", msg)
                    self.append_log(f"[中断] {msg}")
                else:
                    QMessageBox.critical(self, "错误", msg)
                    self.append_log(f"[错误] {msg}")
        except (AttributeError, RuntimeError):
            pass
