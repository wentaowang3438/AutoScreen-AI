"""
自定义控件：标题栏、日志处理器
"""
import logging

from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
)


class QEditTextLogger(logging.Handler, QObject):
    """将 logging 输出重定向到 Qt 信号，便于在 QTextEdit 中显示。"""
    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)


class CustomTitleBar(QWidget):
    """无边框窗口的自定义标题栏，支持拖动、最小化/最大化/关闭。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self.window_parent = parent
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 6, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("DeepSeek Excel 智能批处理工具 Pro")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignVCenter)
        layout.addWidget(self.title_label, 0, Qt.AlignVCenter)
        layout.addStretch()

        # 最小化：水平短横线（极简线条）
        self.min_btn = QPushButton("\u2500")   # ─ (BOX DRAWINGS LIGHT HORIZONTAL)
        self.min_btn.setObjectName("TitleBtn")
        self.min_btn.setFixedSize(28, 28)
        self.min_btn.setCursor(Qt.PointingHandCursor)
        if self.window_parent:
            self.min_btn.clicked.connect(self.window_parent.showMinimized)
        self.min_btn.setToolTip("最小化")

        # 最大化/还原：单方框□ 与 重叠方框⧉ 切换
        self.max_btn = QPushButton("\u25A1")   # □ 未最大化时显示
        self.max_btn.setObjectName("TitleBtn")
        self.max_btn.setFixedSize(28, 28)
        self.max_btn.setCursor(Qt.PointingHandCursor)
        if self.window_parent:
            self.max_btn.clicked.connect(self.toggle_max_state)
        self.max_btn.setToolTip("最大化 / 还原")

        # 关闭：X 形线条
        self.close_btn = QPushButton("\u00D7")  # ×
        self.close_btn.setObjectName("TitleBtn_Close")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        if self.window_parent:
            self.close_btn.clicked.connect(self.window_parent.close)
        self.close_btn.setToolTip("关闭")

        layout.addSpacing(6)
        layout.addWidget(self.min_btn, 0, Qt.AlignVCenter)
        layout.addSpacing(4)
        layout.addWidget(self.max_btn, 0, Qt.AlignVCenter)
        layout.addSpacing(4)
        layout.addWidget(self.close_btn, 0, Qt.AlignVCenter)
        layout.addSpacing(2)

    def _get_global_pos(self, event):
        return event.globalPos()

    def toggle_max_state(self):
        if not self.window_parent:
            return
        if self.window_parent.isMaximized():
            self.window_parent.showNormal()
            self.max_btn.setText("\u25A1")   # □ 还原后显示“最大化”
        else:
            self.window_parent.showMaximized()
            self.max_btn.setText("\u29C9")   # ⧉ 重叠方框表示“还原”

    def update_max_button(self):
        if not self.window_parent:
            return
        self.max_btn.setText("\u29C9" if self.window_parent.isMaximized() else "\u25A1")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_max_state()
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_pos = event.pos()

            if (
                self.min_btn.geometry().contains(click_pos)
                or self.max_btn.geometry().contains(click_pos)
                or self.close_btn.geometry().contains(click_pos)
            ):
                event.ignore()
                return

            if self.window_parent and not self.window_parent.isMaximized():
                global_pos = self._get_global_pos(event)
                self._drag_pos = global_pos - self.window_parent.pos()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if (
            self._drag_pos
            and event.buttons() & Qt.LeftButton
            and self.window_parent
            and not self.window_parent.isMaximized()
        ):
            global_pos = self._get_global_pos(event)
            self.window_parent.move(global_pos - self._drag_pos)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
