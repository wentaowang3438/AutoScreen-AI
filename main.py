"""
Excel 智能批处理工具 - 程序入口
"""
import os
import sys

# 在导入 QApplication 之前设置 Qt 平台插件路径，避免中文路径下找不到 "windows" 插件
def _setup_qt_plugin_path():
    if getattr(sys, "frozen", False):
        # 打包后从 PyInstaller 解压目录（_MEIPASS）查找 Qt 平台插件
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        for sub in (
            "PyQt5/Qt5/plugins/platforms",
            "Qt5/plugins/platforms",
            "Qt/plugins/platforms",
            "plugins/platforms",
            "platforms",
        ):
            path = os.path.join(base, *sub.split("/"))
            if os.path.exists(path) and os.path.exists(os.path.join(path, "qwindows.dll")):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.normpath(path)
                return
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

from styles import get_stylesheet
from main_window import MainWindow


def main():
    # PyQt5 高 DPI 适配（Win10 兼容）
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass
    app = QApplication(sys.argv)
    # 按 DPI/缩放比例动态放大字号（4K 等高分屏）
    try:
        screen = app.primaryScreen()
        dpi = screen.logicalDpiX() if screen else 96
        scale = max(1.0, min(2.0, dpi / 96.0))
        app.setStyleSheet(get_stylesheet(scale))
    except Exception:
        app.setStyleSheet(get_stylesheet(1.0))
    window = MainWindow()
    window.show()
    return sys.exit(app.exec_())


if __name__ == "__main__":
    main()
