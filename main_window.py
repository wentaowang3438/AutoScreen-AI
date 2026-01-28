"""
主窗口：界面布局、事件与业务逻辑入口
- 使用 QSplitter + QScrollArea 提升适配性与小窗口体验
- API Key 显隐、列全选/取消全选、快捷键与状态提示
"""
import os
import json
import time
import logging

from PySide6.QtWidgets import (
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
    QGraphicsDropShadowEffect,
    QSizeGrip,
    QComboBox,
    QInputDialog,
    QScrollArea,
    QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QShortcut, QKeySequence

from config import (
    TEMPLATE_DIR,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    load_api_profile,
    load_current_profile_id,
    save_api_profile,
)
from api import init_client
from widgets import CustomTitleBar, QEditTextLogger
from workers import Worker, ApiTestThread

# 布局常量，便于统一调整
LEFT_PANEL_WIDTH = 320
LEFT_PANEL_MIN = 260
LEFT_PANEL_MAX = 460

# 支持的 API 平台 / 模型配置
API_PROFILES = [
    {
        "id": "deepseek-chat",
        "label": "DeepSeek 官方 (deepseek-chat)",
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
    },
    {
        "id": "siliconflow-glm-4.7",
        "label": "SiliconFlow · GLM-4.7",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Pro/zai-org/GLM-4.7",
    },
    {
        "id": "siliconflow-deepseek-r1-qwen-7b",
        "label": "SiliconFlow · DeepSeek-R1-Distill-Qwen-7B",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    },
]

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
        self.resize(1100, 750)
        self.setMinimumSize(720, 520)

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

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.main_frame.setGraphicsEffect(shadow)

        self.log_handler.log_signal.connect(self.append_log)

        # === 从本地配置恢复当前 profile 与对应的 API Key ===
        if hasattr(self, "api_profile_combo"):
            # 1) 先确定当前 profile id
            current_id = load_current_profile_id(API_PROFILES[0]["id"])
            current_index = 0
            for i, profile in enumerate(API_PROFILES):
                if profile["id"] == current_id:
                    current_index = i
                    break
            self.api_profile_combo.setCurrentIndex(current_index)

            # 2) 读取该 profile 的配置并填充 API Key
            profile = API_PROFILES[current_index]
            cfg = load_api_profile(
                profile_id=profile["id"],
                default_base_url=profile["base_url"],
                default_model=profile["model"],
            )
            key = cfg.get("api_key") or ""
            if key:
                self.api_key_edit.setText(key)
                self.append_log(f"已为 {profile['label']} 自动加载保存的 API Key")

        if hasattr(self, "status_icon"):
            self.update_status_icon("ready")

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.update_max_button()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "size_grip") and self.size_grip:
            try:
                size = self.size_grip.sizeHint()
                self.size_grip.move(
                    self.width() - size.width(), self.height() - size.height()
                )
                self.size_grip.raise_()
            except (AttributeError, RuntimeError):
                pass

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
        main_layout.setContentsMargins(16, 8, 16, 16)
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
        left_content_layout.setContentsMargins(4, 0, 8, 8)
        left_content_layout.setSpacing(12)

        # 1) API 配置
        api_box = QGroupBox("🔑 API 配置")
        api_layout = QVBoxLayout()
        api_layout.setSpacing(6)

        # 平台与模型选择
        api_layout.addWidget(QLabel("平台与模型"))
        self.api_profile_combo = QComboBox()
        self.api_profile_combo.setMinimumWidth(220)
        self.api_profile_combo.setToolTip("选择调用的平台与模型，例如 DeepSeek 或 SiliconFlow")
        for profile in API_PROFILES:
            # itemData 存 profile_id，具体 base_url 和 model 从 API_PROFILES 中查
            self.api_profile_combo.addItem(profile["label"], profile["id"])
        api_layout.addWidget(self.api_profile_combo)

        # API Key
        api_layout.addWidget(QLabel("API Key"))
        api_key_row = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-...（必填）")
        self.api_key_edit.setToolTip(
            "平台提供的 API Key，例如 DeepSeek 或 SiliconFlow 控制台生成的密钥"
        )
        self.api_key_edit.setMinimumHeight(28)
        self._api_key_visible = False
        self.api_key_toggle_btn = QPushButton("显示")
        self.api_key_toggle_btn.setObjectName("SmallBtn")
        self.api_key_toggle_btn.setFixedWidth(44)
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

        api_box.setLayout(api_layout)
        left_content_layout.addWidget(api_box)

        # 2) 数据源
        file_box = QGroupBox("📂 数据源")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(6)
        file_layout.addWidget(QLabel("输入 Excel"))
        h1 = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        self.input_edit.setPlaceholderText("未选择")
        self.input_edit.setToolTip("支持 .xlsx / .xls")
        self.input_edit.setMinimumHeight(28)
        btn_in = QPushButton("…")
        btn_in.setObjectName("SmallBtn")
        btn_in.setFixedWidth(36)
        btn_in.setToolTip("选择文件 (Ctrl+O)")
        btn_in.clicked.connect(self.choose_input)
        h1.addWidget(self.input_edit)
        h1.addWidget(btn_in)
        file_layout.addLayout(h1)
        file_layout.addWidget(QLabel("输出路径"))
        h2 = QHBoxLayout()
        self.output_edit = QLineEdit("output.xlsx")
        self.output_edit.setToolTip("结果将写入该文件，并增加 AI_Output 列")
        self.output_edit.setMinimumHeight(28)
        btn_out = QPushButton("…")
        btn_out.setObjectName("SmallBtn")
        btn_out.setFixedWidth(36)
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
        self.col_list.setMinimumHeight(80)
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
        p_layout.setSpacing(10)
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
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(150)
        self.template_combo.setToolTip("选择已保存的 Prompt 模板")
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        self._template_loading = False
        template_header.addWidget(self.template_combo)
        self.save_template_btn = QPushButton("💾 保存模板")
        self.save_template_btn.setObjectName("PrimaryBtn")
        self.save_template_btn.setToolTip("将当前 Prompt 保存为模板")
        self.save_template_btn.clicked.connect(self.save_prompt_template)
        template_header.addWidget(self.save_template_btn)
        self.delete_template_btn = QPushButton("🗑 删除")
        self.delete_template_btn.setObjectName("DangerBtn")
        self.delete_template_btn.setToolTip("删除选中的模板")
        self.delete_template_btn.clicked.connect(self.delete_prompt_template)
        template_header.addStretch()
        p_layout.addLayout(template_header)
        self.refresh_template_list()

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("在此输入你的 Prompt...")
        self.prompt_edit.setToolTip(
            "输入 AI Prompt 模板\n使用 {merged_text} 占位符表示合并后的列内容\n使用 {delimiter} 占位符表示输出分隔符"
        )
        self.prompt_edit.setMinimumHeight(140)
        self.prompt_edit.setPlainText(DEFAULT_PROMPT)
        p_layout.addWidget(self.prompt_edit)

        log_tab = QWidget()
        l_layout = QVBoxLayout(log_tab)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(120)
        self.log_console.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        l_layout.addWidget(self.log_console)

        self.tabs.addTab(prompt_tab, "📝 Prompt")
        self.tabs.addTab(log_tab, "📟 日志")
        self.tabs.setMinimumHeight(200)
        right_layout.addWidget(self.tabs)

        control_frame = QFrame()
        control_frame.setObjectName("ControlFrame")
        control_frame.setStyleSheet(
            "QFrame#ControlFrame { background-color: #f8fafc; border-radius: 8px; padding: 12px 14px; border: 1px solid #e2e8f0; }"
        )
        c_layout = QVBoxLayout(control_frame)
        c_layout.setSpacing(10)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.status_icon = QLabel("\u2713")  # ✓
        self.status_icon.setObjectName("StatusIcon")
        self.status_icon.setFixedSize(28, 28)
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #16a34a;"
            " background-color: #dcfce7; border-radius: 14px;"
        )
        self.status_icon.setToolTip("状态指示")
        info_layout.addWidget(self.status_icon)
        self.status_label = QLabel("准备就绪 \u00B7 请先配置 API、选择文件与列")
        self.status_label.setStyleSheet("font-weight: bold; color: #64748b; font-size: 13px;")
        self.status_label.setToolTip("当前状态与下一步提示")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        self.eta_label = QLabel("\u2014\u2014:\u2014\u2014")  # --:--
        self.eta_label.setStyleSheet("font-family: Consolas, monospace; font-size: 13px; color: #64748b; min-width: 72px;")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.eta_label.setToolTip("预计剩余时间")
        info_layout.addWidget(self.eta_label)
        c_layout.addLayout(info_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setToolTip("显示处理进度")
        c_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.start_btn = QPushButton("\u25B6 开始批量处理")
        self.start_btn.setObjectName("SuccessBtn")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setToolTip("开始处理 (F5)")
        self.start_btn.clicked.connect(self.start_processing)
        self.stop_btn = QPushButton("\u25A0 停止")
        self.stop_btn.setObjectName("DangerBtn")
        self.stop_btn.setFixedHeight(44)
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

        self.size_grip = QSizeGrip(self.main_frame)
        self.size_grip.setObjectName("SizeGrip")

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

    def refresh_template_list(self):
        if not hasattr(self, "template_combo") or not self.template_combo:
            return
        self._template_loading = True
        try:
            self.template_combo.clear()
            self.template_combo.addItem("-- 选择模板 --")
            if not os.path.exists(TEMPLATE_DIR):
                return
            templates = []
            for filename in os.listdir(TEMPLATE_DIR):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(TEMPLATE_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        templates.append((data.get("name", filename[:-5]), filename))
                except (json.JSONDecodeError, OSError) as e:
                    logging.warning(f"无法加载模板 {filename}: {e}")
            templates.sort(key=lambda x: x[0])
            for name, filename in templates:
                self.template_combo.addItem(name, filename)
        finally:
            self._template_loading = False

    def save_prompt_template(self):
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "提示", "Prompt内容不能为空")
            return
        name, ok = QInputDialog.getText(self, "保存模板", "请输入模板名称:")
        if not ok or not name.strip():
            return
        name = name.strip()
        template_data = {
            "name": name,
            "content": prompt_text,
            "delimiter": self.delim_edit.text(),
            "created_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        filepath = os.path.join(TEMPLATE_DIR, f"{name}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", f"模板 '{name}' 已保存")
            self.refresh_template_list()
            idx = self.template_combo.findText(name)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模板失败: {e}")

    def on_template_selected(self, index):
        if self._template_loading or index < 1:
            return
        self.load_prompt_template()

    def load_prompt_template(self):
        index = self.template_combo.currentIndex()
        if index < 1:
            return
        template_name = self.template_combo.currentText()
        filename = self.template_combo.itemData(index)
        if not filename:
            return
        filepath = os.path.join(TEMPLATE_DIR, filename)
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "错误", "模板文件不存在")
            self.refresh_template_list()
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.prompt_edit.setPlainText(data.get("content", ""))
            if "delimiter" in data:
                self.delim_edit.setText(data["delimiter"])
            self.append_log(f"已加载模板: {template_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板失败: {e}")

    def delete_prompt_template(self):
        index = self.template_combo.currentIndex()
        if index < 1:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        template_name = self.template_combo.currentText()
        filename = self.template_combo.itemData(index)
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 '{template_name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            filepath = os.path.join(TEMPLATE_DIR, filename)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    QMessageBox.information(self, "成功", f"模板 '{template_name}' 已删除")
                    self.refresh_template_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除模板失败: {e}")

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

    # ===== API Profile & Client =====

    def _get_current_profile(self) -> dict:
        """
        根据下拉框当前选择，返回对应的 profile dict。
        """
        if not hasattr(self, "api_profile_combo"):
            return API_PROFILES[0]
        idx = self.api_profile_combo.currentIndex()
        if idx < 0 or idx >= len(API_PROFILES):
            return API_PROFILES[0]
        return API_PROFILES[idx]

    def get_client(self):
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key")
            return None

        profile = self._get_current_profile()
        base_url = profile["base_url"]
        model = profile["model"]

        # 初始化 client
        client = init_client(api_key, base_url=base_url, model=model)

        # 将该 profile 的配置（尤其是 key）单独保存，供下次自动恢复
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
            df = pd.read_excel(path, nrows=5)
            if df.empty:
                QMessageBox.warning(self, "警告", "文件为空或无法读取")
                return
            cols = df.columns.tolist()
            if not cols:
                QMessageBox.warning(self, "警告", "文件中没有找到列")
                return
            if hasattr(self, "col_list") and self.col_list:
                self.col_list.blockSignals(True)
                self.col_list.clear()
                for c in cols:
                    item = QListWidgetItem(str(c))
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    self.col_list.addItem(item)
                self.col_list.blockSignals(False)
                if hasattr(self, "col_count_label"):
                    self.col_count_label.setText("已选 0 列")
                if hasattr(self, "col_hint"):
                    self.col_hint.setText("勾选需要参与合并并发送给 AI 的列")
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
        self.worker = Worker(
            input_path, selected_cols, delimiter, output_path, prompt
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
            self.stop_btn.setText("\u25A0 停止")

    def update_status_icon(self, status):
        if not hasattr(self, "status_icon"):
            return
        config = {
            "ready": ("\u2713", "#16a34a", "#dcfce7"),      # ✓ 绿字 浅绿底
            "processing": ("\u23F3", "#0284c7", "#e0f2fe"),  # ⏳ 蓝字 浅蓝底
            "success": ("\u2713", "#16a34a", "#dcfce7"),     # ✓ 绿字 浅绿底
            "error": ("\u2717", "#dc2626", "#fee2e2"),       # ✗ 红字 浅红底
        }
        icon, color, bg = config.get(status, ("\u2713", "#64748b", "#f1f5f9"))
        self.status_icon.setText(icon)
        self.status_icon.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {color};"
            f" background-color: {bg}; border-radius: 14px;"
        )

    def on_progress(self, done, total, eta):
        if not hasattr(self, "progress_bar") or not self.progress_bar:
            return
        try:
            self.progress_bar.setMaximum(max(total, 1))
            self.progress_bar.setValue(min(done, total))
            self.update_status_icon("processing")
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
                self.stop_btn.setText("\u25A0 停止")
            if hasattr(self, "status_label"):
                self.status_label.setText("任务结束")
            if hasattr(self, "eta_label"):
                self.eta_label.setText("--:--")
            if ok:
                self.update_status_icon("success")
                QMessageBox.information(self, "完成", msg)
                self.append_log(f"✅ {msg}")
            else:
                if "用户中断" in msg:
                    self.update_status_icon("ready")
                    QMessageBox.warning(self, "中断", msg)
                    self.append_log(f"⚠️ {msg}")
                else:
                    self.update_status_icon("error")
                    QMessageBox.critical(self, "错误", msg)
                    self.append_log(f"❌ {msg}")
        except (AttributeError, RuntimeError):
            pass
