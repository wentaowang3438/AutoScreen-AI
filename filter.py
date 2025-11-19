import sys
import os
import time
import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QGroupBox, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ======================================================
# =============       AI 处理逻辑函数       ============
# ======================================================

# 初始化 DeepSeek 客户端（只保留一次）
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def call_model(prompt: str, max_retries: int = 3) -> str:
    """
    调用 DeepSeek 模型，带简单重试机制。
    若最终失败，返回空字符串 ""。
    """
    backoff_base = 2  # 指数退避基数
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"模型调用失败（第 {attempt + 1} 次）：{e}")
            if attempt < max_retries - 1:
                # 简单指数退避
                sleep_sec = backoff_base ** attempt
                time.sleep(sleep_sec)
            else:
                # 最终失败
                return ""
    return ""


def process_row(row_index, merged_text, delimiter, prompt_template, cache_key):
    """
    单行处理逻辑。
    返回结构：
    {
        "index": 行号,
        "output": 模型输出或错误占位,
        "cache_key": 缓存键,
        "error": bool,
        "error_msg": str
    }
    """
    prompt = (
        prompt_template
        .replace("{merged_text}", merged_text)
        .replace("{delimiter}", delimiter)
    )

    result = call_model(prompt)

    error = False
    error_msg = ""

    if not result:
        error = True
        error_msg = "API 调用失败或返回空内容"
        result = f"生成失败{delimiter}生成失败"
    elif delimiter not in result:
        error = True
        error_msg = "结果中缺少分隔符"
        result = f"生成失败{delimiter}生成失败"

    return {
        "index": row_index,
        "output": result,
        "cache_key": cache_key,
        "error": error,
        "error_msg": error_msg,
    }


def run_processing(input_path, cols, delimiter, output_path, prompt, progress_cb, stop_flag):
    """
    主处理函数：
    - 读取 Excel
    - 多线程调用 AI
    - 写回结果
    - 支持中断
    - 支持缓存
    - 记录错误行
    """
    df = pd.read_excel(input_path)
    df["AI_Output"] = ""
    total = len(df)

    cache = {}          # key -> {"output", "error", "error_msg"}
    results = []        # 每行结果
    error_rows = []     # 记录错误信息

    # 用于进度计算
    done_cnt = 0

    with ThreadPoolExecutor(max_workers=20) as pool:
        tasks = []

        # 先提交任务（同时利用缓存）
        for idx, row in df.iterrows():
            if stop_flag():
                break

            merged_text = "\n".join(str(row[c]) for c in cols if c in df.columns)
            key = f"{merged_text}|{delimiter}|{prompt}"

            # 缓存命中，直接使用
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
                if r["error"]:
                    error_rows.append(f"行 {idx}：{r['error_msg']}（缓存）")
                done_cnt += 1
                progress_cb(done_cnt, total)
            else:
                # 未命中，提交到线程池
                future = pool.submit(
                    process_row,
                    idx,
                    merged_text,
                    delimiter,
                    prompt,
                    key
                )
                tasks.append(future)

        # 处理线程池返回结果
        for future in as_completed(tasks):
            if stop_flag():
                # 用户中断，停止收集更多结果（但线程池会自然跑完）
                break

            r = future.result()
            results.append(r)

            # 写入缓存（不包含 index）
            cache[r["cache_key"]] = {
                "output": r["output"],
                "error": r["error"],
                "error_msg": r["error_msg"],
            }

            if r["error"]:
                error_rows.append(f"行 {r['index']}：{r['error_msg']}")

            done_cnt += 1
            progress_cb(done_cnt, total)

    # 写回已完成结果（包括缓存和实际调用的）
    for r in results:
        df.at[r["index"], "AI_Output"] = r["output"]

    # 保存主结果
    df.to_excel(output_path, index=False)

    # 保存错误日志
    if error_rows:
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(error_rows))

    processed_count = len(results)

    if stop_flag():
        return False, f"用户中断任务，已处理 {processed_count}/{total} 行（错误 {len(error_rows)} 行，详情见 error_log.txt）"
    else:
        if error_rows:
            return True, f"处理完成：{total} 行，其中错误 {len(error_rows)} 行（详情见 error_log.txt）"
        else:
            return True, f"处理完成：{total} 行，全部成功"


