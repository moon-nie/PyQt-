"""SelectionController — QTableView 선택 ↔ SelectionScope."""
from __future__ import annotations

from PyQt6.QtCore import QModelIndex, QItemSelection, QItemSelectionModel

from df_tool.grid.model import GridModel
from df_tool.selection import SelectionScope


class SelectionController:
    """Qt 모델 인덱스를 Gridloom SelectionScope로 변환."""

    def __init__(self, model: GridModel) -> None:
        self._model = model

    def from_selection_model(
        self,
        selection_model: QItemSelectionModel,
        *,
        active_cell: tuple[object, str] | None = None,
    ) -> SelectionScope:
        indexes = selection_model.selectedIndexes()
        if not indexes:
            return SelectionScope()

        rows = {idx.row() for idx in indexes}
        cols = {idx.column() for idx in indexes}
        scope = SelectionScope()

        if len(rows) == self._model.rowCount() and len(cols) == 1:
            col_name = self._model.column_name_at(next(iter(cols)))
            if col_name:
                scope.mode = "column"
                scope.columns = {col_name}
                scope.anchor_column = col_name
                return scope

        if len(cols) == self._model.columnCount() and len(rows) >= 1:
            src_rows = {self._model.source_index_at(r) for r in rows}
            src_rows.discard(None)
            if src_rows:
                scope.mode = "rows" if len(src_rows) > 1 else "row"
                scope.rows = src_rows
                scope.anchor_row = next(iter(src_rows))
                return scope

        cells: set[tuple[object, str]] = set()
        for idx in indexes:
            src = self._model.source_index_at(idx.row())
            col = self._model.column_name_at(idx.column())
            if src is not None and col is not None:
                cells.add((src, col))
        if cells:
            scope.mode = "cell"
            scope.cells = cells
            if active_cell and active_cell in cells:
                scope.anchor_cell = active_cell
            else:
                scope.anchor_cell = next(iter(cells))
        return scope

    def select_cell(
        self,
        selection_model: QItemSelectionModel,
        source_index: object,
        column: str,
        *,
        clear: bool = True,
    ) -> None:
        row = self._model.view_row_for_index(source_index)
        col = self._model.view_col_for_name(column)
        if row is None or col is None:
            return
        idx = self._model.index(row, col)
        if clear:
            selection_model.clearSelection()
        selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select)
        selection_model.setCurrentIndex(idx, QItemSelectionModel.SelectionFlag.NoUpdate)

    def select_range(
        self,
        selection_model: QItemSelectionModel,
        top_left: tuple[object, str],
        bottom_right: tuple[object, str],
    ) -> None:
        r1 = self._model.view_row_for_index(top_left[0])
        c1 = self._model.view_col_for_name(top_left[1])
        r2 = self._model.view_row_for_index(bottom_right[0])
        c2 = self._model.view_col_for_name(bottom_right[1])
        if None in (r1, c1, r2, c2):
            return
        top_row, bottom_row = min(r1, r2), max(r1, r2)
        left_col, right_col = min(c1, c2), max(c1, c2)
        selection = QItemSelection(
            self._model.index(top_row, left_col),
            self._model.index(bottom_row, right_col),
        )
        selection_model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    @staticmethod
    def current_source_cell(selection_model: QItemSelectionModel, model: GridModel) -> tuple[object, str] | None:
        idx = selection_model.currentIndex()
        if not idx.isValid():
            return None
        src = model.source_index_at(idx.row())
        col = model.column_name_at(idx.column())
        if src is None or col is None:
            return None
        return src, col
