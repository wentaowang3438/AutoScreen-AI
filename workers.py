"""
后台工作线程：批处理 Worker 与 API 测试线程
"""
import time

from PySide6.QtCore import QThread, Signal

from api import run_processing


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
            self.input_path,
            self.cols,
            self.delimiter,
            self.output_path,
            self.prompt,
            prog_cb,
            log_cb,
            self.is_stopped,
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
                temperature=0,
            )
            if resp:
                self.finished.emit(True, "API 连接成功！延迟正常。")
            else:
                self.finished.emit(False, "API 返回内容为空。")
        except Exception as e:
            self.finished.emit(False, f"API 连接异常: {str(e)}")