# ======================================================
# =================     后台线程类      ================
# ======================================================

class Worker(QThread):
    # 进度信号：已完成、总数、预计剩余秒数
    progress = Signal(int, int, float)
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

        def cb(done, total):
            # 在回调里计算预计剩余时间
            elapsed = time.time() - self._start_time if self._start_time else 0
            if done > 0 and elapsed > 0:
                rate = elapsed / done  # 秒 / 条
                remaining = max(total - done, 0)
                eta = remaining * rate
            else:
                eta = -1.0  # 不可用

            self.progress.emit(done, total, eta)

        ok, msg = run_processing(
            self.input_path,
            self.cols,
            self.delimiter,
            self.output_path,
            self.prompt,
            cb,
            stop_flag=self.is_stopped
        )
        self.finished.emit(ok, msg)


class ApiTestThread(QThread):
    finished = Signal(bool, str)

    def run(self):
        test_prompt = "这是一个测试请求，请简单回复“OK”。"
        try:
            resp = call_model(test_prompt, max_retries=2)
            if resp:
                self.finished.emit(True, "API 测试成功，可正常调用。")
            else:
                self.finished.emit(False, "API 调用失败或返回空内容，请检查网络或密钥。")
        except Exception as e:
            self.finished.emit(False, f"API 测试异常：{e}")


