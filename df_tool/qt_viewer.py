"""PyQt 데이터 표 UI — GridModel/GridView 기반 DataFrameViewer."""
from __future__ import annotations

from typing import Callable

import pandas as pd
from PyQt6.QtCore import QItemSelectionModel, QEvent, QPoint, Qt, QTimer
from PyQt6.QtGui import QAction, QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from df_tool.grid import GridModel, GridView, SelectionController
from df_tool.grid.header import GridHorizontalHeader, GridVerticalHeader
from df_tool.grid.format import raw_value
from df_tool.performance import COLUMN_WINDOW_THRESHOLD, is_heavy_dataframe
from df_tool.qt_theme import card_frame_style
from df_tool.selection import SelectionScope
from df_tool.qt_viewer_ops import (
    delete_column_with_dialog,
    delete_columns_with_dialog,
    duplicate_column_with_dialog,
    fill_column_with_dialog,
    fill_sequential_with_dialog,
    merge_columns_with_dialog,
    split_column_with_dialog,
    insert_column_with_dialog,
    insert_row_with_dialog,
    rename_column_with_dialog,
)
from df_tool.theme import COLORS


class DataFrameViewer(QWidget):
    """Tk DataFrameViewer와 동일한 public API를 제공하는 PyQt 위젯."""


    def __init__(
        self,
        parent: QWidget | None = None,
        on_change: Callable[[pd.DataFrame], None] | None = None,
        on_info_refresh: Callable[[pd.DataFrame], None] | None = None,
        on_selection_change: Callable[[SelectionScope], None] | None = None,
        on_action: Callable[[str], None] | None = None,
        on_action_error: Callable[[str, str], None] | None = None,
        on_drop_duplicates: Callable[[], None] | None = None,
        on_drop_na_rows: Callable[[], None] | None = None,
        on_fill_na: Callable[[], None] | None = None,
        on_fill_na_column: Callable[[str], None] | None = None,
        on_vlookup: Callable[[], None] | None = None,
        on_merge: Callable[[], None] | None = None,
        on_concat: Callable[[], None] | None = None,
        on_group_summary: Callable[[], None] | None = None,
        on_add_column: Callable[[], None] | None = None,
        on_delete_column: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_change = on_change
        self.on_info_refresh = on_info_refresh
        self.on_selection_change = on_selection_change
        self.on_action = on_action
        self.on_action_error = on_action_error
        self.on_drop_duplicates = on_drop_duplicates
        self.on_drop_na_rows = on_drop_na_rows
        self.on_fill_na = on_fill_na
        self.on_fill_na_column = on_fill_na_column
        self.on_vlookup = on_vlookup
        self.on_merge = on_merge
        self.on_concat = on_concat
        self.on_group_summary = on_group_summary
        self.on_add_column = on_add_column
        self.on_delete_column = on_delete_column

        self._df: pd.DataFrame | None = None
        self._filtered_indices: list[object] = []
        self._filter_pinned_rows: set[object] = set()
        self._selection = SelectionScope()
        self._active_cell: tuple[object, str] | None = None
        self._sort_column: str | None = None
        self._sort_ascending = True
        self._col_offset = 0
        self._use_col_window = False
        self._restore_callback: Callable[[], None] | None = None
        self._preserve_scroll = False
        self._syncing_column_selection = False
        self._syncing_row_selection = False
        self._model = GridModel(self)
        self._model.set_commit_handler(self._commit_cell_edit)
        self._selection_ctrl = SelectionController(self._model)

        self._build_ui()
        self._bind_events()

    @staticmethod
    def _add_action_btn(row: QHBoxLayout, label: str, callback: Callable[[], None] | None) -> None:
        btn = QPushButton(label)
        btn.setEnabled(callback is not None)
        if callback:
            btn.clicked.connect(callback)
        row.addWidget(btn)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        preview_block = QFrame()
        preview_block.setObjectName("CardFrame")
        preview_block.setStyleSheet(card_frame_style())
        self._preview_block = preview_block
        preview_layout = QVBoxLayout(preview_block)
        preview_layout.setContentsMargins(10, 8, 10, 8)
        preview_layout.setSpacing(4)
        header = QHBoxLayout()
        header.addWidget(QLabel("선택 값"))
        header.addStretch()
        self.selection_label = QLabel("선택 없음")
        self.selection_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        header.addWidget(self.selection_label)
        preview_layout.addLayout(header)

        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(False)
        self.preview_text.setMaximumHeight(56)
        self.preview_text.setPlaceholderText("셀을 클릭하면 전체 내용이 표시됩니다")
        preview_layout.addWidget(self.preview_text)
        self.preview_meta = QLabel("")
        self.preview_meta.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        preview_layout.addWidget(self.preview_meta)
        layout.addWidget(preview_block)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        search_row.addWidget(QLabel("검색"))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("값 검색 · 공백=결측치")
        search_row.addWidget(self.search_entry, stretch=1)
        self.search_column_combo = QComboBox()
        self.search_column_combo.setMinimumWidth(120)
        self.search_column_combo.addItem("전체 열")
        search_row.addWidget(self.search_column_combo)
        self.search_exact_cb = QCheckBox("정확히")
        self.search_exclude_cb = QCheckBox("제외")
        search_row.addWidget(self.search_exact_cb)
        search_row.addWidget(self.search_exclude_cb)
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self._apply_filter_now)
        search_row.addWidget(self.search_btn)
        reset_btn = QPushButton("보기 초기화")
        reset_btn.clicked.connect(self._reset_view)
        search_row.addWidget(reset_btn)
        self._restore_btn = QPushButton("원본 복원")
        self._restore_btn.setVisible(False)
        self._restore_btn.clicked.connect(self._on_restore_original)
        search_row.addWidget(self._restore_btn)
        layout.addLayout(search_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        self._add_action_btn(action_row, "VLOOKUP", self.on_vlookup)
        self._add_action_btn(action_row, "조인", self.on_merge)
        self._add_action_btn(action_row, "병합", self.on_concat)
        action_row.addStretch()
        self._add_action_btn(action_row, "그룹", self.on_group_summary)
        self._add_action_btn(action_row, "결측 채우기", self.on_fill_na)
        self._add_action_btn(action_row, "결측 제거", self.on_drop_na_rows)
        self._add_action_btn(action_row, "중복 제거", self.on_drop_duplicates)
        self._add_action_btn(action_row, "+ 열", self.on_add_column)
        layout.addLayout(action_row)

        self._table = GridView(self._model, self)
        self._table.verticalHeader().setSectionsClickable(True)
        self._col_drop_line = QFrame(self._table)
        self._col_drop_line.setFixedWidth(3)
        self._col_drop_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._col_drop_line.setStyleSheet(
            f"background-color: {COLORS['primary']}; border: none;"
        )
        self._col_drop_line.hide()
        layout.addWidget(self._table, stretch=1)

        self.page_label = QLabel("")
        self.page_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self.page_label)

    def _bind_events(self) -> None:
        self.preview_text.installEventFilter(self)

        sel = self._table.selectionModel()
        sel.selectionChanged.connect(self._on_selection_changed)
        sel.currentChanged.connect(self._on_current_changed)
        h_header = self._table.horizontalHeader()
        v_header = self._table.verticalHeader()
        h_header.sectionDoubleClicked.connect(self._on_header_double_clicked)
        if isinstance(h_header, GridHorizontalHeader):
            h_header.column_header_clicked.connect(self._on_column_header_clicked)
            h_header.header_context_menu.connect(self._show_column_header_menu)
            h_header.column_reorder.connect(self._on_column_reorder)
            h_header.drop_indicator_changed.connect(self._on_col_drop_indicator)
        if isinstance(v_header, GridVerticalHeader):
            v_header.row_header_clicked.connect(self._on_row_header_clicked)
        else:
            v_header.sectionClicked.connect(self._on_row_header_clicked)
        v_header.header_context_menu.connect(self._show_row_header_menu)

        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        self.search_entry.returnPressed.connect(self._apply_filter_now)

        QShortcut(QKeySequence("Ctrl+C"), self, self._on_copy)
        QShortcut(QKeySequence("Ctrl+V"), self, self._on_paste)
        QShortcut(QKeySequence("Ctrl+A"), self._table, self._select_all)
        QShortcut(QKeySequence("Ctrl+Space"), self._table, self._select_column_shortcut)
        QShortcut(QKeySequence("Shift+Space"), self._table, self._select_row_shortcut)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self._table, lambda: self._table.clearFocus())
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table, self._clear_selection_content)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self._table, self._clear_selection_content)
        QShortcut(QKeySequence(Qt.Key.Key_F2), self._table, lambda: self._table.edit(self._table.currentIndex()))
        QShortcut(QKeySequence("Ctrl+Home"), self._table, self._go_first_cell)
        QShortcut(QKeySequence("Ctrl+End"), self._table, self._go_last_cell)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self._table, lambda: self._page_scroll(-1))
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self._table, lambda: self._page_scroll(1))
        for key in (
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Backtab,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
        ):
            QShortcut(QKeySequence(key), self._table, lambda k=key: self._on_key_nav(k))

    def _on_key_nav(self, key: Qt.Key) -> None:
        if self._df is None or self._table.state() == self._table.State.EditingState:
            return
        idx = self._table.currentIndex()
        if not idx.isValid():
            return
        row, col = idx.row(), idx.column()
        mods = QApplication.keyboardModifiers()
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)

        if key == Qt.Key.Key_Up:
            row = max(0, row - 1)
        elif key == Qt.Key.Key_Down:
            row = min(self._model.rowCount() - 1, row + 1)
        elif key == Qt.Key.Key_Left:
            col = max(0, col - 1)
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Tab):
            col = min(self._model.columnCount() - 1, col + 1)
        elif key == Qt.Key.Key_Backtab:
            col = max(0, col - 1)
        elif key == Qt.Key.Key_Home:
            col = 0
        elif key == Qt.Key.Key_End:
            col = self._model.columnCount() - 1

        new_idx = self._model.index(row, col)
        if not new_idx.isValid():
            return
        sel = self._table.selectionModel()
        if shift:
            sel.select(new_idx, QItemSelectionModel.SelectionFlag.Select)
        else:
            sel.setCurrentIndex(new_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self._table.scrollTo(new_idx)

    def _defer_action(self, fn, *args, **kwargs) -> None:
        QTimer.singleShot(0, lambda: fn(*args, **kwargs))

    def _save_scroll(self) -> tuple[int, int]:
        return (
            self._table.verticalScrollBar().value(),
            self._table.horizontalScrollBar().value(),
        )

    def _restore_scroll(self, vertical: int, horizontal: int) -> None:
        self._table.verticalScrollBar().setValue(vertical)
        self._table.horizontalScrollBar().setValue(horizontal)

    def _go_first_cell(self) -> None:
        if self._df is None or self._model.rowCount() == 0 or self._model.columnCount() == 0:
            return
        idx = self._model.index(0, 0)
        self._table.selectionModel().setCurrentIndex(
            idx,
            QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    def _go_last_cell(self) -> None:
        if self._df is None or self._model.rowCount() == 0 or self._model.columnCount() == 0:
            return
        idx = self._model.index(self._model.rowCount() - 1, self._model.columnCount() - 1)
        self._table.selectionModel().setCurrentIndex(
            idx,
            QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    def _page_scroll(self, direction: int) -> None:
        bar = self._table.verticalScrollBar()
        step = max(self._table.viewport().height(), 1)
        bar.setValue(bar.value() + direction * step)

    def _on_col_drop_indicator(self, x) -> None:
        if x is None:
            self._col_drop_line.hide()
            return
        header = self._table.horizontalHeader()
        top_left = header.mapTo(self._table, QPoint(int(x), 0))
        height = max(self._table.height() - header.height(), 1)
        self._col_drop_line.setGeometry(top_left.x() - 1, header.height(), 3, height)
        self._col_drop_line.raise_()
        self._col_drop_line.show()

    def _on_column_reorder(self, source_logical: int, target_logical: int) -> None:
        if self._df is None or source_logical == target_logical:
            return
        source_col = self._model.column_name_at(source_logical)
        target_col = self._model.column_name_at(target_logical)
        if source_col is None or target_col is None:
            return
        from df_tool.operations import reorder_columns

        self._col_drop_line.hide()
        self._apply_df(
            reorder_columns(self._df, source_col, target_col),
            action="열 순서 변경",
            restructure=True,
        )

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.preview_text and event.type() == QEvent.Type.FocusOut:
            self._commit_preview_edit()
        return super().eventFilter(obj, event)

    # --- Public API (Tk viewer 호환) ---

    def get_selection(self) -> SelectionScope:
        return self._selection

    def get_dataframe(self) -> pd.DataFrame | None:
        return self._df.copy() if self._df is not None else None

    def prepare_for_new_dataset(self) -> None:
        self._filter_pinned_rows.clear()
        self.search_entry.clear()
        self.search_column_combo.setCurrentText("전체 열")
        self.search_exact_cb.setChecked(False)
        self.search_exclude_cb.setChecked(False)
        self._col_offset = 0
        self._use_col_window = False
        self._active_cell = None
        self.preview_text.setPlainText("셀을 클릭하면 전체 내용이 표시됩니다")
        self.preview_meta.setText("")

    def set_dataframe(
        self,
        df: pd.DataFrame,
        *,
        reset_sort: bool = True,
        copy: bool = False,
        new_session: bool = False,
    ) -> None:
        if new_session:
            self.prepare_for_new_dataset()
            self._filter_pinned_rows.clear()
            self._selection = SelectionScope()
            self._active_cell = None
        if copy:
            self._assign_df(df.copy())
        else:
            self._assign_df(df)
        if reset_sort:
            self._sort_column = None
            self._sort_ascending = True
        if new_session:
            self._refresh_search_columns()
        self._recompute_filtered_indices()
        self._sync_model(reset_sort=reset_sort)
        self._update_selection_label()
        self._update_page_label()

    def set_restore_available(self, available: bool, callback: Callable[[], None] | None = None) -> None:
        self._restore_callback = callback if available else None
        self._restore_btn.setVisible(available and callback is not None)

    def clear(self) -> None:
        self.prepare_for_new_dataset()
        self._df = None
        self._filtered_indices = []
        self._filter_pinned_rows.clear()
        self._selection = SelectionScope()
        self._active_cell = None
        self._model.set_dataframe(pd.DataFrame())
        self._update_selection_label()
        self._update_page_label()

    def replace_dataframe(self, df: pd.DataFrame) -> None:
        self.set_dataframe(df, reset_sort=False, copy=False, new_session=False)
        self._notify_change()

    def sort_by(self, column: str, ascending: bool = True) -> None:
        if self._df is None:
            return
        self._sort_column = column
        self._sort_ascending = ascending
        self._model.set_sort(column, ascending)
        self._model.set_filtered_indices(self._sorted_filtered_indices())
        self._update_page_label()

    def delete_selected_rows(self) -> None:
        self._delete_selected_rows()

    def insert_row_above_selection(self) -> None:
        self._insert_row_at_selection("above")

    def insert_row_below_selection(self) -> None:
        self._insert_row_at_selection("below")

    def insert_column_left_selection(self) -> None:
        self._insert_column_at_selection("left")

    def insert_column_right_selection(self) -> None:
        self._insert_column_at_selection("right")

    def apply_theme(self) -> None:
        from df_tool.qt_theme import card_frame_style

        self._preview_block.setStyleSheet(card_frame_style())
        self._col_drop_line.setStyleSheet(
            f"background-color: {COLORS['primary']}; border: none;"
        )
        self.selection_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.preview_meta.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        self.page_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self._table.apply_theme()

    # --- Internal ---

    def _assign_df(self, df: pd.DataFrame) -> None:
        self._df = df
        cols = len(df.columns)
        self._use_col_window = cols > COLUMN_WINDOW_THRESHOLD
        if not self._use_col_window:
            self._col_offset = 0

    def _apply_df(
        self,
        df: pd.DataFrame,
        *,
        action: str | None = None,
        restructure: bool = False,
    ) -> None:
        """DataFrame 교체 — restructure=True면 행·열 구조 변경(추가/삭제 등)."""
        self._assign_df(df)
        if restructure:
            self._recompute_filtered_indices()
            self._sync_model(reset_sort=False)
        else:
            self._model.replace_dataframe(df)
            self._table.refresh_column_headers()
        self._notify_change(action=action)

    def _index_list(self) -> list:
        return self._model.all_source_indices()

    def _column_list(self) -> list:
        return self._model.all_column_names()

    def _sorted_row_indices(self, indices: set) -> list:
        order = self._index_list()
        pos = {idx: i for i, idx in enumerate(order)}
        return sorted(indices, key=lambda x: pos.get(x, 0))

    def _sorted_columns(self, columns: set) -> list:
        order = self._column_list()
        pos = {c: i for i, c in enumerate(order)}
        return sorted(columns, key=lambda x: pos.get(x, 0))

    def _display_row_indices(self) -> list[object]:
        """검색 결과 + 필터 중 편집한 행(조건에 안 맞아도 유지)."""
        indices = list(self._filtered_indices)
        if self._df is not None and self._filter_pinned_rows:
            seen = set(indices)
            for idx in self._filter_pinned_rows:
                if idx in self._df.index and idx not in seen:
                    indices.append(idx)
                    seen.add(idx)
        return indices

    def _sorted_filtered_indices(self) -> list[object]:
        indices = self._display_row_indices()
        if not indices or self._df is None or not self._sort_column:
            return indices
        if self._sort_column not in self._df.columns:
            return indices
        subset = self._df.loc[indices, self._sort_column]
        order = subset.sort_values(ascending=self._sort_ascending, na_position="last").index
        return list(order)

    def _sync_model(self, *, reset_sort: bool = True) -> None:
        if self._df is None:
            return
        self._model.set_dataframe(
            self._df,
            reset_sort=reset_sort and self._sort_column is None,
            col_offset=self._col_offset,
        )
        if self._sort_column:
            self._model.set_sort(self._sort_column, self._sort_ascending)
        self._model.set_filtered_indices(self._sorted_filtered_indices())
        self._table.refresh_column_headers()

    def _refresh_search_columns(self) -> None:
        self.search_column_combo.blockSignals(True)
        current = self.search_column_combo.currentText()
        self.search_column_combo.clear()
        self.search_column_combo.addItem("전체 열")
        if self._df is not None:
            for col in self._df.columns:
                self.search_column_combo.addItem(str(col))
        idx = self.search_column_combo.findText(current)
        if idx >= 0:
            self.search_column_combo.setCurrentIndex(idx)
        self.search_column_combo.blockSignals(False)

    def _search_target_columns(self) -> list[str]:
        assert self._df is not None
        choice = self.search_column_combo.currentText().strip()
        if choice and choice != "전체 열":
            from df_tool.operations import resolve_column_key

            key = resolve_column_key(self._df, choice)
            return [key] if key in self._df.columns else [str(c) for c in self._df.columns]
        return [str(c) for c in self._df.columns]

    def _is_specific_search_column(self) -> bool:
        choice = self.search_column_combo.currentText().strip()
        return bool(choice and choice != "전체 열")

    def _build_null_mask(self) -> pd.Series:
        from df_tool.operations import null_mask

        assert self._df is not None
        cols = self._search_target_columns()
        if len(cols) == 1:
            return null_mask(self._df[cols[0]])
        mask = pd.Series(False, index=self._df.index)
        for col in cols:
            mask |= null_mask(self._df[col])
        return mask

    def _build_search_mask(self, query: str) -> pd.Series:
        assert self._df is not None
        exact = self.search_exact_cb.isChecked()
        exclude = self.search_exclude_cb.isChecked()
        q = query.lower()
        match: pd.Series | None = None
        for col in self._search_target_columns():
            series = self._df[col].astype("string", copy=False).str.lower()
            col_match = series == q if exact else series.str.contains(q, na=False, regex=False)
            match = col_match if match is None else (match | col_match)
        if match is None:
            match = pd.Series(False, index=self._df.index)
        return ~match if exclude else match

    def _recompute_filtered_indices(self) -> None:
        if self._df is None:
            self._filtered_indices = []
            return
        query = self.search_entry.text().strip()
        if not query:
            if self._is_specific_search_column():
                mask = self._build_null_mask()
                if self.search_exclude_cb.isChecked():
                    mask = ~mask
                self._filtered_indices = list(self._df.index[mask])
            else:
                self._filtered_indices = list(self._df.index)
        else:
            self._filtered_indices = list(self._df.index[self._build_search_mask(query)])

    def _row_filter_active(self) -> bool:
        """검색·필터로 일부 행만 표시 중인지."""
        if self._df is None:
            return False
        return len(self._filtered_indices) < len(self._df.index)

    def _cells_for_visible_columns(self, columns: list[str]) -> list[tuple[object, str]]:
        rows = self._index_list()
        return [(row, col) for col in columns for row in rows]

    def _apply_filter_now(self) -> None:
        self._filter_pinned_rows.clear()
        self._recompute_filtered_indices()
        self._model.set_filtered_indices(self._sorted_filtered_indices())
        self._update_page_label()

    def _pin_row_under_filter(self, source_index: object) -> None:
        """검색 조건에서 벗어난 뒤에도 방금 편집한 행을 목록에 남김."""
        if self._df is None or source_index not in self._df.index:
            return
        if self._row_filter_active():
            self._filter_pinned_rows.add(source_index)

    def _reset_view(self) -> None:
        if self._df is None:
            return
        self.search_entry.clear()
        self.search_column_combo.setCurrentText("전체 열")
        self.search_exact_cb.setChecked(False)
        self.search_exclude_cb.setChecked(False)
        self._sort_column = None
        self._sort_ascending = True
        self._col_offset = 0
        self._selection = SelectionScope()
        self._active_cell = None
        self._filter_pinned_rows.clear()
        self._recompute_filtered_indices()
        self._sync_model(reset_sort=True)
        self._table.clearSelection()
        self._update_selection_label()
        self._update_page_label()
        if self.on_action:
            self.on_action("보기 초기화")

    def _on_selection_changed(self) -> None:
        if self._syncing_column_selection or self._syncing_row_selection:
            return
        active = self._active_cell
        self._selection = self._selection_ctrl.from_selection_model(
            self._table.selectionModel(),
            active_cell=active,
        )
        self._update_selection_label()
        if self.on_selection_change:
            self.on_selection_change(self._selection)

    def _on_current_changed(self, current, _previous) -> None:
        if self._syncing_column_selection or self._syncing_row_selection:
            return
        if not current.isValid() or self._df is None:
            return
        src = self._model.source_index_at(current.row())
        col = self._model.column_name_at(current.column())
        if src is None or col is None:
            return
        self._active_cell = (src, col)
        self._table.set_active_cell(current.row(), current.column())
        value = self._df.at[src, col]
        self.preview_text.blockSignals(True)
        self.preview_text.setPlainText(raw_value(value))
        self.preview_text.blockSignals(False)
        self.preview_meta.setText(f"[{src}, {col}]")
        if not self._preserve_scroll:
            self._on_selection_changed()

    def _commit_preview_edit(self) -> None:
        if self._df is None or self._active_cell is None:
            return
        idx, col = self._active_cell
        text = self.preview_text.toPlainText()
        current = raw_value(self._df.at[idx, col])
        if text == current:
            return
        from df_tool.operations import set_cell_value

        try:
            new_df = set_cell_value(self._df, idx, col, text)
        except Exception as exc:
            self._emit_error("셀 편집", str(exc))
            return
        self._apply_df(new_df)
        self._pin_row_under_filter(idx)

    def _commit_cell_edit(self, source_index: object, column: str, text: str) -> bool:
        if self._df is None:
            return False
        from df_tool.operations import set_cell_value

        try:
            new_df = set_cell_value(self._df, source_index, column, text)
        except Exception as exc:
            self._emit_error("셀 편집", str(exc))
            return False
        self._apply_df(new_df)
        self._pin_row_under_filter(source_index)
        if self._active_cell == (source_index, column):
            self.preview_text.blockSignals(True)
            self.preview_text.setPlainText(text)
            self.preview_text.blockSignals(False)
        return True

    def _on_column_header_clicked(self, section: int, modifiers) -> None:
        if self._df is None:
            return
        col_name = self._model.column_name_at(section)
        if col_name is None:
            return
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self._toggle_column_in_selection(col_name)
        else:
            self._select_column(col_name)

    def _on_header_double_clicked(self, section: int) -> None:
        if self._df is None:
            return
        col_name = self._model.column_name_at(section)
        if not col_name:
            return
        if self._sort_column == col_name:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = col_name
            self._sort_ascending = True
        self._model.set_sort(self._sort_column, self._sort_ascending)
        self._model.set_filtered_indices(self._sorted_filtered_indices())
        self._update_page_label()

    def _on_row_header_clicked(self, section: int, modifiers=Qt.KeyboardModifier.NoModifier) -> None:
        if self._df is None:
            return
        src = self._model.source_index_at(section)
        if src is None:
            return
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            anchor = self._selection.anchor_row
            if anchor is not None and self._selection.mode in {"row", "rows"}:
                self._select_row_range(anchor, src)
            else:
                self._select_row(src)
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            self._toggle_row_in_selection(src)
        else:
            self._select_row(src)

    def _select_column(self, column: str) -> None:
        self._select_columns([column])

    def _selected_column_names(self) -> list[str]:
        scope = self._selection_ctrl.from_selection_model(
            self._table.selectionModel(),
            active_cell=self._active_cell,
        )
        if scope.mode in {"column", "columns"} and scope.columns:
            return self._sorted_columns(scope.columns)
        if self._selection.mode in {"column", "columns"} and self._selection.columns:
            return self._sorted_columns(self._selection.columns)
        return []

    def _select_columns(self, columns: list[str]) -> None:
        if self._df is None:
            return
        ordered = self._sorted_columns(set(columns))
        if not ordered:
            return
        rows = self._index_list()
        if not rows:
            return
        sel_model = self._table.selectionModel()
        self._syncing_column_selection = True
        sel_model.blockSignals(True)
        try:
            self._selection_ctrl.select_columns(
                sel_model,
                ordered,
                clear=True,
            )
            mode = "column" if len(ordered) == 1 else "columns"
            self._selection = SelectionScope(
                mode=mode,
                columns=set(ordered),
                anchor_column=ordered[0],
            )
            self._active_cell = (rows[0], ordered[0])
            self._update_selection_label()
            view_col = self._model.view_col_for_name(ordered[0]) or 0
            idx = self._model.index(0, view_col)
            if idx.isValid():
                self._table.set_active_cell(idx.row(), idx.column())
            self._table.setFocus(Qt.FocusReason.OtherFocusReason)
        finally:
            sel_model.blockSignals(False)
            self._syncing_column_selection = False

    def _toggle_column_in_selection(self, column: str) -> None:
        if self._df is None:
            return
        current = self._selected_column_names()
        if current:
            cols = set(current)
            if column in cols:
                cols.discard(column)
                if not cols:
                    self._table.clearSelection()
                    self._selection = SelectionScope()
                    self._active_cell = None
                    self._update_selection_label()
                    return
            else:
                cols.add(column)
            self._select_columns(list(cols))
        else:
            self._select_column(column)

    def _select_row(self, source_index: object) -> None:
        self._select_rows([source_index])

    def _select_rows(self, source_indices: list[object]) -> None:
        if self._df is None:
            return
        ordered = self._sorted_row_indices(set(source_indices))
        if not ordered:
            return
        cols = self._column_list()
        if not cols:
            return
        sel_model = self._table.selectionModel()
        self._syncing_row_selection = True
        sel_model.blockSignals(True)
        try:
            self._selection_ctrl.select_rows(sel_model, ordered, clear=True)
            mode = "row" if len(ordered) == 1 else "rows"
            self._selection = SelectionScope(
                mode=mode,
                rows=set(ordered),
                anchor_row=ordered[0],
            )
            self._active_cell = (ordered[0], cols[0])
            self._update_selection_label()
            view_col = self._model.view_col_for_name(cols[0]) or 0
            view_row = self._model.view_row_for_index(ordered[0])
            if view_row is not None:
                self._table.set_active_cell(view_row, view_col)
            self._table.setFocus(Qt.FocusReason.OtherFocusReason)
        finally:
            sel_model.blockSignals(False)
            self._syncing_row_selection = False

    def _select_row_range(self, start_index: object, end_index: object) -> None:
        idx_order = self._index_list()
        try:
            i0 = idx_order.index(start_index)
            i1 = idx_order.index(end_index)
        except ValueError:
            self._select_row(end_index)
            return
        lo, hi = min(i0, i1), max(i0, i1)
        self._select_rows(idx_order[lo : hi + 1])

    def _toggle_row_in_selection(self, source_index: object) -> None:
        if self._df is None:
            return
        if self._selection.mode in {"row", "rows"} and self._selection.rows:
            rows = set(self._selection.rows)
            if source_index in rows:
                rows.discard(source_index)
                if not rows:
                    self._table.clearSelection()
                    self._selection = SelectionScope()
                    self._active_cell = None
                    self._update_selection_label()
                    return
            else:
                rows.add(source_index)
            self._select_rows(list(rows))
        else:
            self._select_row(source_index)

    def _update_selection_label(self) -> None:
        self.selection_label.setText(self._selection.describe())

    def _update_page_label(self) -> None:
        if self._df is None:
            self.page_label.setText("")
            return
        shown = len(self._display_row_indices())
        matched = len(self._filtered_indices)
        total = len(self._df)
        if shown != matched and self._row_filter_active():
            parts = [f"{shown:,}행 표시 (검색 {matched:,} + 편집 {shown - matched:,}) / {total:,}행"]
        else:
            parts = [f"{shown:,} / {total:,}행 표시"]
        if self._use_col_window:
            cols = len(self._df.columns)
            end = min(self._col_offset + GridModel.MAX_DATA_COLUMNS, cols)
            parts.append(f"열 {self._col_offset + 1}–{end} / {cols}")
        if self._sort_column:
            arrow = "▲" if self._sort_ascending else "▼"
            parts.append(f"정렬: {self._sort_column} {arrow}")
        self.page_label.setText(" · ".join(parts))

    def _notify_change(self, *, action: str | None = None) -> None:
        if self.on_change and self._df is not None:
            self.on_change(self._df)
        if self.on_info_refresh and self._df is not None:
            self.on_info_refresh(self._df)
        if action and self.on_action:
            self.on_action(action)

    def _emit_error(self, title: str, detail: str) -> None:
        if self.on_action_error:
            self.on_action_error(title, detail)
        else:
            QMessageBox.critical(self, title, detail)

    def _clear_selection_content(self) -> None:
        if self._df is None:
            return
        from df_tool.operations import clear_cells, clear_columns, clear_rows

        if self._selection.mode in {"column", "columns"} and self._selection.columns:
            cols = list(self._selection.columns)
            if self._row_filter_active():
                cells = self._cells_for_visible_columns(cols)
                self._apply_df(
                    clear_cells(self._df, cells),
                    action="검색 결과 행 내용 지우기",
                )
            else:
                self._apply_df(clear_columns(self._df, cols), action="선택 영역 지우기")
        elif self._selection.mode in {"row", "rows"} and self._selection.rows:
            self._apply_df(clear_rows(self._df, list(self._selection.rows)), action="선택 영역 지우기")
        elif self._selection.cells:
            self._apply_df(clear_cells(self._df, list(self._selection.cells)), action="선택 영역 지우기")
        elif self._active_cell:
            self._apply_df(clear_cells(self._df, [self._active_cell]), action="선택 영역 지우기")
        else:
            return

    def _copy_grid(self) -> list[list[str]] | None:
        if self._df is None:
            return None
        if self._selection.mode in {"column", "columns"} and self._selection.columns:
            cols = self._sorted_columns(self._selection.columns)
            rows = self._index_list()
            return [[raw_value(self._df.at[r, c]) for c in cols] for r in rows]
        if self._selection.mode in {"row", "rows"} and self._selection.rows:
            cols = self._column_list()
            rows = self._sorted_row_indices(self._selection.rows)
            return [[raw_value(self._df.at[r, c]) for c in cols] for r in rows]
        if self._selection.mode == "cell" and self._selection.cells:
            cols = self._sorted_columns({c for _, c in self._selection.cells})
            rows = self._sorted_row_indices({r for r, _ in self._selection.cells})
            return [
                [
                    raw_value(self._df.at[r, c]) if (r, c) in self._selection.cells else ""
                    for c in cols
                ]
                for r in rows
            ]
        if self._active_cell:
            r, c = self._active_cell
            if r in self._df.index and c in self._df.columns:
                return [[raw_value(self._df.at[r, c])]]
        return None

    @staticmethod
    def _grid_to_clipboard_text(grid: list[list[str]]) -> str:
        if len(grid) == 1 and len(grid[0]) == 1:
            return grid[0][0]
        return "\n".join("\t".join(row) for row in grid)

    @staticmethod
    def _parse_clipboard_grid(text: str) -> list[list[str]]:
        if not text:
            return [[""]]
        rows = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if rows and rows[-1] == "":
            rows.pop()
        if not rows:
            return [[""]]
        return [row.split("\t") for row in rows]

    def _assignments_at_anchor(
        self,
        start_idx: object,
        start_col: str,
        grid: list[list[str]],
    ) -> list[tuple[object, str, str]]:
        """앵커 셀부터 오른쪽·아래로 클립보드 격자 붙여넣기 (엑셀 방식)."""
        idx_order = self._index_list()
        col_order = self._column_list()
        if not idx_order or not col_order:
            return []
        try:
            r0 = idx_order.index(start_idx)
            c0 = col_order.index(start_col)
        except ValueError:
            return []
        out: list[tuple[object, str, str]] = []
        for dr, row_vals in enumerate(grid):
            for dc, value in enumerate(row_vals):
                ri = r0 + dr
                ci = c0 + dc
                if ri >= len(idx_order) or ci >= len(col_order):
                    continue
                out.append((idx_order[ri], col_order[ci], value))
        return out

    def _ensure_paste_fits(self, grid: list[list[str]], anchor: tuple[object, str]) -> None:
        """붙여넣기 범위가 표를 넘으면 행·열을 자동 추가."""
        if self._df is None or not grid:
            return
        idx_order = self._index_list()
        col_order = self._column_list()
        rows_h = len(grid)
        cols_w = max((len(r) for r in grid), default=0)
        try:
            r0 = idx_order.index(anchor[0])
            c0 = col_order.index(anchor[1])
        except ValueError:
            return
        from df_tool.operations import insert_column_at_end, insert_row_at_end

        df = self._df
        changed = False
        need_rows = r0 + rows_h - len(idx_order)
        if need_rows > 0:
            df = insert_row_at_end(df, need_rows)
            changed = True
        need_cols = c0 + cols_w - len(col_order)
        for _ in range(max(0, need_cols)):
            df = insert_column_at_end(df)
            changed = True
        if changed:
            self._apply_df(df, restructure=True)
            self._refresh_search_columns()

    def _paste_anchor(self) -> tuple[object, str] | None:
        if self._selection.mode in {"column", "columns"} and self._selection.columns:
            cols = self._sorted_columns(self._selection.columns)
            idx_order = self._index_list()
            if cols and idx_order:
                return idx_order[0], cols[0]
        if self._selection.mode in {"row", "rows"} and self._selection.rows:
            rows = self._sorted_row_indices(self._selection.rows)
            cols = self._column_list()
            if rows and cols:
                return rows[0], cols[0]
        if self._active_cell:
            return self._active_cell
        if self._selection.cells:
            rows = self._sorted_row_indices({r for r, _ in self._selection.cells})
            cols = self._sorted_columns({c for _, c in self._selection.cells})
            if rows and cols:
                return rows[0], cols[0]
        return None

    def _build_paste_assignments(self, grid: list[list[str]]) -> list[tuple[object, str, str]]:
        if self._df is None or not grid:
            return []
        idx_order = self._index_list()
        col_order = self._column_list()
        if not idx_order or not col_order:
            return []
        rows_h = len(grid)
        cols_w = max((len(r) for r in grid), default=0)
        single_value = rows_h == 1 and cols_w <= 1
        one = grid[0][0] if single_value else None
        mode = self._selection.mode

        if mode in {"column", "columns"} and self._selection.columns:
            target_cols = self._sorted_columns(self._selection.columns)
            if single_value:
                return [(r, c, one) for r in idx_order for c in target_cols]
            out: list[tuple[object, str, str]] = []
            for dr, row_vals in enumerate(grid):
                if dr >= len(idx_order):
                    break
                r = idx_order[dr]
                for dc, c in enumerate(target_cols):
                    if dc >= len(row_vals):
                        break
                    out.append((r, c, row_vals[dc]))
            return out

        if mode in {"row", "rows"} and self._selection.rows:
            target_rows = self._sorted_row_indices(self._selection.rows)
            if single_value:
                return [(r, c, one) for r in target_rows for c in col_order]
            out = []
            for dr, r in enumerate(target_rows):
                if dr >= rows_h:
                    break
                row_vals = grid[dr]
                for dc, c in enumerate(col_order):
                    if dc >= len(row_vals):
                        break
                    out.append((r, c, row_vals[dc]))
            return out

        if mode == "cell" and self._selection.cells:
            if single_value:
                return [(r, c, one) for r, c in self._selection.cells]
            sel_rows = self._sorted_row_indices({r for r, _ in self._selection.cells})
            sel_cols = self._sorted_columns({c for _, c in self._selection.cells})
            return self._assignments_at_anchor(sel_rows[0], sel_cols[0], grid)

        anchor = self._paste_anchor()
        if anchor is None:
            return []
        return self._assignments_at_anchor(anchor[0], anchor[1], grid)

    def _on_copy(self) -> None:
        if self._df is None or self._table.state() == self._table.State.EditingState:
            return
        grid = self._copy_grid()
        if not grid:
            return
        QGuiApplication.clipboard().setText(self._grid_to_clipboard_text(grid))

    def _on_paste(self) -> None:
        if self._df is None or self._table.state() == self._table.State.EditingState:
            return
        text = QGuiApplication.clipboard().text()
        grid = self._parse_clipboard_grid(text)
        anchor = self._paste_anchor()
        if anchor is not None:
            self._ensure_paste_fits(grid, anchor)
        assignments = self._build_paste_assignments(grid)
        if not assignments:
            return
        from df_tool.operations import paste_cells

        scroll = self._save_scroll()
        prior_mode = self._selection.mode
        prior_columns = set(self._selection.columns) if self._selection.columns else set()
        prior_rows = set(self._selection.rows) if self._selection.rows else set()

        self._preserve_scroll = True
        try:
            self._apply_df(paste_cells(self._df, assignments), action="붙여넣기", restructure=False)
            rows = self._sorted_row_indices({r for r, _, _ in assignments})
            cols = self._sorted_columns({c for _, c, _ in assignments})
            anchor = (rows[0], cols[0])

            if prior_mode in {"column", "columns"} and prior_columns:
                if len(prior_columns) == 1:
                    self._select_column(next(iter(prior_columns)))
                else:
                    self._selection = SelectionScope(
                        mode="columns",
                        columns=prior_columns,
                        anchor_column=cols[0],
                    )
                    self._update_selection_label()
            elif prior_mode in {"row", "rows"} and prior_rows:
                if len(prior_rows) == 1:
                    self._select_row(next(iter(prior_rows)))
                else:
                    self._selection = SelectionScope(
                        mode="rows",
                        rows=prior_rows,
                        anchor_row=rows[0],
                    )
                    self._update_selection_label()
            elif len(assignments) == 1:
                self._selection = SelectionScope(mode="cell", cells={anchor}, anchor_cell=anchor)
                self._active_cell = anchor
                self._selection_ctrl.select_cell(
                    self._table.selectionModel(),
                    anchor[0],
                    anchor[1],
                )
            else:
                pasted_cells = {(r, c) for r, c, _ in assignments}
                self._selection = SelectionScope(
                    mode="cell",
                    cells=pasted_cells,
                    anchor_cell=anchor,
                )
                self._active_cell = anchor
                self._selection_ctrl.select_cell(
                    self._table.selectionModel(),
                    anchor[0],
                    anchor[1],
                )
        finally:
            self._preserve_scroll = False
            self._restore_scroll(*scroll)
            self._update_selection_label()

    def _delete_selected_rows(self) -> None:
        if self._df is None:
            return
        indices = self._selection.row_indices()
        if not indices:
            self._emit_error("행 삭제", "삭제할 행을 선택하세요.")
            return
        n = len(indices)
        reply = QMessageBox.question(
            self,
            "행 삭제",
            f"선택한 행 {n}개를 삭제할까요?\n\n되돌리려면 Ctrl+Z를 사용하세요.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from df_tool.operations import delete_rows, resolve_index_keys

        keys = resolve_index_keys(self._df, indices)
        new_df = delete_rows(self._df, indices)
        if len(new_df) == len(self._df):
            self._emit_error("행 삭제", "선택한 행을 삭제하지 못했습니다.")
            return
        self._apply_df(new_df, action=f"행 {n}개 삭제" if n > 1 else "행 삭제", restructure=True)
        self._selection = SelectionScope()
        self._table.clearSelection()

    def _insert_row_at_selection(self, position: str) -> None:
        if self._df is None:
            return
        if not self._df.index.size:
            from df_tool.operations import insert_row_at_end
            from df_tool.qt_dialogs import qt_insert_row_dialog

            result = qt_insert_row_dialog(
                self,
                position_label="표 끝에 빈 행을 추가합니다.",
            )
            if not result:
                return
            self._apply_df(insert_row_at_end(self._df, count=result), action="행 추가", restructure=True)
            return
        ref = (
            next(iter(self._selection.rows))
            if self._selection.rows
            else (self._active_cell[0] if self._active_cell else self._df.index[0])
        )
        try:
            new_df = insert_row_with_dialog(self._df, ref, position, parent=self)
        except Exception as exc:
            self._emit_error("행 추가", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action="행 추가", restructure=True)

    def _insert_column_at_selection(self, position: str) -> None:
        if self._df is None or not len(self._df.columns):
            return
        if self._selection.columns:
            ref = next(iter(self._selection.columns))
        elif self._active_cell:
            ref = self._active_cell[1]
        else:
            ref = self._df.columns[0]
        try:
            new_df = insert_column_with_dialog(self._df, ref, position, parent=self)
        except ValueError as exc:
            self._emit_error("열 추가", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action="열 추가", restructure=True)
        self._refresh_search_columns()

    def _insert_row(self, reference_index, position: str) -> None:
        try:
            new_df = insert_row_with_dialog(self._df, reference_index, position, parent=self)
        except Exception as exc:
            self._emit_error("행 추가", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action="행 추가", restructure=True)

    def _insert_column(self, reference_column, position: str) -> None:
        try:
            new_df = insert_column_with_dialog(self._df, reference_column, position, parent=self)
        except ValueError as exc:
            self._emit_error("열 추가", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action="열 추가", restructure=True)
        self._refresh_search_columns()

    def _rename_column(self, column) -> None:
        try:
            new_df = rename_column_with_dialog(self._df, column, parent=self)
        except Exception as exc:
            self._emit_error("열 이름 변경", str(exc))
            return
        if new_df is None:
            return
        from df_tool.operations import resolve_column_key

        old_key = resolve_column_key(self._df, column)
        if self._sort_column is not None and old_key is not None and str(self._sort_column) == str(old_key):
            new_cols = list(new_df.columns)
            for c in new_cols:
                if str(c) != str(old_key):
                    self._sort_column = c
                    break
        self._apply_df(new_df, action="열 이름 변경", restructure=True)

    def _duplicate_column(self, column) -> None:
        try:
            new_df = duplicate_column_with_dialog(self._df, column, parent=self)
        except ValueError as exc:
            self._emit_error("열 복제", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action="열 복제", restructure=True)
        self._refresh_search_columns()

    def _trigger_fill_na_column(self, column: str) -> None:
        if self.on_fill_na_column:
            self.on_fill_na_column(column)

    def _split_column(self, column) -> None:
        if self._df is None:
            return
        try:
            new_df = split_column_with_dialog(self._df, column, parent=self)
        except ValueError as exc:
            self._emit_error("열 분리 실패", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action=f"열 '{column}' 분리", restructure=True)
        self._refresh_search_columns()
        self._selection = SelectionScope()
        self._table.clearSelection()

    def _merge_selected_columns(self) -> None:
        if self._df is None or not self._has_column_selection():
            return
        columns = self._sorted_columns(self._selection.columns)
        if len(columns) < 2:
            self._emit_error("열 병합", "Ctrl+클릭으로 열을 2개 이상 선택하세요.")
            return
        try:
            new_df = merge_columns_with_dialog(self._df, columns, parent=self)
        except ValueError as exc:
            self._emit_error("열 병합 실패", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action=f"열 병합 ({len(columns)}개)", restructure=True)
        self._refresh_search_columns()
        self._selection = SelectionScope()
        self._table.clearSelection()

    def _fill_column(self, column, method: str) -> None:
        try:
            new_df = fill_column_with_dialog(self._df, column, method, parent=self)
        except Exception as exc:
            self._emit_error("열 채우기", str(exc))
            return
        if new_df is None:
            return
        label = "위로 채우기" if method == "ffill" else "아래로 채우기"
        self._apply_df(new_df, action=label, restructure=False)

    def _fill_sequential(self, column) -> None:
        try:
            new_df = fill_sequential_with_dialog(self._df, column, parent=self)
        except Exception as exc:
            self._emit_error("순차 번호", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action="순차 번호 채우기", restructure=False)

    def _delete_column(self, column) -> None:
        try:
            new_df = delete_column_with_dialog(self._df, column, parent=self)
        except ValueError as exc:
            self._emit_error("열 삭제", str(exc))
            return
        if new_df is None:
            return
        if self._sort_column == column:
            self._sort_column = None
        self._apply_df(new_df, action=f"열 '{column}' 삭제", restructure=True)
        self._refresh_search_columns()
        self._selection = SelectionScope()
        self._table.clearSelection()

    def _delete_selected_columns(self) -> None:
        if self._df is None:
            return
        columns = self._sorted_columns(set(self._selection.columns))
        if not columns and self._active_cell:
            columns = [self._active_cell[1]]
        if not columns:
            return
        try:
            new_df = delete_columns_with_dialog(self._df, columns, parent=self)
        except ValueError as exc:
            self._emit_error("열 삭제", str(exc))
            return
        if new_df is None:
            return
        self._apply_df(new_df, action=f"열 {len(columns)}개 삭제", restructure=True)
        self._refresh_search_columns()
        self._selection = SelectionScope()
        self._table.clearSelection()

    def _copy_column(self, column) -> None:
        if self._df is None:
            return
        lines = [raw_value(v) for v in self._df[column].tolist()]
        QGuiApplication.clipboard().setText("\n".join(lines))

    def _select_all(self) -> None:
        if self._df is None or not self._index_list() or not self._column_list():
            return
        rows = self._index_list()
        cols = self._column_list()
        self._selection_ctrl.select_range(
            self._table.selectionModel(),
            (rows[0], cols[0]),
            (rows[-1], cols[-1]),
        )
        self._on_selection_changed()

    def _select_column_shortcut(self) -> None:
        if self._active_cell:
            self._select_column(self._active_cell[1])
        elif self._column_list():
            self._select_column(self._column_list()[0])

    def _select_row_shortcut(self) -> None:
        if self._active_cell:
            self._select_row(self._active_cell[0])
        elif self._index_list():
            self._select_row(self._index_list()[0])

    def _on_restore_original(self) -> None:
        if self._restore_callback:
            self._restore_callback()

    @staticmethod
    def _header_section_at(header, pos) -> int:
        section = header.logicalIndexAt(pos)
        if section >= 0:
            return section
        if header.orientation() == Qt.Orientation.Horizontal:
            section = header.sectionAt(pos.x())
        else:
            section = header.sectionAt(pos.y())
        if section >= 0:
            return section
        if header.orientation() == Qt.Orientation.Horizontal:
            x = pos.x()
            for logical in range(header.count()):
                visual = header.visualIndex(logical)
                left = header.sectionPosition(visual)
                if left <= x < left + header.sectionSize(visual):
                    return logical
        return -1

    def _has_column_selection(self) -> bool:
        return self._selection.mode in {"column", "columns"} and bool(self._selection.columns)

    def _column_menu_target(self, clicked_column: str | None) -> str | None:
        if not self._has_column_selection():
            return clicked_column
        if clicked_column is not None and clicked_column in self._selection.columns:
            return clicked_column
        ordered = self._sorted_columns(self._selection.columns)
        return ordered[0] if ordered else clicked_column

    def _ensure_column_context_selection(self, column: str) -> None:
        if self._has_column_selection() and column in self._selection.columns:
            return
        self._select_column(column)

    def _popup_column_menu(self, column: str, global_pos: QPoint) -> None:
        if self._df is None:
            return
        menu = QMenu(self)
        menu.addAction("▲ 오름차순 정렬", lambda: self.sort_by(column, True))
        menu.addAction("▼ 내림차순 정렬", lambda: self.sort_by(column, False))
        menu.addSeparator()
        menu.addAction("열 전체 선택", lambda: self._select_column(column))
        if self._has_column_selection() and len(self._selection.columns) >= 2:
            n_merge = len(self._selection.columns)
            menu.addAction(
                f"선택 열 {n_merge}개 병합…",
                lambda: self._defer_action(self._merge_selected_columns),
            )
        menu.addAction(
            "열 이름 변경…",
            lambda: self._defer_action(self._rename_column, column),
        )
        menu.addAction(
            "열 복제",
            lambda: self._defer_action(self._duplicate_column, column),
        )
        menu.addAction(
            "열 분리…",
            lambda: self._defer_action(self._split_column, column),
        )
        menu.addSeparator()
        menu.addAction(
            "◀ 왼쪽에 열 추가",
            lambda: self._defer_action(self._insert_column, column, "left"),
        )
        menu.addAction(
            "▶ 오른쪽에 열 추가",
            lambda: self._defer_action(self._insert_column, column, "right"),
        )
        menu.addSeparator()
        from df_tool.operations import count_nulls, resolve_column_key

        col_key = resolve_column_key(self._df, column)
        if col_key is not None and count_nulls(self._df[col_key]) > 0 and self.on_fill_na_column:
            menu.addAction(
                "결측치 채우기…",
                lambda: self._defer_action(self._trigger_fill_na_column, column),
            )
            menu.addSeparator()
        menu.addAction(
            "위로 채우기 (빈칸)",
            lambda: self._defer_action(self._fill_column, column, "ffill"),
        )
        menu.addAction(
            "아래로 채우기 (빈칸)",
            lambda: self._defer_action(self._fill_column, column, "bfill"),
        )
        menu.addAction(
            "순차 번호 채우기 (간격)…",
            lambda: self._defer_action(self._fill_sequential, column),
        )
        menu.addSeparator()
        menu.addAction("열 복사", lambda: self._copy_column(column))
        n_cols = len(self._selection.columns) if self._has_column_selection() else 1
        menu.addAction(
            f"선택 열 {n_cols}개 삭제" if n_cols > 1 else "열 삭제",
            lambda: self._defer_action(self._delete_selected_columns),
        )
        menu.addSeparator()
        menu.addAction("복사 (Ctrl+C)", self._on_copy)
        menu.addAction("붙여넣기 (Ctrl+V)", self._on_paste)
        menu.exec(global_pos)


    def _show_column_header_menu(self, pos) -> None:
        header = self._table.horizontalHeader()
        section = self._header_section_at(header, pos)
        column = self._model.column_name_at(section)
        if column is None or self._df is None:
            return
        self._ensure_column_context_selection(column)
        self._popup_column_menu(column, header.mapToGlobal(pos))

    def _show_row_header_menu(self, pos) -> None:
        header = self._table.verticalHeader()
        section = self._header_section_at(header, pos)
        src = self._model.source_index_at(section)
        if src is None or self._df is None:
            return
        menu = QMenu(self)
        menu.addAction(
            "▲ 위에 행 추가",
            lambda: self._defer_action(self._insert_row, src, "above"),
        )
        menu.addAction(
            "▼ 아래에 행 추가",
            lambda: self._defer_action(self._insert_row, src, "below"),
        )
        menu.addSeparator()
        n = len(self._selection.rows) if self._selection.rows else 1
        menu.addAction(
            f"선택 행 {n}개 삭제" if n > 1 else "행 삭제",
            lambda: self._defer_action(self.delete_selected_rows),
        )
        menu.addSeparator()
        menu.addAction("복사 (Ctrl+C)", self._on_copy)
        menu.addAction("붙여넣기 (Ctrl+V)", self._on_paste)
        menu.exec(header.mapToGlobal(pos))

    def _show_context_menu(self, pos) -> None:
        if self._df is None:
            return
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        src = self._model.source_index_at(index.row())
        col = self._model.column_name_at(index.column())
        if src is None or col is None:
            return
        global_pos = self._table.viewport().mapToGlobal(pos)

        if self._has_column_selection():
            menu_col = self._column_menu_target(col)
            if menu_col is not None:
                self._popup_column_menu(menu_col, global_pos)
                return

        if self._selection.mode in {"row", "rows"} and src in (self._selection.rows or set()):
            self._popup_row_menu(src, global_pos)
            return

        if self._selection.mode not in {"row", "rows"} or src not in (self._selection.rows or set()):
            self._selection_ctrl.select_cell(
                self._table.selectionModel(),
                src,
                col,
            )
            self._active_cell = (src, col)
        self._popup_row_menu(src, global_pos)

    def _popup_row_menu(self, source_index: object, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction("셀 편집 (F2)", lambda: self._table.edit(self._table.currentIndex()))
        menu.addSeparator()
        menu.addAction("행 전체 선택", lambda: self._select_row(source_index))
        menu.addAction(
            "▲ 위에 행 추가",
            lambda: self._defer_action(self._insert_row, source_index, "above"),
        )
        menu.addAction(
            "▼ 아래에 행 추가",
            lambda: self._defer_action(self._insert_row, source_index, "below"),
        )
        menu.addSeparator()
        n = len(self._selection.rows) if self._selection.rows else 1
        menu.addAction(
            f"선택 행 {n}개 삭제" if n > 1 else "행 삭제",
            lambda: self._defer_action(self.delete_selected_rows),
        )
        menu.addSeparator()
        menu.addAction("복사 (Ctrl+C)", self._on_copy)
        menu.addAction("붙여넣기 (Ctrl+V)", self._on_paste)
        menu.exec(global_pos)
