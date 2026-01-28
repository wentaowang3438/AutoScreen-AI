"""
自定义控件：标题栏、日志处理器
"""
import logging

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
)


class QEditTextLogger(logging.Handler, QObject):
    """将 logging 输出重定向到 Qt 信号，便于在 QTextEdit 中显示。"""
    log_signal = Signal(str)

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
        self.setFixedHeight(40)
        self.window_parent = parent
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("DeepSeek Excel 智能批处理工具 Pro")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.title_label)
        layout.addStretch()

        # 窗口控制按钮容器，右对齐、统一尺寸与间距
        self.min_btn = QPushButton("\u2212")  # Unicode minus
        self.min_btn.setObjectName("TitleBtn")
        self.min_btn.setFixedSize(36, 36)
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setStyleSheet("font-size: 18px; font-weight: 600;")
        if self.window_parent:
            self.min_btn.clicked.connect(self.window_parent.showMinimized)
        self.min_btn.setToolTip("最小化")

        self.max_btn = QPushButton("\u25A1")  # □
        self.max_btn.setObjectName("TitleBtn")
        self.max_btn.setFixedSize(36, 36)
        self.max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.max_btn.setStyleSheet("font-size: 16px; font-weight: 600;")
        if self.window_parent:
            self.max_btn.clicked.connect(self.toggle_max_state)
        self.max_btn.setToolTip("最大化 / 还原")

        self.close_btn = QPushButton("\u00D7")  # ×
        self.close_btn.setObjectName("TitleBtn_Close")
        self.close_btn.setFixedSize(36, 36)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("font-size: 20px; font-weight: 600; line-height: 1;")
        if self.window_parent:
            self.close_btn.clicked.connect(self.window_parent.close)
        self.close_btn.setToolTip("关闭")

        layout.addSpacing(4)
        layout.addWidget(self.min_btn)
        layout.addSpacing(2)
        layout.addWidget(self.max_btn)
        layout.addSpacing(2)
        layout.addWidget(self.close_btn)

    def _get_global_pos(self, event):
        try:
            if hasattr(event, "globalPosition"):
                return event.globalPosition().toPoint()
            return event.globalPos()
        except AttributeError:
            return event.globalPos()

    def toggle_max_state(self):
        if not self.window_parent:
            return
        if self.window_parent.isMaximized():
            self.window_parent.showNormal()
            self.max_btn.setText("\u25A1")
        else:
            self.window_parent.showMaximized()
            self.max_btn.setText("\u25A0")  # ■ 表示“已最大化”

    def update_max_button(self):
        if not self.window_parent:
            return
        self.max_btn.setText("\u25A0" if self.window_parent.isMaximized() else "\u25A1")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_max_state()
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                click_pos = (
                    event.position().toPoint() if hasattr(event, "position") else event.pos()
                )
            except AttributeError:
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
            and event.buttons() & Qt.MouseButton.LeftButton
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
