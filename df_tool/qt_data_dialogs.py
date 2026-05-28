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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from df_tool.loader import FILE_DIALOG_TYPES, load_file
from df_tool.operations import vlookup, vlookup_stats
from df_tool.qt_dialogs import _QtFormDialog, _dialog_stylesheet
from df_tool.theme import COLORS

_PREVIEW_ROWS = 50


def _cell_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


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

        for combo in (self.left_key, self.right_key, self.return_col):
            combo.currentTextChanged.connect(self._schedule_preview)
        self.new_name.textChanged.connect(self._schedule_preview)

    def _load_reference(self) -> None:
        filters = ";;".join(f"{label} ({pat})" for label, pat in FILE_DIALOG_TYPES)
        path, _ = QFileDialog.getOpenFileName(self, "참조 파일 선택", "", filters)
        if not path:
            return
        try:
            loaded = load_file(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "파일 열기 실패", str(exc))
            return
        self._ref_df = loaded.dataframe
        cols = [str(c) for c in self._ref_df.columns]
        self.file_label.setText(f"{loaded.path.name}  ({len(self._ref_df):,}행 × {len(cols)}열)")
        self.file_label.setStyleSheet(f"color: {COLORS['text']};")
        self.right_key.clear()
        self.return_col.clear()
        self.right_key.addItems(cols)
        self.return_col.addItems(cols)
        if cols:
            self.right_key.setCurrentIndex(0)
            pick = 1 if len(cols) > 1 else 0
            self.return_col.setCurrentIndex(pick)
            if not self.new_name.text().strip():
                self.new_name.setText(cols[pick])
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


def qt_merge_dialog(
    parent: QWidget | None,
    left_columns: list[str],
    lookup_sources: list[tuple[str, list[str]]],
) -> tuple[str, str, str, str] | None:
    if not lookup_sources:
        return None
    dlg = _QtFormDialog(parent, "파일 조인 (Merge)", confirm_text="조인", min_width=520)
    hint = QLabel("키 열이 같은 행끼리 가로로 합칩니다.")
    hint.setWordWrap(True)
    hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
    dlg._layout.addWidget(hint)

    source_names = [name for name, _ in lookup_sources]
    lookup_map = {name: cols for name, cols in lookup_sources}

    dlg._layout.addWidget(QLabel("참조 파일:"))
    source_combo = QComboBox()
    source_combo.addItems(source_names)
    dlg._layout.addWidget(source_combo)

    dlg._layout.addWidget(QLabel("현재 표 키 열:"))
    left_on = QComboBox()
    left_on.addItems(left_columns)
    dlg._layout.addWidget(left_on)

    dlg._layout.addWidget(QLabel("참조 파일 키 열:"))
    right_on = QComboBox()
    right_on.addItems(lookup_sources[0][1])
    dlg._layout.addWidget(right_on)

    def _on_source_changed(name: str) -> None:
        cols = lookup_map.get(name, [])
        right_on.clear()
        right_on.addItems(cols)

    source_combo.currentTextChanged.connect(_on_source_changed)

    dlg._layout.addWidget(QLabel("조인 방식:"))
    how_combo = QComboBox()
    how_combo.addItems([label for _, label in _JOIN_TYPES])
    dlg._layout.addWidget(how_combo)
    dlg._layout.addWidget(dlg._buttons)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    source = source_combo.currentText().strip()
    left_key = left_on.currentText().strip()
    right_key = right_on.currentText().strip()
    how_label = how_combo.currentText().strip()
    how = next(code for code, label in _JOIN_TYPES if label == how_label)
    if not all([source, left_key, right_key]):
        QMessageBox.warning(parent, "입력 오류", "모든 항목을 선택하세요.")
        return None
    return source, left_key, right_key, how


def qt_concat_dialog(parent: QWidget | None, sources: list[str]) -> list[str] | None:
    dlg = _QtFormDialog(parent, "파일 세로 병합 (Concat)", confirm_text="병합", min_width=480)
    hint = QLabel(
        "선택한 파일들을 아래로 이어 붙입니다.\n열 이름이 같으면 같은 열로 합쳐집니다."
    )
    hint.setWordWrap(True)
    dlg._layout.addWidget(hint)
    list_widget = QListWidget()
    list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
    for item in sources:
        list_widget.addItem(item)
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)
    dlg._layout.addWidget(list_widget)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    selected = [item.text() for item in list_widget.selectedItems()]
    if not selected:
        QMessageBox.warning(parent, "입력 오류", "병합할 파일을 선택하세요.")
        return None
    return selected


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
