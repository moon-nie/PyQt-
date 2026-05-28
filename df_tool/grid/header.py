"""QHeaderView — 우클릭 메뉴 + 열 드래그 재정렬."""
from __future__ import annotations

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
    """열 헤더 — 드래그 재정렬 + 드롭 위치 표시."""

    COL_DRAG_THRESHOLD = 5
    COL_RESIZE_ZONE = 10

    column_reorder = pyqtSignal(int, int)
    drop_indicator_changed = pyqtSignal(object)  # int | None

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsMovable(False)
        self._drag_logical: int | None = None
        self._drag_start_x = 0
        self._dragging = False
        self._drop_x: int | None = None
        self._resize_active = False

    def _is_resize_edge(self, x: int) -> bool:
        zone = self.COL_RESIZE_ZONE
        for visual in range(self.count()):
            left = self.sectionPosition(visual)
            right = left + self.sectionSize(visual)
            if abs(x - right) <= zone:
                return True
            if visual > 0 and abs(x - left) <= zone:
                return True
        return False

    def _logical_at(self, x: int) -> int:
        point = QPoint(max(0, x), max(0, self.height() // 2))
        logical = self.logicalIndexAt(point)
        if logical >= 0:
            return logical
        logical = self.sectionAt(x)
        return logical if logical >= 0 else -1

    def _drop_x_for_logical(self, logical: int) -> int | None:
        if logical < 0:
            return None
        visual = self.visualIndex(logical)
        if visual < 0:
            return None
        return self.sectionPosition(visual)

    def _update_drop_target(self, x: int) -> None:
        logical = self._logical_at(x)
        drop_x = self._drop_x_for_logical(logical)
        if (
            self._drag_logical is not None
            and logical >= 0
            and logical == self._drag_logical
        ):
            drop_x = None
        if drop_x != self._drop_x:
            self._drop_x = drop_x
            self.drop_indicator_changed.emit(drop_x)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self._emit_context_menu(event.pos())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            if self._is_resize_edge(x):
                self._resize_active = True
                self._drag_logical = None
                self._dragging = False
            else:
                self._resize_active = False
                logical = self._logical_at(x)
                self._drag_logical = logical if logical >= 0 else None
                self._drag_start_x = x
                self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._resize_active:
            super().mouseMoveEvent(event)
            return
        if (
            (event.buttons() & Qt.MouseButton.LeftButton)
            and self._drag_logical is not None
        ):
            if (
                not self._dragging
                and abs(event.pos().x() - self._drag_start_x) >= self.COL_DRAG_THRESHOLD
            ):
                self._dragging = True
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            if self._dragging:
                self._update_drop_target(event.pos().x())
                event.accept()
                return
        super().mouseMoveEvent(event)

    def _clear_drag(self) -> None:
        self._drag_logical = None
        self._dragging = False
        self._drop_x = None
        self.unsetCursor()
        self.drop_indicator_changed.emit(None)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._resize_active:
            self._resize_active = False
            super().mouseReleaseEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            source = self._drag_logical
            target = self._logical_at(event.pos().x())
            if source is not None and target is not None and source >= 0 and target >= 0 and source != target:
                self.column_reorder.emit(source, target)
            self._clear_drag()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and not self._dragging:
            self._drag_logical = None
        super().mouseReleaseEvent(event)
