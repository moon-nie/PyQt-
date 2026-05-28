"""GridModel — pandas DataFrame ↔ QAbstractTableModel."""
from __future__ import annotations

from typing import Callable

import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal

from df_tool.grid.format import format_cell_value
from df_tool.performance import COLUMN_WINDOW_THRESHOLD, is_heavy_dataframe


class GridModel(QAbstractTableModel):
    """필터·정렬·열 윈도우를 row_map/col_map으로 표현하는 가상화 모델."""

    dataframe_changed = pyqtSignal()
    cell_edited = pyqtSignal(object, str, str)

    MAX_DATA_COLUMNS = 40

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._df: pd.DataFrame | None = None
        self._row_indices: list[object] = []
        self._columns: list[str] = []
        self._sort_column: str | None = None
        self._sort_ascending = True
        self._col_offset = 0
        self._use_col_window = False
        self._heavy = False
        self._on_commit_edit: Callable[[object, str, str], bool] | None = None

    def set_commit_handler(self, handler: Callable[[object, str, str], bool] | None) -> None:
        self._on_commit_edit = handler

    def source_dataframe(self) -> pd.DataFrame | None:
        return self._df

    def set_dataframe(
        self,
        df: pd.DataFrame,
        *,
        reset_sort: bool = True,
        col_offset: int = 0,
    ) -> None:
        self.beginResetModel()
        self._df = df
        rows, cols = len(df), len(df.columns)
        self._heavy = is_heavy_dataframe(rows, cols)
        self._use_col_window = cols > COLUMN_WINDOW_THRESHOLD
        self._col_offset = col_offset if self._use_col_window else 0
        if reset_sort:
            self._sort_column = None
            self._sort_ascending = True
        self._rebuild_row_map()
        self._rebuild_col_map()
        self.endResetModel()
        self.dataframe_changed.emit()

    def set_filtered_indices(self, indices: list[object]) -> None:
        self.beginResetModel()
        self._row_indices = list(indices)
        self.endResetModel()

    def set_sort(self, column: str | None, ascending: bool = True) -> None:
        self._sort_column = column
        self._sort_ascending = ascending
        self._rebuild_row_map()
        self.layoutChanged.emit()

    def set_col_offset(self, offset: int) -> None:
        if not self._use_col_window or self._df is None:
            return
        max_offset = max(0, len(self._df.columns) - self.MAX_DATA_COLUMNS)
        self._col_offset = max(0, min(offset, max_offset))
        self._rebuild_col_map()
        self.layoutChanged.emit()

    def col_offset(self) -> int:
        return self._col_offset

    def use_col_window(self) -> bool:
        return self._use_col_window

    def total_columns(self) -> int:
        return len(self._df.columns) if self._df is not None else 0

    def sort_state(self) -> tuple[str | None, bool]:
        return self._sort_column, self._sort_ascending

    def source_index_at(self, view_row: int) -> object | None:
        if 0 <= view_row < len(self._row_indices):
            return self._row_indices[view_row]
        return None

    def column_name_at(self, view_col: int) -> str | None:
        if 0 <= view_col < len(self._columns):
            return self._columns[view_col]
        return None

    def view_row_for_index(self, source_index: object) -> int | None:
        try:
            return self._row_indices.index(source_index)
        except ValueError:
            return None

    def view_col_for_name(self, column: str) -> int | None:
        try:
            return self._columns.index(column)
        except ValueError:
            return None

    def all_source_indices(self) -> list[object]:
        return list(self._row_indices)

    def all_column_names(self) -> list[str]:
        return list(self._columns)

    def _rebuild_row_map(self) -> None:
        if self._df is None:
            self._row_indices = []
            return
        indices = list(self._df.index)
        if self._sort_column and self._sort_column in self._df.columns:
            series = self._df[self._sort_column]
            order = series.sort_values(ascending=self._sort_ascending, na_position="last").index
            indices = list(order)
        self._row_indices = indices

    def _rebuild_col_map(self) -> None:
        if self._df is None:
            self._columns = []
            return
        all_cols = list(self._df.columns)
        if self._use_col_window:
            end = min(self._col_offset + self.MAX_DATA_COLUMNS, len(all_cols))
            self._columns = all_cols[self._col_offset:end]
        else:
            self._columns = all_cols

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._row_indices)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if not index.isValid() or self._df is None:
            return None
        row, col = index.row(), index.column()
        if row >= len(self._row_indices) or col >= len(self._columns):
            return None
        src_idx = self._row_indices[row]
        col_name = self._columns[col]
        value = self._df.at[src_idx, col_name]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if role == Qt.ItemDataRole.EditRole:
                from df_tool.grid.format import raw_value

                return raw_value(value)
            return format_cell_value(value, heavy=self._heavy)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._columns):
                return str(self._columns[section])
            return None
        if 0 <= section < len(self._row_indices):
            return str(section + 1)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:  # noqa: N802
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or self._df is None:
            return False
        src_idx = self.source_index_at(index.row())
        col_name = self.column_name_at(index.column())
        if src_idx is None or col_name is None:
            return False
        text = "" if value is None else str(value)
        if self._on_commit_edit is not None:
            ok = self._on_commit_edit(src_idx, col_name, text)
        else:
            ok = False
        if ok:
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            self.cell_edited.emit(src_idx, col_name, text)
        return ok

    def replace_dataframe(self, df: pd.DataFrame) -> None:
        """뷰어가 소스 DataFrame을 교체한 뒤 모델 표시만 동기화."""
        self._df = df
        rows, cols = len(df), len(df.columns)
        self._heavy = is_heavy_dataframe(rows, cols)
        if self.rowCount() > 0 and self.columnCount() > 0:
            top_left = self.index(0, 0)
            bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.dataChanged.emit(
                top_left,
                bottom_right,
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole],
            )
        else:
            self.layoutChanged.emit()

    def refresh(self) -> None:
        """소스 DataFrame은 유지하고 row/col 맵만 재계산."""
        if self._df is None:
            return
        self.beginResetModel()
        self._rebuild_row_map()
        self._rebuild_col_map()
        self.endResetModel()
