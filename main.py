import sys
import os
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
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
