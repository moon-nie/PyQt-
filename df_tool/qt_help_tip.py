"""분석 등 UI용 느낌표(!) 도움말 배지."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QToolTip, QWidget

from df_tool.analysis_help import tip_text
from df_tool.theme import COLORS


class HelpTipBadge(QToolButton):
    """마우스 올리면 용어 설명이 뜨는 작은 '!' 배지.

    전역 QWidget 스타일시트 때문에 기본 setToolTip 이 안 보이는 경우가 있어
    enter 시 ``QToolTip.showText``로 직접 띄웁니다. 클릭해도 같은 설명을 보여 줍니다.
    """

    def __init__(self, parent: QWidget | None = None, *, key: str = "") -> None:
        super().__init__(parent)
        self._key = ""
        self._tip = ""
        self.setObjectName("helpTipBadge")
        self.setText("!")
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(20, 20)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        self.setStyleSheet(
            f"""
            QToolButton#helpTipBadge {{
                background: {COLORS['surface_alt']};
                color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }}
            QToolButton#helpTipBadge:hover {{
                background: {COLORS['primary_soft']};
                color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
            """
        )
        self.clicked.connect(self._show_tip_now)
        if key:
            self.set_key(key)

    def set_key(self, key: str) -> None:
        self._key = key
        self._tip = tip_text(key)
        # 기본 경로 + showText 백업
        self.setToolTip(self._tip)
        self.setWhatsThis("")

    def _tip_pos(self) -> QPoint:
        return self.mapToGlobal(QPoint(0, self.height() + 4))

    def _show_tip_now(self) -> None:
        if not self._tip:
            return
        QToolTip.showText(self._tip_pos(), self._tip, self, self.rect(), 15000)

    def enterEvent(self, event: QEnterEvent) -> None:
        super().enterEvent(event)
        # 짧은 지연 후 표시 (실수로 지나갈 때 깜빡임 감소)
        QTimer.singleShot(80, self._show_if_still_hovered)

    def _show_if_still_hovered(self) -> None:
        if self.underMouse() and self._tip:
            QToolTip.showText(self._tip_pos(), self._tip, self, self.rect(), 15000)

    def leaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().leaveEvent(event)


def help_tip_badge(parent: QWidget | None, key: str) -> HelpTipBadge:
    return HelpTipBadge(parent, key=key)


def add_label_with_help(layout: QHBoxLayout, text: str, key: str) -> HelpTipBadge:
    """가로 레이아웃에 라벨과 ! 배지를 연속 추가하고 배지를 반환."""
    layout.addWidget(QLabel(text))
    badge = help_tip_badge(None, key)
    layout.addWidget(badge)
    return badge