# ======================================================
# =================       主 GUI 界面      ==============
# ======================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DeepSeek 批处理工具 - 自动读取列版")
        self.setGeometry(100, 100, 950, 750)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.setCentralWidget(widget)

        self.col_checkboxes = []
        self.worker = None
        self.api_test_thread = None

        # ========== 文件设置 ==========
        file_box = QGroupBox("📁 文件设置 / API 测试")
        file_layout = QGridLayout()
        file_box.setLayout(file_layout)

        file_layout.addWidget(QLabel("输入 Excel 文件："), 0, 0)
        self.input_edit = QLineEdit()
        file_layout.addWidget(self.input_edit, 0, 1)
        btn = QPushButton("浏览")
        btn.clicked.connect(self.choose_input)
        file_layout.addWidget(btn, 0, 2)

        file_layout.addWidget(QLabel("输出 Excel 文件："), 1, 0)
        self.output_edit = QLineEdit("output.xlsx")
        file_layout.addWidget(self.output_edit, 1, 1)
        btn2 = QPushButton("浏览")
        btn2.clicked.connect(self.choose_output)
        file_layout.addWidget(btn2, 1, 2)

        # API 测试按钮
        self.test_api_btn = QPushButton("🔍 测试 API")
        self.test_api_btn.clicked.connect(self.test_api)
        file_layout.addWidget(self.test_api_btn, 2, 0, 1, 3)

        layout.addWidget(file_box)

        # ========== 自动列名区域 ==========
        col_box = QGroupBox("📋 自动检测到的列（可多选）")
        col_vlayout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self.col_container = QVBoxLayout(inner)
        scroll.setWidget(inner)

        col_vlayout.addWidget(scroll)
        col_box.setLayout(col_vlayout)
        layout.addWidget(col_box)

        # ========== 分隔符 ==========
        delim_box = QGroupBox("⚙️ 输出分隔符")
        delim_layout = QHBoxLayout()
        delim_box.setLayout(delim_layout)

        delim_layout.addWidget(QLabel("分隔符："))
        self.delim_edit = QLineEdit("|")
        self.delim_edit.setFixedWidth(120)
        delim_layout.addWidget(self.delim_edit)

        layout.addWidget(delim_box)

        # ========== Prompt ==========
        prompt_box = QGroupBox("📝 Prompt 模板")
        prompt_layout = QVBoxLayout()

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(
            "你是一名专业领域的文献筛选专家。\n\n"
            "【任务目标】\n"
            "根据提供的文章内容，判断其是否属于【研究类型名称】类文献，并给出是否保留与匹配评分。\n\n"
            "【判定标准】\n"
            "1. 若文章具备以下任意特征，可判断为【研究类型名称】：\n"
            "   - 【特征1】\n"
            "   - 【特征2】\n"
            "   - 【特征3】\n"
            "   - （可自行添加更多特征）\n"
            "2. 若文章具备以下任意情况，则不属于【研究类型名称】：\n"
            "   - 【排除条件1】\n"
            "   - 【排除条件2】\n"
            "   - 【排除条件3】\n"
            "   - （可自行添加更多排除条件）\n\n"
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
            "- 输出任何换行\n"
            "- 输出任何解释说明、理由、总结\n"
            "- 输出任何额外符号、标点、序号\n"
            "- 输出除三个字段外的任何文字\n"
            "- 输出前后空格或换行\n\n"
            "【文章内容】\n"
            "{merged_text}"
        )
        prompt_layout.addWidget(self.prompt_edit)
        prompt_box.setLayout(prompt_layout)
        layout.addWidget(prompt_box)

        # ========== 控制区域 ==========
        control = QHBoxLayout()

        self.progress = QProgressBar()
        control.addWidget(self.progress)

        self.status_label = QLabel("就绪")
        control.addWidget(self.status_label)

        self.start_btn = QPushButton("🚀 开始处理")
        self.start_btn.clicked.connect(self.start)
        control.addWidget(self.start_btn)

        self.stop_btn = QPushButton("🛑 停止")
        self.stop_btn.clicked.connect(self.stop_task)
        self.stop_btn.setEnabled(False)
        control.addWidget(self.stop_btn)

        layout.addLayout(control)

    # ==================================================
    # ================== 事件函数 =======================
    # ==================================================

    def choose_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Excel 文件", "", "Excel (*.xlsx)")
        if not path:
            return

        self.input_edit.setText(path)
        self.load_columns(path)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "输出 Excel 文件", "output.xlsx", "Excel (*.xlsx)")
        if path:
            self.output_edit.setText(path)

    def load_columns(self, excel_path):
        """自动加载列名"""
        try:
            df = pd.read_excel(excel_path)
            columns = list(df.columns)

            for cb in self.col_checkboxes:
                cb.setParent(None)
            self.col_checkboxes.clear()

            for col in columns:
                cb = QCheckBox(col)
                self.col_container.addWidget(cb)
                self.col_checkboxes.append(cb)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载列失败：{e}")

    def start(self):
        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()
        delimiter = self.delim_edit.text().strip()
        prompt = self.prompt_edit.toPlainText()

        if not os.path.exists(input_path):
            QMessageBox.critical(self, "错误", "输入文件不存在！")
            return

        if not delimiter:
            QMessageBox.warning(self, "警告", "分隔符不能为空！")
            return

        selected_cols = [cb.text() for cb in self.col_checkboxes if cb.isChecked()]
        if not selected_cols:
            QMessageBox.warning(self, "警告", "请至少选择一个列！")
            return

        self.worker = Worker(input_path, selected_cols, delimiter, output_path, prompt)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("处理中...")

    def stop_task(self):
        if self.worker is not None:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("正在请求停止...")

    def format_eta(self, eta_seconds: float) -> str:
        if eta_seconds < 0:
            return "预计剩余时间：计算中..."
        eta_seconds = int(eta_seconds)
        h = eta_seconds // 3600
        m = (eta_seconds % 3600) // 60
        s = eta_seconds % 60
        if h > 0:
            return f"预计剩余时间：{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"预计剩余时间：{m:02d}:{s:02d}"

    def on_progress(self, done, total, eta):
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        eta_text = self.format_eta(eta)
        self.status_label.setText(f"{done}/{total} | {eta_text}")

    def on_finished(self, ok, msg):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.information(self, "完成", msg)
        self.status_label.setText("完成" if ok else "已终止")

    def test_api(self):
        """测试 DeepSeek API 是否可用"""
        self.test_api_btn.setEnabled(False)
        self.status_label.setText("正在测试 API...")

        self.api_test_thread = ApiTestThread()
        self.api_test_thread.finished.connect(self.on_api_test_finished)
        self.api_test_thread.start()

    def on_api_test_finished(self, ok: bool, msg: str):
        self.test_api_btn.setEnabled(True)
        QMessageBox.information(self, "API 测试结果", msg)
        self.status_label.setText("就绪" if ok else "API 测试失败，请检查配置")


# ======================================================
# ======================  程序入口 ======================
# ======================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
