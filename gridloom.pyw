"""Gridloom — PyQt6 표 엔진 (기본 실행).

Windows: python gridloom.pyw
Mac:     python3 gridloom.pyw
"""

import sys

from PyQt6.QtWidgets import QApplication

from df_tool.qt_app import MainWindow


def main() -> None:
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
