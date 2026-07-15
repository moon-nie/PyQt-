"""Gridloom — PyQt6 표 엔진 (기본 실행).

Windows: python gridloom.pyw
Mac:     python3 gridloom.pyw
"""

import sys

# Qt WebEngine은 QApplication 인스턴스 생성 전에 import 해야 합니다.
# (미설치여도 앱 자체는 실행 가능하도록 예외를 삼킵니다.)
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication

from df_tool.qt_app import MainWindow


def main() -> None:
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
