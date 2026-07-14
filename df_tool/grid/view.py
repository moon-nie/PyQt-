"""GridView — QTableView 래퍼."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractButton, QAbstractItemView, QHeaderView, QTableView

from df_tool.grid.delegate import GridCellDelegate
from df_tool.grid.header import GridHorizontalHeader, GridVerticalHeader
from df_tool.grid.model import GridModel
from df_tool.theme import COLORS


class GridView(QTableView):
    """가상화 QTableView — 스크롤·편집·선택."""

    def __init__(self, model: GridModel, parent=None) -> None:
        super().__init__(parent)
        h_header = GridHorizontalHeader(self)
        v_header = GridVerticalHeader(self)
        self.setHorizontalHeader(h_header)
        self.setVerticalHeader(v_header)
        self.setModel(model)
        self._delegate = GridCellDelegate(self)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setShowGrid(False)
        # 행·열 헤더가 만나는 왼쪽 위 코너 — 클릭 시 전체 선택(엑셀과 동일)
        self.setCornerButtonEnabled(True)
        corner = self.findChild(QAbstractButton)
        if corner is not None:
            corner.setToolTip("전체 선택 (Ctrl+A)")
        self.verticalHeader().setDefaultSectionSize(30)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setDefaultSectionSize(96)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionsClickable(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.apply_theme()

    @property
    def grid_delegate(self) -> GridCellDelegate:
        return self._delegate

    def apply_theme(self) -> None:
        self._delegate.apply_theme()
        bg = COLORS["surface"]
        alt = COLORS["row_alt"]
        fg = COLORS["text"]
        header_bg = COLORS["header_bg"]
        header_fg = COLORS["header_fg"]
        sel_bg = COLORS["row_selected"]
        self.setStyleSheet(
            f"""
            QTableView {{
                background-color: {bg};
                alternate-background-color: {alt};
                color: {fg};
                border: none;
                gridline-color: {COLORS['cell_grid']};
                selection-background-color: {sel_bg};
                selection-color: {fg};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_fg};
                border: none;
                border-right: 1px solid {COLORS['cell_grid']};
                border-bottom: 1px solid {COLORS['cell_grid']};
                padding: 4px 6px;
            }}
            QTableCornerButton::section {{
                background-color: {header_bg};
                border: none;
            }}
            """
        )

    def scroll_to_cell(self, row: int, col: int) -> None:
        idx = self.model().index(row, col)
        if idx.isValid():
            self.scrollTo(idx, QAbstractItemView.ScrollHint.EnsureVisible)

    def refresh_column_headers(self) -> None:
        """열 구조 변경 후 새 열 헤더 리사이즈가 동작하도록 재설정."""
        header = self.horizontalHeader()
        count = self.model().columnCount() if self.model() is not None else 0
        default_w = header.defaultSectionSize() or 96
        for visual in range(count):
            logical = header.logicalIndex(visual)
            if logical < 0:
                continue
            header.setSectionResizeMode(logical, QHeaderView.ResizeMode.Interactive)
            if header.sectionSize(logical) < 32:
                header.resizeSection(logical, default_w)
        header.viewport().update()

    def set_active_cell(self, row: int | None, col: int | None) -> None:
        self._delegate.set_active_cell(row, col)
        self.viewport().update()
