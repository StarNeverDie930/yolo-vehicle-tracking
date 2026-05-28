"""桌面应用启动入口。

负责创建 Qt 应用、加载全局样式表，并打开主窗口。业务处理逻辑放在
core/、analysis/ 和 app/ 内部，入口文件只保留最小启动流程。
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
    """初始化 QApplication 并进入 Qt 事件循环。"""
    app = QApplication(sys.argv)

    # 加载样式表
    style_path = os.path.join(os.path.dirname(__file__), "app", "resources", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
