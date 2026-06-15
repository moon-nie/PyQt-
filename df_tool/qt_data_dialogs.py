"""PyQt 데이터 처리 다이얼로그 — VLOOKUP, 조인, 병합, 그룹 요약."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from df_tool.analysis import knn_fill_preview
from df_tool.analysis_deps import feature_requirement_message, sklearn_available
from df_tool.loader import FILE_DIALOG_TYPES, load_file
from df_tool.operations import (
    FILL_NA_METHOD_LABELS,
    column_fill_na_methods,
    column_supports_numeric_fill,
    compute_fill_na_scalar,
    concat_dataframes,
    count_nulls,
    merge_dataframes,
    resolve_column_key,
    vlookup,
    vlookup_stats,
)
from df_tool.qt_dialogs import _QtFormDialog, _dialog_stylesheet
from df_tool.theme import COLORS

_PREVIEW_ROWS = 50
_PREVIEW_COLS = 12


def _cell_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _preview_columns(df: pd.DataFrame) -> list[str]:
    cols = [str(c) for c in df.columns[:_PREVIEW_COLS]]
    if len(df.columns) > _PREVIEW_COLS:
        cols.append(f"… 외 {len(df.columns) - _PREVIEW_COLS}열")
    return cols


def _fill_table(table: QTableWidget, df: pd.DataFrame, columns: list[str]) -> None:
    table.clear()
    if not columns:
        table.setRowCount(0)
        table.setColumnCount(0)
        return
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setRowCount(len(df))
    for row_idx, (_, row) in enumerate(df.iterrows()):
        for col_idx, col in enumerate(columns):
            table.setItem(row_idx, col_idx, QTableWidgetItem(_cell_text(row.get(col))))
    table.resizeColumnsToContents()


def _prompt_load_reference(parent, title: str = "참조 파일 선택"):
    """파일 선택 다이얼로그 → load_file. 취소/실패 시 None(실패는 경고 표시).

    VLOOKUP·조인·병합이 공유하는 참조 파일 로드 보일러플레이트.
    """
    filters = ";;".join(f"{label} ({pat})" for label, pat in FILE_DIALOG_TYPES)
    path, _ = QFileDialog.getOpenFileName(parent, title, "", filters)
    if not path:
        return None
    try:
        return load_file(Path(path))
    except Exception as exc:
        QMessageBox.critical(parent, "파일 열기 실패", str(exc))
        return None


def _set_ref_file_label(label, loaded) -> None:
    """불러온 참조 파일 정보를 라벨에 '이름 (n행 × m열)' 형식으로 표시."""
    df = loaded.dataframe
    label.setText(f"{loaded.path.name}  ({len(df):,}행 × {len(df.columns)}열)")
    label.setStyleSheet(f"color: {COLORS['text']};")


class QtVLookupDialog(QDialog):
    """VLOOKUP — 참조 파일 불러오기·설정·미리보기."""

    def __init__(
        self,
        parent: QWidget | None,
        left_columns: list[str],
        current_df: pd.DataFrame,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("VLOOKUP — 값 찾아오기")
        self.setModal(True)
        self.resize(860, 600)
        self.setMinimumSize(760, 520)
        self._current_df = current_df
        self._ref_df: pd.DataFrame | None = None
        self._result: tuple[pd.DataFrame, str, str, str, str] | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)
        self._left_columns = left_columns
        self._build_ui(left_columns)
        self.setStyleSheet(_dialog_stylesheet())

    def _build_ui(self, left_columns: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        hint = QLabel("참조 파일을 불러온 뒤 키 열·가져올 열을 설정하고 미리보기로 확인하세요.")
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        left_layout.addWidget(QLabel("현재 표 키 열:"))
        self.left_key = QComboBox()
        self.left_key.addItems(left_columns)
        left_layout.addWidget(self.left_key)

        file_row = QHBoxLayout()
        self.file_label = QLabel("(파일 없음)")
        self.file_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        file_row.addWidget(self.file_label, stretch=1)
        load_btn = QPushButton("불러오기…")
        load_btn.clicked.connect(self._load_reference)
        file_row.addWidget(load_btn)
        left_layout.addWidget(QLabel("참조 파일:"))
        left_layout.addLayout(file_row)

        left_layout.addWidget(QLabel("참조 파일 키 열:"))
        self.right_key = QComboBox()
        left_layout.addWidget(self.right_key)

        left_layout.addWidget(QLabel("가져올 열:"))
        self.return_col = QComboBox()
        left_layout.addWidget(self.return_col)

        left_layout.addWidget(QLabel("결과 열 이름:"))
        self.new_name = QLineEdit()
        left_layout.addWidget(self.new_name)
        left_layout.addStretch()
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        self.stats_label = QLabel("참조 파일과 열을 설정하면 미리보기가 표시됩니다.")
        self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.stats_label.setWordWrap(True)
        right_layout.addWidget(self.stats_label)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.preview_table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=1)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("미리보기 새로고침")
        refresh_btn.clicked.connect(self._update_preview)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("적용")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        layout.addLayout(btn_row)

        for combo in (self.left_key, self.right_key):
            combo.currentTextChanged.connect(self._schedule_preview)
        self.return_col.currentTextChanged.connect(self._on_return_col_changed)
        self.new_name.textChanged.connect(self._schedule_preview)

    def _load_reference(self) -> None:
        loaded = _prompt_load_reference(self)
        if loaded is None:
            return
        self._ref_df = loaded.dataframe
        cols = [str(c) for c in self._ref_df.columns]
        _set_ref_file_label(self.file_label, loaded)
        self.right_key.clear()
        self.return_col.clear()
        self.right_key.addItems(cols)
        self.return_col.addItems(cols)
        if cols:
            self.right_key.setCurrentIndex(0)
            key_name = cols[0]
            others = [c for c in cols if c != key_name]
            pick = others[0] if others else cols[0]
            pick_idx = cols.index(pick)
            self.return_col.setCurrentIndex(pick_idx)
            self._suggest_output_name(pick)
        self._schedule_preview()

    def _suggest_output_name(self, return_col: str) -> None:
        if return_col == self.right_key.currentText().strip() and return_col in self._left_columns:
            suggested = f"{return_col}_참조"
        elif return_col in self._left_columns:
            suggested = f"{return_col}_참조"
        else:
            suggested = return_col
        if not self.new_name.text().strip() or self.new_name.text().strip() in self._left_columns:
            self.new_name.setText(suggested)

    def _on_return_col_changed(self, _text: str = "") -> None:
        self._suggest_output_name(self.return_col.currentText().strip())
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        self._preview_timer.start(300)

    def _get_config(self) -> tuple[str, str, str, str] | None:
        if self._ref_df is None:
            return None
        left_key = self.left_key.currentText().strip()
        right_key = self.right_key.currentText().strip()
        return_col = self.return_col.currentText().strip()
        new_name = self.new_name.text().strip() or return_col
        if not all([left_key, right_key, return_col]):
            return None
        return left_key, right_key, return_col, new_name

    def _update_preview(self) -> None:
        config = self._get_config()
        if not config:
            self.stats_label.setText("참조 파일과 열을 설정하면 미리보기가 표시됩니다.")
            self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        left_key, right_key, return_col, new_name = config
        if return_col == right_key:
            self.stats_label.setText("가져올 열은 키 열(상품명 등)과 다른 열을 선택하세요.")
            self.stats_label.setStyleSheet(f"color: {COLORS['warning']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        try:
            sample = self._current_df.head(_PREVIEW_ROWS)
            stats = vlookup_stats(sample, self._ref_df, left_key, right_key, return_col, new_name)
            preview_df = vlookup(sample, self._ref_df, left_key, right_key, return_col, new_name)
        except Exception as exc:
            self.stats_label.setText(f"미리보기 오류: {exc}")
            self.stats_label.setStyleSheet(f"color: {COLORS['danger']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        self.stats_label.setText(
            f"미리보기 {min(len(self._current_df), _PREVIEW_ROWS):,}행 기준 · "
            f"매칭 {stats['matched']:,} · 미매칭 {stats['unmatched']:,} · "
            f"전체 {stats['total']:,}행"
        )
        self.stats_label.setStyleSheet(f"color: {COLORS['text']};")
        show_cols = [left_key]
        if new_name in preview_df.columns and new_name not in show_cols:
            show_cols.append(new_name)
        _fill_table(self.preview_table, preview_df, show_cols)

    def _apply(self) -> None:
        if self._ref_df is None:
            QMessageBox.warning(self, "입력 오류", "참조 파일을 불러오세요.")
            return
        config = self._get_config()
        if not config:
            QMessageBox.warning(self, "입력 오류", "모든 항목을 선택하세요.")
            return
        left_key, right_key, return_col, new_name = config
        if return_col == right_key:
            QMessageBox.warning(self, "입력 오류", "가져올 열은 키 열과 다른 열을 선택하세요.")
            return
        try:
            vlookup(self._current_df.head(1), self._ref_df, left_key, right_key, return_col, new_name)
        except Exception as exc:
            QMessageBox.critical(self, "설정 오류", str(exc))
            return
        self._result = (self._ref_df, left_key, right_key, return_col, new_name)
        self.accept()

    def get_result(self) -> tuple[pd.DataFrame, str, str, str, str] | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._result


_JOIN_TYPES = [
    ("inner", "내부 조인 — 양쪽 모두 있는 키만"),
    ("left", "왼쪽 조인 — 현재 표 기준"),
    ("right", "오른쪽 조인 — 참조 파일 기준"),
    ("outer", "외부 조인 — 전체 합집합"),
]

_AGG_OPTIONS = [
    ("count", "count (개수)"),
    ("sum", "sum (합계)"),
    ("mean", "mean (평균)"),
    ("min", "min (최소)"),
    ("max", "max (최대)"),
]


class QtMergeDialog(QDialog):
    """조인 — 참조 파일 불러오기·키 열 설정·미리보기."""

    def __init__(
        self,
        parent: QWidget | None,
        left_columns: list[str],
        current_df: pd.DataFrame,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("파일 조인 (Merge)")
        self.setModal(True)
        self.resize(860, 600)
        self.setMinimumSize(760, 520)
        self._current_df = current_df
        self._ref_df: pd.DataFrame | None = None
        self._result: tuple[pd.DataFrame, str, str, str] | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)
        self._build_ui(left_columns)
        self.setStyleSheet(_dialog_stylesheet())

    def _build_ui(self, left_columns: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        hint = QLabel("참조 파일을 불러온 뒤 키 열·조인 방식을 설정하고 미리보기로 확인하세요.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        file_row = QHBoxLayout()
        self.file_label = QLabel("(파일 없음)")
        self.file_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        file_row.addWidget(self.file_label, stretch=1)
        load_btn = QPushButton("불러오기…")
        load_btn.clicked.connect(self._load_reference)
        file_row.addWidget(load_btn)
        left_layout.addWidget(QLabel("참조 파일:"))
        left_layout.addLayout(file_row)

        left_layout.addWidget(QLabel("현재 표 키 열:"))
        self.left_on = QComboBox()
        self.left_on.addItems(left_columns)
        left_layout.addWidget(self.left_on)

        left_layout.addWidget(QLabel("참조 파일 키 열:"))
        self.right_on = QComboBox()
        left_layout.addWidget(self.right_on)

        left_layout.addWidget(QLabel("조인 방식:"))
        self.how_combo = QComboBox()
        self.how_combo.addItems([label for _, label in _JOIN_TYPES])
        left_layout.addWidget(self.how_combo)
        left_layout.addStretch()
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        self.stats_label = QLabel("참조 파일과 키 열을 설정하면 미리보기가 표시됩니다.")
        self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.stats_label.setWordWrap(True)
        right_layout.addWidget(self.stats_label)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.preview_table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=1)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("미리보기 새로고침")
        refresh_btn.clicked.connect(self._update_preview)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("조인")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        layout.addLayout(btn_row)

        for combo in (self.left_on, self.right_on):
            combo.currentTextChanged.connect(self._schedule_preview)
        self.how_combo.currentTextChanged.connect(self._schedule_preview)

    def _schedule_preview(self) -> None:
        self._preview_timer.start(300)

    def _get_config(self) -> tuple[str, str, str] | None:
        if self._ref_df is None:
            return None
        left_key = self.left_on.currentText().strip()
        right_key = self.right_on.currentText().strip()
        how_label = self.how_combo.currentText().strip()
        if not all([left_key, right_key]):
            return None
        how = next(code for code, label in _JOIN_TYPES if label == how_label)
        return left_key, right_key, how

    def _update_preview(self) -> None:
        config = self._get_config()
        if not config:
            self.stats_label.setText("참조 파일과 키 열을 설정하면 미리보기가 표시됩니다.")
            self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        left_key, right_key, how = config
        try:
            left_sample = self._current_df.head(_PREVIEW_ROWS)
            right_sample = self._ref_df.head(_PREVIEW_ROWS)
            preview_df = merge_dataframes(
                left_sample, right_sample, left_key, right_key, how=how
            )
        except Exception as exc:
            self.stats_label.setText(f"미리보기 오류: {exc}")
            self.stats_label.setStyleSheet(f"color: {COLORS['danger']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        self.stats_label.setText(
            f"미리보기 상위 {_PREVIEW_ROWS}행 기준 · "
            f"{len(preview_df):,}행 × {len(preview_df.columns)}열 · "
            f"현재 표 {len(self._current_df):,}행 + 참조 {len(self._ref_df):,}행"
        )
        self.stats_label.setStyleSheet(f"color: {COLORS['text']};")
        show_cols = _preview_columns(preview_df)
        real_cols = [c for c in show_cols if not c.startswith("…")]
        _fill_table(self.preview_table, preview_df, real_cols)

    def _load_reference(self) -> None:
        loaded = _prompt_load_reference(self)
        if loaded is None:
            return
        self._ref_df = loaded.dataframe
        cols = [str(c) for c in self._ref_df.columns]
        _set_ref_file_label(self.file_label, loaded)
        self.right_on.clear()
        self.right_on.addItems(cols)
        if cols:
            self.right_on.setCurrentIndex(0)
        self._schedule_preview()

    def _apply(self) -> None:
        if self._ref_df is None:
            QMessageBox.warning(self, "입력 오류", "참조 파일을 불러오세요.")
            return
        left_key = self.left_on.currentText().strip()
        right_key = self.right_on.currentText().strip()
        how_label = self.how_combo.currentText().strip()
        how = next(code for code, label in _JOIN_TYPES if label == how_label)
        if not all([left_key, right_key]):
            QMessageBox.warning(self, "입력 오류", "키 열을 선택하세요.")
            return
        self._result = (self._ref_df, left_key, right_key, how)
        self.accept()

    def get_result(self) -> tuple[pd.DataFrame, str, str, str] | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._result


class QtConcatDialog(QDialog):
    """세로 병합 — 현재 표 + 참조 파일 선택·미리보기."""

    def __init__(self, parent: QWidget | None, current_df: pd.DataFrame) -> None:
        super().__init__(parent)
        self.setWindowTitle("파일 세로 병합 (Concat)")
        self.setModal(True)
        self.resize(860, 600)
        self.setMinimumSize(760, 520)
        self._current_df = current_df
        self._items: list[tuple[str, pd.DataFrame | None]] = []
        self._result: list[pd.DataFrame] | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)
        self._build_ui()
        self.setStyleSheet(_dialog_stylesheet())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint = QLabel(
            "병합할 표를 선택하세요. [파일 추가]로 참조 파일을 불러올 수 있습니다.\n"
            "열 이름이 같으면 같은 열로 합쳐집니다."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("파일 추가…")
        add_btn.clicked.connect(self._add_file)
        remove_btn = QPushButton("선택 제거")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        left_layout.addLayout(btn_row)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._items.append(("(현재 표)", None))
        self.list_widget.addItem("(현재 표)")
        self.list_widget.item(0).setSelected(True)
        self.list_widget.itemSelectionChanged.connect(self._schedule_preview)
        left_layout.addWidget(self.list_widget)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        self.stats_label = QLabel("병합할 항목을 선택하면 미리보기가 표시됩니다.")
        self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.stats_label.setWordWrap(True)
        right_layout.addWidget(self.stats_label)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.preview_table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        bottom = QHBoxLayout()
        refresh_btn = QPushButton("미리보기 새로고침")
        refresh_btn.clicked.connect(self._update_preview)
        bottom.addWidget(refresh_btn)
        bottom.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("병합")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        self._preview_timer.start(300)

    def _selected_dataframes(self) -> list[pd.DataFrame]:
        selected = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()})
        dfs: list[pd.DataFrame] = []
        for idx in selected:
            if idx >= len(self._items):
                continue
            _, df = self._items[idx]
            if df is None:
                dfs.append(self._current_df)
            else:
                dfs.append(df)
        return dfs

    def _update_preview(self) -> None:
        dfs = self._selected_dataframes()
        if not dfs:
            self.stats_label.setText("병합할 항목을 하나 이상 선택하세요.")
            self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        try:
            samples = [df.head(_PREVIEW_ROWS) for df in dfs]
            preview_df = concat_dataframes(samples)
            total_rows = sum(len(df) for df in dfs)
            all_cols = list(dict.fromkeys(str(c) for df in dfs for c in df.columns))
        except Exception as exc:
            self.stats_label.setText(f"미리보기 오류: {exc}")
            self.stats_label.setStyleSheet(f"color: {COLORS['danger']};")
            _fill_table(self.preview_table, pd.DataFrame(), [])
            return
        self.stats_label.setText(
            f"예상 {total_rows:,}행 × {len(all_cols)}열 · "
            f"미리보기 각 표 상위 {_PREVIEW_ROWS}행"
        )
        self.stats_label.setStyleSheet(f"color: {COLORS['text']};")
        show_cols = _preview_columns(preview_df)
        real_cols = [c for c in show_cols if not c.startswith("…")]
        _fill_table(self.preview_table, preview_df, real_cols)

    def _add_file(self) -> None:
        loaded = _prompt_load_reference(self, "병합할 파일 선택")
        if loaded is None:
            return
        name = loaded.path.name
        label = f"{name} ({len(loaded.dataframe):,}행)"
        self._items.append((label, loaded.dataframe))
        self.list_widget.addItem(label)
        self.list_widget.item(self.list_widget.count() - 1).setSelected(True)
        self._schedule_preview()

    def _remove_selected(self) -> None:
        rows = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()}, reverse=True)
        for idx in rows:
            if idx <= 0:
                continue
            self.list_widget.takeItem(idx)
            if idx < len(self._items):
                self._items.pop(idx)
        self._schedule_preview()

    def _apply(self) -> None:
        selected = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()})
        if not selected:
            QMessageBox.warning(self, "입력 오류", "병합할 항목을 선택하세요.")
            return
        dfs: list[pd.DataFrame] = []
        for idx in selected:
            if idx >= len(self._items):
                continue
            _, df = self._items[idx]
            if df is None:
                dfs.append(self._current_df)
            else:
                dfs.append(df)
        if not dfs:
            QMessageBox.warning(self, "입력 오류", "병합할 데이터가 없습니다.")
            return
        self._result = dfs
        self.accept()

    def get_result(self) -> list[pd.DataFrame] | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._result


def qt_merge_dialog(
    parent: QWidget | None,
    left_columns: list[str],
    current_df: pd.DataFrame,
) -> tuple[pd.DataFrame, str, str, str] | None:
    return QtMergeDialog(parent, left_columns, current_df).get_result()


def qt_concat_dialog(
    parent: QWidget | None,
    current_df: pd.DataFrame,
) -> list[pd.DataFrame] | None:
    return QtConcatDialog(parent, current_df).get_result()


def qt_group_summary_dialog(
    parent: QWidget | None,
    columns: list[str],
) -> tuple[str, str, str] | None:
    dlg = _QtFormDialog(parent, "그룹 요약", confirm_text="적용", min_width=460)
    hint = QLabel(
        "그룹별로 집계한 요약 표로 전환됩니다.\n"
        "적용 후 [원본 복원] 또는 Ctrl+Z로 되돌릴 수 있습니다."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
    dlg._layout.addWidget(hint)

    dlg._layout.addWidget(QLabel("그룹 기준 열:"))
    group_combo = QComboBox()
    group_combo.addItems(columns)
    dlg._layout.addWidget(group_combo)

    dlg._layout.addWidget(QLabel("집계 대상 열:"))
    value_combo = QComboBox()
    value_combo.addItems(columns)
    dlg._layout.addWidget(value_combo)

    dlg._layout.addWidget(QLabel("집계 방식:"))
    agg_combo = QComboBox()
    agg_combo.addItems([label for _, label in _AGG_OPTIONS])
    dlg._layout.addWidget(agg_combo)
    dlg._layout.addWidget(dlg._buttons)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    group_col = group_combo.currentText().strip()
    value_col = value_combo.currentText().strip()
    agg_label = agg_combo.currentText().strip()
    agg = agg_label.split()[0]
    if not group_col or not value_col:
        QMessageBox.warning(parent, "입력 오류", "열을 선택하세요.")
        return None
    return group_col, value_col, agg


def qt_vlookup_dialog(
    parent: QWidget | None,
    left_columns: list[str],
    current_df: pd.DataFrame,
) -> tuple[pd.DataFrame, str, str, str, str] | None:
    return QtVLookupDialog(parent, left_columns, current_df).get_result()


class QtFillNaDialog(QDialog):
    """결측치 채우기 — 숫자 열은 평균·중앙값 등 통계 방식 지원."""

    def __init__(
        self,
        parent: QWidget | None,
        df: pd.DataFrame,
        column: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("결측치 채우기")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._df = df
        self._column = column
        self._result: tuple[str, str | None, int | None] | None = None
        key = resolve_column_key(df, column)
        if key is None:
            raise ValueError(f"열 '{column}'이(가) 없습니다.")
        self._key = key
        self._series = df[key]
        self._methods = column_fill_na_methods(self._series)
        self._build_ui()
        self.setStyleSheet(_dialog_stylesheet())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        nulls = count_nulls(self._series)
        hint = QLabel(
            f"열 '{self._column}' · 결측 {nulls:,}개\n"
            "비어 있는 칸만 채웁니다. (행 삭제가 아닙니다)"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(hint)

        if column_supports_numeric_fill(self._series):
            stat_hint = QLabel("숫자 열 — 평균·중앙값·최소·최대 등 통계값으로 채울 수 있습니다.")
        else:
            stat_hint = QLabel("텍스트·날짜 등 — 최빈값·위/아래 값·직접 입력을 사용하세요.")
        stat_hint.setWordWrap(True)
        stat_hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(stat_hint)

        layout.addWidget(QLabel("채우기 방식:"))
        self.method_combo = QComboBox()
        self._method_codes: list[str] = []
        for code in self._methods:
            self._method_codes.append(code)
            self.method_combo.addItem(FILL_NA_METHOD_LABELS.get(code, code))
        self._sync_dependency_methods()
        layout.addWidget(self.method_combo)

        self.constant_label = QLabel("채울 값:")
        self.constant_entry = QLineEdit()
        const_row = QVBoxLayout()
        const_row.addWidget(self.constant_label)
        const_row.addWidget(self.constant_entry)
        self._constant_box = QWidget()
        self._constant_box.setLayout(const_row)
        layout.addWidget(self._constant_box)

        knn_row = QHBoxLayout()
        knn_row.addWidget(QLabel("이웃 수 (k):"))
        self._knn_neighbors = QSpinBox()
        self._knn_neighbors.setRange(1, 50)
        self._knn_neighbors.setValue(5)
        knn_row.addWidget(self._knn_neighbors)
        knn_row.addStretch()
        self._knn_box = QWidget()
        self._knn_box.setLayout(knn_row)
        layout.addWidget(self._knn_box)

        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self.preview_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("적용")
        self._ok_btn = ok_btn
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.method_combo.currentTextChanged.connect(self._update_option_visibility)
        self.method_combo.currentTextChanged.connect(self._update_preview)
        self.constant_entry.textChanged.connect(self._update_preview)
        self._knn_neighbors.valueChanged.connect(self._update_preview)
        self._update_option_visibility()
        self._update_preview()

    def _sync_dependency_methods(self) -> None:
        if sklearn_available():
            return
        model = self.method_combo.model()
        for idx, code in enumerate(self._method_codes):
            if code in {"knn", "mice"} and hasattr(model, "item"):
                item = model.item(idx)
                if item is not None:
                    item.setEnabled(False)
                    item.setToolTip(feature_requirement_message("sklearn", inline=True))

    def _selected_method(self) -> str:
        idx = self.method_combo.currentIndex()
        return self._method_codes[idx] if 0 <= idx < len(self._method_codes) else "mode"

    def _update_option_visibility(self) -> None:
        method = self._selected_method()
        self._constant_box.setVisible(method == "constant")
        self._knn_box.setVisible(method == "knn")

    def _update_preview(self) -> None:
        method = self._selected_method()
        if hasattr(self, "_ok_btn") and self._ok_btn is not None:
            self._ok_btn.setEnabled(not (method in {"knn", "mice"} and not sklearn_available()))
        if method == "mice":
            if not sklearn_available():
                self.preview_label.setStyleSheet(f"color: {COLORS['danger']};")
                self.preview_label.setText(feature_requirement_message("sklearn", feature="MICE", inline=True))
                return
            before, _, targets = knn_fill_preview(self._df, [self._column])
            if not targets:
                self.preview_label.setText("MICE: 숫자 열이 아니거나 결측이 없습니다.")
                return
            warn = "\n⚠ 대용량 — 반복 대체라 시간이 걸릴 수 있습니다." if len(self._df) > 3000 else ""
            self.preview_label.setStyleSheet(f"color: {COLORS['text']};")
            self.preview_label.setText(f"미리보기 — MICE: 결측 {before:,}개 → 0개 (반복 대체){warn}")
            return
        if method == "knn":
            if not sklearn_available():
                self.preview_label.setStyleSheet(f"color: {COLORS['danger']};")
                self.preview_label.setText(feature_requirement_message("sklearn", feature="KNN", inline=True))
                return
            before, _, targets = knn_fill_preview(self._df, [self._column])
            if not targets:
                self.preview_label.setText("KNN: 숫자 열이 아니거나 결측이 없습니다.")
                return
            k = self._knn_neighbors.value()
            warn = "\n⚠ 대용량 데이터 — 적용에 시간이 걸릴 수 있습니다." if len(self._df) > 5000 else ""
            self.preview_label.setStyleSheet(f"color: {COLORS['text']};")
            self.preview_label.setText(
                f"미리보기 — KNN (k={k}): 결측 {before:,}개 → 0개 (모델 기반 대체){warn}"
            )
            return
        if method in ("ffill", "bfill"):
            self.preview_label.setText(
                "미리보기: 인접한 값으로 빈 칸을 채웁니다. (맨 위/아래는 남을 수 있음)"
            )
            return
        if method == "constant":
            text = self.constant_entry.text().strip()
            if not text:
                self.preview_label.setText("채울 값을 입력하면 미리보기가 표시됩니다.")
                return
            try:
                sample = compute_fill_na_scalar(self._series, method, constant=text)
            except Exception as exc:
                self.preview_label.setText(f"미리보기 오류: {exc}")
                self.preview_label.setStyleSheet(f"color: {COLORS['danger']};")
                return
        else:
            try:
                sample = compute_fill_na_scalar(self._series, method)
            except Exception as exc:
                self.preview_label.setText(f"미리보기 오류: {exc}")
                self.preview_label.setStyleSheet(f"color: {COLORS['danger']};")
                return
        self.preview_label.setStyleSheet(f"color: {COLORS['text']};")
        self.preview_label.setText(f"미리보기 — 모든 결측치에 넣을 값: {sample}")

    def _apply(self) -> None:
        method = self._selected_method()
        constant = self.constant_entry.text().strip() if method == "constant" else None
        n_neighbors = self._knn_neighbors.value() if method == "knn" else None
        try:
            if method in ("knn", "mice"):
                if not sklearn_available():
                    raise ValueError("scikit-learn이 설치되어 있지 않습니다.")
            elif method == "constant":
                compute_fill_na_scalar(self._series, method, constant=constant)
            elif method not in ("ffill", "bfill"):
                compute_fill_na_scalar(self._series, method)
        except Exception as exc:
            QMessageBox.warning(self, "입력 오류", str(exc))
            return
        self._result = (method, constant if method == "constant" else None, n_neighbors)
        self.accept()

    def get_result(self) -> tuple[str, str | None, int | None] | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._result


def qt_fill_na_dialog(
    parent: QWidget | None,
    df: pd.DataFrame,
    column: str,
) -> tuple[str, str | None, int | None] | None:
    key = resolve_column_key(df, column)
    if key is None or count_nulls(df[key]) <= 0:
        QMessageBox.information(parent, "결측치 없음", f"'{column}' 열에 결측치가 없습니다.")
        return None
    try:
        return QtFillNaDialog(parent, df, column).get_result()
    except ValueError as exc:
        QMessageBox.warning(parent, "열 오류", str(exc))
        return None


def qt_fill_na_pick_column_dialog(
    parent: QWidget | None,
    df: pd.DataFrame,
) -> str | None:
    """결측이 있는 열 목록에서 선택."""
    from df_tool.operations import resolve_column_key as _resolve

    choices: list[str] = []
    for col in df.columns:
        key = _resolve(df, str(col))
        if key is not None and count_nulls(df[key]) > 0:
            choices.append(str(col))
    if not choices:
        QMessageBox.information(parent, "결측치 없음", "결측치가 있는 열이 없습니다.")
        return None
    dlg = _QtFormDialog(parent, "결측치 채우기 — 열 선택", confirm_text="다음", min_width=400)
    dlg._layout.addWidget(QLabel("결측치를 채울 열을 선택하세요."))
    combo = QComboBox()
    for name in choices:
        key = _resolve(df, name)
        n = count_nulls(df[key]) if key is not None else 0
        combo.addItem(f"{name}  (결측 {n:,}개)")
    dlg._layout.addWidget(combo)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    text = combo.currentText().strip()
    return text.split("  (")[0] if "  (" in text else text
