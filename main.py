"""
DeepSeek Excel 智能批处理工具 Pro - 程序入口
"""
import os
import sys

# 在导入 QApplication 之前设置 Qt 平台插件路径，避免中文路径下找不到 "windows" 插件
def _setup_qt_plugin_path():
    if getattr(sys, "frozen", False):
        return
    try:
        import PyQt5
        base = os.path.dirname(PyQt5.__file__)
        for sub in ("Qt5/plugins/platforms", "Qt/plugins/platforms", "plugins/platforms"):
            path = os.path.join(base, *sub.split("/"))
            if os.path.exists(path) and os.path.exists(os.path.join(path, "qwindows.dll")):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.normpath(path)
                break
    except Exception:
        pass

_setup_qt_plugin_path()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from styles import STYLESHEET
from main_window import MainWindow


def main():
    # PyQt5 高 DPI 适配（Win10 兼容）
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return sys.exit(app.exec_())


if __name__ == "__main__":
    main()
