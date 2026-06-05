"""PyQt 사이드바 패널 — 정보·코드·작업 로그."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from df_tool.operations import SELECTABLE_DTYPES, column_dtype_display, count_nulls
from df_tool.performance import should_show_detailed_stats_by_default
from df_tool.theme import COLORS

_KIND_LABEL = {
    "success": "완료",
    "error": "실패",
    "warning": "알림",
    "info": "정보",
}


def _memory_usage(df: pd.DataFrame, *, detailed: bool) -> str:
    try:
        mem = df.memory_usage(deep=detailed).sum()
    except (TypeError, ValueError):
        mem = df.memory_usage(deep=False).sum()
    if mem >= 1024**3:
        return f"{mem / 1024**3:.2f} GB"
    if mem >= 1024**2:
        return f"{mem / 1024**2:.1f} MB"
    if mem >= 1024:
        return f"{mem / 1024:.1f} KB"
    return f"{mem} B"


def _readonly_table_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class InfoPanel(QWidget):
    def __init__(
        self,
        on_dtype_change: Callable[[str, str], None] | None = None,
        on_fill_na: Callable[[str], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.on_dtype_change = on_dtype_change
        self.on_fill_na = on_fill_na
        self._df: pd.DataFrame | None = None
        self._path = ""
        self._sheet: str | None = None
        self._detailed_stats = True
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("데이터 정보"))
        header.addStretch()
        self._stats_btn = QPushButton("상세 통계 켜짐")
        self._stats_btn.clicked.connect(self.toggle_detailed_stats)
        header.addWidget(self._stats_btn)
        layout.addLayout(header)

        stats = QHBoxLayout()
        self.rows_label = QLabel("-")
        self.cols_label = QLabel("-")
        self.memory_label = QLabel("-")
        for title, widget in [("행", self.rows_label), ("열", self.cols_label), ("크기", self.memory_label)]:
            box = QFrame()
            box.setObjectName("StatBox")
            box.setStyleSheet(f"background: {COLORS['stat_bg']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(8, 6, 8, 6)
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9pt;")
            bl.addWidget(title_lbl)
            widget.setStyleSheet("font-weight: 600; font-size: 11pt;")
            bl.addWidget(widget)
            stats.addWidget(box)
        layout.addLayout(stats)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["컬럼", "타입", "결측치", "고유값"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table, stretch=1)

        self.file_label = QLabel("파일을 열면 요약이 표시됩니다")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)

    def apply_default_stats_visibility(self, row_count: int, col_count: int) -> None:
        self.set_detailed_stats(should_show_detailed_stats_by_default(row_count, col_count))

    def set_detailed_stats(self, enabled: bool) -> None:
        self._detailed_stats = enabled
        self._stats_btn.setText("상세 통계 켜짐" if enabled else "상세 통계 꺼짐")
        if self._df is not None:
            self._render()

    def toggle_detailed_stats(self) -> None:
        self.set_detailed_stats(not self._detailed_stats)

    def show(self, df: pd.DataFrame, path: str, sheet: str | None = None) -> None:
        self._df = df
        self._path = path
        self._sheet = sheet
        self._render()

    def clear(self) -> None:
        self._df = None
        self.rows_label.setText("-")
        self.cols_label.setText("-")
        self.memory_label.setText("-")
        self.table.setRowCount(0)
        self.file_label.setText("파일을 열면 요약이 표시됩니다")

    def apply_theme(self) -> None:
        from df_tool.qt_theme import card_frame_style

        c = COLORS
        stat_style = (
            f"QFrame#StatBox {{ background: {c['stat_bg']}; "
            f"border: 1px solid {c['border_subtle']}; border-radius: 4px; padding: 4px; }}"
        )
        for box in self.findChildren(QFrame):
            if box.objectName() == "StatBox":
                box.setStyleSheet(stat_style)
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {c['surface']}; gridline-color: {c['cell_grid']}; "
            f"border: 1px solid {c['border_subtle']}; border-radius: 4px; }}"
        )
        self.file_label.setStyleSheet(f"color: {c['text_muted']};")

    def _render(self) -> None:
        if self._df is None:
            return
        df = self._df
        self.rows_label.setText(f"{len(df):,}")
        self.cols_label.setText(f"{len(df.columns):,}")
        self.memory_label.setText(_memory_usage(df, detailed=self._detailed_stats))
        file_text = Path(self._path).name if self._path else "파일"
        if self._sheet:
            file_text += f" · {self._sheet}"
        self.file_label.setText(file_text)

        self.table.setRowCount(len(df.columns))
        for row, col in enumerate(df.columns):
            col_str = str(col)
            if self._detailed_stats:
                null_text = f"{count_nulls(df[col]):,}"
                unique_text = f"{int(df[col].nunique(dropna=True)):,}"
            else:
                null_text = "—"
                unique_text = "—"
            self.table.setItem(row, 0, _readonly_table_item(col_str))
            self.table.setItem(row, 1, _readonly_table_item(column_dtype_display(df[col])))
            null_item = _readonly_table_item(null_text)
            if self._detailed_stats and null_text not in ("—", "0"):
                null_item.setForeground(QColor(COLORS["primary"]))
                null_item.setToolTip("클릭하여 결측치 채우기")
            self.table.setItem(row, 2, null_item)
            self.table.setItem(row, 3, _readonly_table_item(unique_text))

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col != 2 or self._df is None or not self.on_fill_na:
            return
        column_item = self.table.item(row, 0)
        if not column_item:
            return
        from df_tool.operations import count_nulls, resolve_column_key

        column = column_item.text()
        key = resolve_column_key(self._df, column)
        if key is None:
            return
        if count_nulls(self._df[key]) <= 0:
            return
        self.on_fill_na(column)

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if col == 1:
            self._on_dtype_click(row, col)

    def _on_dtype_click(self, row: int, col: int) -> None:
        if col != 1 or self._df is None or not self.on_dtype_change:
            return
        column_item = self.table.item(row, 0)
        if not column_item:
            return
        column = column_item.text()
        combo = QComboBox(self.table)
        combo.addItems(SELECTABLE_DTYPES)
        combo.setCurrentText(column_dtype_display(self._df[column]))
        combo.activated.connect(lambda _i: self._apply_dtype(row, column, combo))
        self.table.setCellWidget(row, 1, combo)

    def _apply_dtype(self, row: int, column: str, combo: QComboBox) -> None:
        dtype = combo.currentText()
        self.table.removeCellWidget(row, 1)
        if self.on_dtype_change:
            self.on_dtype_change(column, dtype)


DEFAULT_CODE = """# df 변수로 데이터 조작 (pandas 사용 가능)
# df = df[df['age'] > 25]
# df['bonus'] = df['salary'] * 0.1
"""


class CodePanel(QWidget):
    def __init__(
        self,
        on_run: Callable[[pd.DataFrame], None],
        get_dataframe: Callable[[], pd.DataFrame | None],
        on_undo: Callable[[], None] | None = None,
        on_notify: Callable[[bool, str], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.on_run = on_run
        self.get_dataframe = get_dataframe
        self.on_undo = on_undo
        self.on_notify = on_notify
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Python 코드"))
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Ctrl+Enter 실행"))
        toolbar.addStretch()
        self.output_label = QLabel("준비")
        toolbar.addWidget(self.output_label)
        run_btn = QPushButton("실행")
        run_btn.clicked.connect(self.execute)
        toolbar.addWidget(run_btn)
        undo_btn = QPushButton("되돌리기")
        undo_btn.clicked.connect(self._undo_last)
        toolbar.addWidget(undo_btn)
        reset_btn = QPushButton("초기화")
        reset_btn.clicked.connect(self.reset_code)
        toolbar.addWidget(reset_btn)
        layout.addLayout(toolbar)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(DEFAULT_CODE)
        font = QFont("Consolas", 10)
        self.editor.setFont(font)
        self.editor.setStyleSheet(
            f"background: {COLORS['code_bg']}; color: {COLORS['code_fg']}; border: 1px solid {COLORS['border_subtle']};"
        )
        layout.addWidget(self.editor, stretch=1)
        QShortcut(QKeySequence("Ctrl+Return"), self.editor, self.execute)
        QShortcut(QKeySequence("Ctrl+Enter"), self.editor, self.execute)

    def execute(self) -> None:
        df = self.get_dataframe()
        if df is None:
            self.output_label.setText("데이터 없음")
            return
        code = self.editor.toPlainText()
        local_ns = {"df": df.copy(), "pd": pd}
        try:
            exec(code, {"pd": pd}, local_ns)
        except Exception as exc:
            self.output_label.setText("오류")
            if self.on_notify:
                self.on_notify(False, str(exc))
            return
        result = local_ns.get("df")
        if not isinstance(result, pd.DataFrame):
            self.output_label.setText("df가 DataFrame이 아님")
            if self.on_notify:
                self.on_notify(False, "코드 실행 후 df가 pandas DataFrame이어야 합니다.")
            return
        self.output_label.setText("완료")
        self.on_run(result)

    def _undo_last(self) -> None:
        if self.on_undo:
            self.on_undo()

    def reset_code(self) -> None:
        self.editor.setPlainText(DEFAULT_CODE)
        self.output_label.setText("준비")

    def apply_theme(self) -> None:
        self.editor.setStyleSheet(
            f"background: {COLORS['code_bg']}; color: {COLORS['code_fg']}; border: 1px solid {COLORS['border_subtle']};"
        )


class ActivityLogPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[tuple[str, str, str | None, datetime]] = []
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("작업 로그"))
        header.addStretch()
        self.count_label = QLabel("기록 0건")
        header.addWidget(self.count_label)
        clear_btn = QPushButton("로그 지우기")
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text, stretch=1)

    def add(self, kind: str, message: str, detail: str | None = None) -> None:
        ts = datetime.now()
        self._entries.append((kind, message, detail, ts))
        self._render()

    def clear(self) -> None:
        self._entries.clear()
        self.text.clear()
        self.count_label.setText("기록 0건")

    def apply_theme(self) -> None:
        self.text.setStyleSheet(
            f"background: {COLORS['code_bg']}; color: {COLORS['code_fg']}; border: 1px solid {COLORS['border_subtle']};"
        )

    def _render(self) -> None:
        lines: list[str] = []
        for kind, message, detail, ts in self._entries:
            label = _KIND_LABEL.get(kind, kind)
            line = f"[{ts.strftime('%H:%M:%S')}] [{label}] {message}"
            if detail:
                line += f"\n    {detail}"
            lines.append(line)
        self.text.setPlainText("\n\n".join(lines))
        self.count_label.setText(f"기록 {len(self._entries)}건")
