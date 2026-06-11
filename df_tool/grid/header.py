"""QHeaderView — 우클릭 메뉴 + 열 드래그 재정렬."""
from __future__ import annotations

import time

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent, QMouseEvent
from PyQt6.QtWidgets import QHeaderView


class GridHeaderView(QHeaderView):
    """행/열 헤더 공통 — 우클릭 메뉴."""

    header_context_menu = pyqtSignal(QPoint)

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _emit_context_menu(self, pos: QPoint) -> None:
        self.header_context_menu.emit(pos)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        self._emit_context_menu(event.pos())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self._emit_context_menu(event.pos())
            event.accept()
            return
        super().mousePressEvent(event)


class GridHorizontalHeader(GridHeaderView):
    """열 헤더 — 클릭 선택 / 경계 리사이즈 / 드래그 재정렬."""

    CLICK_SLOP = 8
    DRAG_THRESHOLD = 14
    RESIZE_ZONE = 6

    column_reorder = pyqtSignal(int, int)
    column_header_clicked = pyqtSignal(int, object)  # logical, Qt.KeyboardModifiers
    drop_indicator_changed = pyqtSignal(object)  # int | None

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsMovable(False)
        self._press_logical: int | None = None
        self._press_x = 0
        self._press_modifiers = Qt.KeyboardModifier.NoModifier
        self._resize_active = False
        self._dragging = False
        self._drop_x: int | None = None
        self._last_click_logical: int | None = None
        self._last_click_at = 0.0

    def _logical_at(self, x: int) -> int:
        point = QPoint(max(0, x), max(0, self.height() // 2))
        logical = self.logicalIndexAt(point)
        if logical >= 0:
            return logical
        logical = self.sectionAt(x)
        return logical if logical >= 0 else -1

    def _is_resize_edge(self, x: int) -> bool:
        """열 오른쪽 경계만 리사이즈 구역 (왼쪽 중복 판정 제거)."""
        zone = self.RESIZE_ZONE
        for visual in range(self.count()):
            right = self.sectionPosition(visual) + self.sectionSize(visual)
            if abs(x - right) <= zone:
                return True
        return False

    def _drop_x_for_logical(self, logical: int) -> int | None:
        if logical < 0:
            return None
        visual = self.visualIndex(logical)
        if visual < 0:
            return None
        return self.sectionPosition(visual)

    def _update_drop_target(self, x: int, source_logical: int | None) -> None:
        logical = self._logical_at(x)
        drop_x = self._drop_x_for_logical(logical)
        if source_logical is not None and logical == source_logical:
            drop_x = None
        if drop_x != self._drop_x:
            self._drop_x = drop_x
            self.drop_indicator_changed.emit(drop_x)

    def _reset_pointer_state(self) -> None:
        self._press_logical = None
        self._resize_active = False
        self._dragging = False
        self._drop_x = None
        self.unsetCursor()
        self.drop_indicator_changed.emit(None)

    def _emit_column_click(self, logical: int, modifiers) -> None:
        if logical < 0:
            return
        now = time.monotonic()
        if (
            self._last_click_logical == logical
            and now - self._last_click_at < 0.45
        ):
            self._last_click_logical = None
            self._last_click_at = 0.0
            self.sectionDoubleClicked.emit(logical)
            return
        self._last_click_logical = logical
        self._last_click_at = now
        self.column_header_clicked.emit(logical, modifiers)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self._emit_context_menu(event.pos())
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        x = event.pos().x()
        self._press_x = x
        self._press_modifiers = event.modifiers()
        self._press_logical = self._logical_at(x)
        self._dragging = False

        ctrl = bool(self._press_modifiers & Qt.KeyboardModifier.ControlModifier)
        if self._is_resize_edge(x) and not ctrl:
            self._resize_active = True
            super().mousePressEvent(event)
            return

        self._resize_active = False
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._resize_active:
            super().mouseMoveEvent(event)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._press_logical is None:
            super().mouseMoveEvent(event)
            return

        moved = abs(event.pos().x() - self._press_x)
        if moved < self.DRAG_THRESHOLD:
            super().mouseMoveEvent(event)
            return

        if not self._dragging:
            self._dragging = True
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._update_drop_target(event.pos().x(), self._press_logical)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        moved = abs(event.pos().x() - self._press_x)
        press_logical = self._press_logical
        release_logical = self._logical_at(event.pos().x())

        if self._resize_active:
            if moved <= self.CLICK_SLOP and press_logical is not None and press_logical >= 0:
                self._emit_column_click(press_logical, self._press_modifiers)
            else:
                super().mouseReleaseEvent(event)
            self._reset_pointer_state()
            event.accept()
            return

        if (
            moved <= self.CLICK_SLOP
            and press_logical is not None
            and press_logical >= 0
        ):
            self._emit_column_click(press_logical, self._press_modifiers)
            self._reset_pointer_state()
            event.accept()
            return

        if (
            self._dragging
            and press_logical is not None
            and release_logical is not None
            and press_logical >= 0
            and release_logical >= 0
            and press_logical != release_logical
        ):
            self.column_reorder.emit(press_logical, release_logical)

        self._reset_pointer_state()
        event.accept()


class GridVerticalHeader(GridHeaderView):
    """행 번호 헤더 — 클릭 선택 (Ctrl·Shift 다중 선택)."""

    CLICK_SLOP = 8

    row_header_clicked = pyqtSignal(int, object)  # logical, Qt.KeyboardModifiers

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self._press_logical: int | None = None
        self._press_y = 0
        self._press_modifiers = Qt.KeyboardModifier.NoModifier

    def _logical_at(self, y: int) -> int:
        point = QPoint(max(0, self.width() // 2), max(0, y))
        logical = self.logicalIndexAt(point)
        if logical >= 0:
            return logical
        logical = self.sectionAt(y)
        return logical if logical >= 0 else -1

    def _reset_pointer_state(self) -> None:
        self._press_logical = None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self._emit_context_menu(event.pos())
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        self._press_y = event.pos().y()
        self._press_modifiers = event.modifiers()
        self._press_logical = self._logical_at(self._press_y)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        moved = abs(event.pos().y() - self._press_y)
        if (
            moved <= self.CLICK_SLOP
            and self._press_logical is not None
            and self._press_logical >= 0
        ):
            self.row_header_clicked.emit(self._press_logical, self._press_modifiers)

        self._reset_pointer_state()
        event.accept()
