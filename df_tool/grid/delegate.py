"""GridCellDelegate — 격자선·선택 테두리 paint."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget

from df_tool.theme import COLORS


class GridCellDelegate(QStyledItemDelegate):
    """Frame 오버레이 없이 delegate paint로 셀 격자·선택 강조."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grid_color = QColor(COLORS["cell_grid"])
        self._selection_color = QColor(COLORS["primary"])
        self._active_cell: tuple[int, int] | None = None

    def set_active_cell(self, row: int | None, col: int | None) -> None:
        if row is None or col is None:
            self._active_cell = None
        else:
            self._active_cell = (row, col)

    def apply_theme(self) -> None:
        self._grid_color = QColor(COLORS["cell_grid"])
        self._selection_color = QColor(COLORS["primary"])

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:  # noqa: N802
        super().paint(painter, option, index)
        rect = option.rect
        painter.save()
        pen = QPen(self._grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        if self._active_cell == (index.row(), index.column()):
            sel_pen = QPen(self._selection_color)
            sel_pen.setWidth(2)
            painter.setPen(sel_pen)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        painter.restore()
