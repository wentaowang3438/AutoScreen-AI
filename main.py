"""
DeepSeek Excel 智能批处理工具 Pro - 程序入口
"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from styles import STYLESHEET
from main_window import MainWindow


def main():
    # 高 DPI 适配（Qt6，在创建 app 前设置）
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return sys.exit(app.exec())


if __name__ == "__main__":
    main()
