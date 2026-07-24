"""PyQt 네이티브 다이얼로그."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QCheckBox,
    QAbstractItemView,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from df_tool.loader import SAVE_EXT_BY_FORMAT, SAVE_FORMAT_BY_LABEL, SAVE_FORMAT_LABELS, SAVE_FORMATS
from df_tool.theme import COLORS


class QtSaveAsDialog(QDialog):
    """저장 경로 + 파일 형식 선택 (PyQt 네이티브)."""

    def __init__(
        self,
        parent: QWidget | None,
        default_path: Path,
        default_format: str = "csv_utf8_sig",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("다른 이름으로 저장")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._result: tuple[Path, str] | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(QLabel("저장 위치와 파일 형식을 선택하세요."))

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("파일 경로"))
        self.path_edit = QLineEdit(str(default_path))
        path_row.addWidget(self.path_edit, stretch=1)
        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("파일 형식"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(SAVE_FORMAT_LABELS)
        default_label = next(
            (label for key, label, _ in SAVE_FORMATS if key == default_format),
            SAVE_FORMAT_LABELS[0],
        )
        idx = self.format_combo.findText(default_label)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        fmt_row.addWidget(self.format_combo, stretch=1)
        layout.addLayout(fmt_row)

        hint = QLabel(
            "※ CP949는 한글 Windows·Excel에서 바로 열기 좋습니다.\n"
            "   UTF-8 BOM은 최신 Excel·웹 호환에 적합합니다."
        )
        hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("저장")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}
            QLineEdit, QComboBox {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_subtle']};
                padding: 6px 8px;
            }}
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_subtle']};
                padding: 6px 12px;
            }}
            """
        )

    def _browse(self) -> None:
        label = self.format_combo.currentText()
        fmt_key = SAVE_FORMAT_BY_LABEL.get(label, "csv_utf8_sig")
        ext = SAVE_EXT_BY_FORMAT.get(fmt_key, ".csv")
        current = Path(self.path_edit.text().strip() or ".")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "저장 위치 선택",
            str(current),
            f"{label} (*{ext});;모든 파일 (*.*)",
        )
        if path:
            self.path_edit.setText(path)

    def _accept(self) -> None:
        raw = self.path_edit.text().strip()
        if not raw:
            QMessageBox.warning(self, "입력 오류", "저장할 파일 경로를 입력하세요.")
            return
        label = self.format_combo.currentText()
        fmt = SAVE_FORMAT_BY_LABEL.get(label)
        if not fmt:
            QMessageBox.warning(self, "입력 오류", "파일 형식을 선택하세요.")
            return
        self._result = (Path(raw), fmt)
        self.accept()

    def get_result(self) -> tuple[Path, str] | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._result


def _dialog_stylesheet() -> str:
    return f"""
        QDialog {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}
        QLineEdit {{
            background: {COLORS['surface_alt']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border_subtle']};
            padding: 6px 8px;
        }}
        QPushButton {{
            background: {COLORS['surface']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border_subtle']};
            padding: 6px 12px;
        }}
        """


def qt_confirm(
    parent: QWidget | None,
    title: str,
    message: str,
    *,
    confirm_text: str = "확인",
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    yes_btn = box.addButton(confirm_text, QMessageBox.ButtonRole.YesRole)
    box.addButton("취소", QMessageBox.ButtonRole.NoRole)
    box.exec()
    return box.clickedButton() is yes_btn


class _QtFormDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        *,
        confirm_text: str = "확인",
        min_width: int = 400,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(min_width)
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(10)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText(confirm_text)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        self.setStyleSheet(_dialog_stylesheet())


def qt_insert_row_dialog(parent: QWidget | None, *, position_label: str) -> int | None:
    dlg = _QtFormDialog(parent, "행 추가", confirm_text="추가", min_width=380)
    dlg._layout.addWidget(QLabel(position_label))
    dlg._layout.addWidget(QLabel("추가할 행 개수:"))
    entry = QLineEdit("1")
    dlg._layout.addWidget(entry)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    raw = entry.text().strip()
    if not raw.isdigit() or int(raw) < 1:
        QMessageBox.warning(parent, "입력 오류", "1 이상의 숫자를 입력하세요.")
        return None
    return int(raw)


def qt_add_column_dialog(parent: QWidget | None, *, position_hint: str = "") -> tuple[str, str] | None:
    dlg = _QtFormDialog(parent, "열 추가", confirm_text="추가", min_width=420)
    if position_hint:
        hint = QLabel(position_hint)
        hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        dlg._layout.addWidget(hint)
    dlg._layout.addWidget(QLabel("열 이름:"))
    name_entry = QLineEdit()
    dlg._layout.addWidget(name_entry)
    dlg._layout.addWidget(QLabel("기본값 (선택):"))
    default_entry = QLineEdit()
    dlg._layout.addWidget(default_entry)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    name = name_entry.text().strip()
    if not name:
        QMessageBox.warning(parent, "입력 오류", "열 이름을 입력하세요.")
        return None
    return name, default_entry.text()


def qt_rename_column_dialog(parent: QWidget | None, current_name: str) -> str | None:
    dlg = _QtFormDialog(parent, "열 이름 변경", min_width=420)
    dlg._layout.addWidget(QLabel(f"현재 이름: {current_name}"))
    dlg._layout.addWidget(QLabel("새 이름:"))
    entry = QLineEdit(current_name)
    entry.selectAll()
    dlg._layout.addWidget(entry)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    name = entry.text().strip()
    if not name:
        QMessageBox.warning(parent, "입력 오류", "새 열 이름을 입력하세요.")
        return None
    return name


def qt_duplicate_column_dialog(
    parent: QWidget | None,
    column: str,
    suggested_name: str,
) -> str | None:
    dlg = _QtFormDialog(parent, "열 복제", confirm_text="복제", min_width=420)
    dlg._layout.addWidget(QLabel(f"복제할 열: {column}"))
    dlg._layout.addWidget(QLabel("새 열 이름:"))
    entry = QLineEdit(suggested_name)
    entry.selectAll()
    dlg._layout.addWidget(entry)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    name = entry.text().strip()
    if not name:
        QMessageBox.warning(parent, "입력 오류", "새 열 이름을 입력하세요.")
        return None
    return name


def qt_merge_columns_dialog(
    parent: QWidget | None,
    columns: list[str],
) -> tuple[str, str, bool] | None:
    """열 가로 병합 — (결과 열 이름, 구분자, 원본 열 삭제 여부)."""
    if len(columns) < 2:
        return None
    labels = [str(c) for c in columns]
    default_name = "_".join(labels)
    dlg = _QtFormDialog(parent, "열 병합", confirm_text="병합", min_width=460)
    hint = QLabel(
        f"선택 열 {len(labels)}개: {', '.join(labels)}\n"
        "각 행의 값을 왼쪽→오른쪽 순서로 이어 붙입니다."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
    dlg._layout.addWidget(hint)
    dlg._layout.addWidget(QLabel("결과 열 이름:"))
    name_entry = QLineEdit(default_name)
    dlg._layout.addWidget(name_entry)
    dlg._layout.addWidget(QLabel("구분자 (비우면 붙여 쓰기):"))
    sep_entry = QLineEdit("")
    sep_entry.setPlaceholderText("예: 공백, -, /, _")
    dlg._layout.addWidget(sep_entry)
    drop_cb = QCheckBox("병합 후 원본 열 삭제")
    drop_cb.setChecked(True)
    dlg._layout.addWidget(drop_cb)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    name = name_entry.text().strip()
    if not name:
        QMessageBox.warning(parent, "입력 오류", "결과 열 이름을 입력하세요.")
        return None
    return name, sep_entry.text(), drop_cb.isChecked()


def qt_split_column_dialog(
    parent: QWidget | None,
    column: str,
) -> tuple[str, str, bool] | None:
    """열 분리 — (구분자, 열 이름 접두사, 원본 열 삭제 여부)."""
    col_label = str(column)
    dlg = _QtFormDialog(parent, "열 분리", confirm_text="분리", min_width=460)
    hint = QLabel(
        f"열 '{col_label}'의 값을 구분자 기준으로 나눕니다.\n"
        "예: '서울-강남' + 구분자 '-' → '서울', '강남' 두 열"
    )
    hint.setWordWrap(True)
    hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
    dlg._layout.addWidget(hint)
    dlg._layout.addWidget(QLabel("구분자:"))
    sep_entry = QLineEdit(",")
    sep_entry.setPlaceholderText("예: ,  -  /  공백은 스페이스 한 칸 · 탭은 \\t")
    dlg._layout.addWidget(sep_entry)
    dlg._layout.addWidget(QLabel("새 열 이름 접두사:"))
    prefix_entry = QLineEdit(col_label)
    dlg._layout.addWidget(prefix_entry)
    drop_cb = QCheckBox("분리 후 원본 열 삭제")
    drop_cb.setChecked(False)
    dlg._layout.addWidget(drop_cb)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    separator = sep_entry.text()
    if separator == "":
        QMessageBox.warning(parent, "입력 오류", "구분자를 입력하세요.")
        return None
    prefix = prefix_entry.text().strip()
    if not prefix:
        QMessageBox.warning(parent, "입력 오류", "새 열 이름 접두사를 입력하세요.")
        return None
    return separator, prefix, drop_cb.isChecked()


def qt_sequential_fill_dialog(parent: QWidget | None, column: str) -> tuple[int, int] | None:
    dlg = _QtFormDialog(parent, "순차 번호 채우기", confirm_text="채우기", min_width=400)
    msg = QLabel(f"'{column}' 열 전체에 1, 2, 3… 순서로 번호를 채웁니다.")
    msg.setWordWrap(True)
    dlg._layout.addWidget(msg)
    dlg._layout.addWidget(QLabel("시작 번호:"))
    start_entry = QLineEdit("1")
    dlg._layout.addWidget(start_entry)
    dlg._layout.addWidget(QLabel("간격 (1이면 1,2,3… / 2이면 1,3,5…):"))
    step_entry = QLineEdit("1")
    dlg._layout.addWidget(step_entry)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    try:
        start = int(start_entry.text().strip())
        step = int(step_entry.text().strip())
    except ValueError:
        QMessageBox.warning(parent, "입력 오류", "시작 번호와 간격은 정수로 입력하세요.")
        return None
    if step == 0:
        QMessageBox.warning(parent, "입력 오류", "간격은 0이 아닌 정수로 입력하세요.")
        return None
    return start, step


def qt_select_column_dialog(
    parent: QWidget | None,
    title: str,
    label: str,
    columns: list[str],
    *,
    confirm_text: str = "확인",
) -> str | None:
    if not columns:
        return None
    dlg = _QtFormDialog(parent, title, confirm_text=confirm_text, min_width=420)
    dlg._layout.addWidget(QLabel(label))
    combo = QComboBox()
    combo.addItems(columns)
    dlg._layout.addWidget(combo)
    dlg._layout.addWidget(dlg._buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    value = combo.currentText().strip()
    return value or None


def qt_select_columns_dialog(
    parent: QWidget | None,
    title: str,
    label: str,
    columns: list[str],
    *,
    preselect: list[str] | None = None,
    confirm_text: str = "확인",
    min_count: int = 1,
) -> list[str] | None:
    """여러 열을 Ctrl/Shift로 다중 선택. 선택 목록을 반환합니다."""
    if not columns:
        return None
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.setMinimumWidth(460)
    dlg.resize(480, 420)
    root = QVBoxLayout(dlg)
    hint = QLabel(label)
    hint.setWordWrap(True)
    root.addWidget(hint)
    tip = QLabel("Ctrl·Shift 클릭으로 여러 열을 선택할 수 있습니다.")
    tip.setStyleSheet(f"color: {COLORS['text_muted']};")
    root.addWidget(tip)

    listing = QListWidget()
    listing.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    pre = set(preselect or [])
    for name in columns:
        item = QListWidgetItem(str(name))
        listing.addItem(item)
        if str(name) in pre:
            item.setSelected(True)
    if not listing.selectedItems() and listing.count() > 0:
        listing.item(0).setSelected(True)
    root.addWidget(listing, stretch=1)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
    if ok_btn:
        ok_btn.setText(confirm_text)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    root.addWidget(buttons)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    selected = [item.text() for item in listing.selectedItems()]
    if len(selected) < min_count:
        QMessageBox.warning(parent, title, f"열을 최소 {min_count}개 선택하세요.")
        return None
    # 목록 순서로 정렬
    order = {str(c): i for i, c in enumerate(columns)}
    selected.sort(key=lambda x: order.get(x, 0))
    return selected


def _dup_report_table(report) -> QTableWidget:
    table = QTableWidget(len(report.duplicate_counts), 2)
    table.setHorizontalHeaderLabels(["중복 값", "횟수"])
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)
    for i, (value, count) in enumerate(report.duplicate_counts):
        table.setItem(i, 0, QTableWidgetItem(value))
        table.setItem(i, 1, QTableWidgetItem(f"{count:,}"))
    return table


def qt_duplicate_report_dialog(parent: QWidget | None, report) -> bool:
    """단일 열 값 중복 리포트. True면 표에서 해당 행만 표시."""
    cols = qt_duplicate_reports_dialog(parent, [report])
    return bool(cols)


def qt_duplicate_reports_dialog(parent: QWidget | None, reports) -> list[str] | None:
    """열별 값 중복 리포트. 표시할 열 이름 목록을 반환 (닫기면 None).

    ``reports``: ``operations.DuplicateReport`` 시퀀스 (열마다 1개).
    """
    reports = list(reports)
    if not reports:
        return None

    dlg = QDialog(parent)
    names = [r.column for r in reports]
    title = "값 중복 찾기" if len(names) == 1 else f"값 중복 찾기 — {len(names)}개 열"
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.resize(620, 520)
    layout = QVBoxLayout(dlg)

    lines: list[str] = []
    any_dup = False
    for report in reports:
        col = report.column
        if report.duplicate_value_count == 0:
            lines.append(
                f"· '{col}': 중복 없음 "
                f"(고유 {report.unique_count:,} / 전체 {report.total_rows:,}"
                f" · 결측 {report.null_count:,})"
            )
        else:
            any_dup = True
            lines.append(
                f"· '{col}': 중복 있음 — 중복 값 {report.duplicate_value_count:,}개"
                f" · 해당 행 {report.duplicate_row_count:,}행 "
                f"(고유 {report.unique_count:,} / 전체 {report.total_rows:,}"
                f" · 결측 {report.null_count:,})"
            )
    overview = QLabel(
        "선택한 열을 각각 검사한 결과입니다. (열 조합이 아닙니다)\n\n"
        + "\n".join(lines)
        + "\n\n※ 모든 열이 똑같은 행을 지우려면 [완전동일 행 제거]를 쓰세요."
    )
    overview.setWordWrap(True)
    layout.addWidget(overview)

    result_cols: list[str] = []

    if not any_dup:
        ok = QLabel("선택한 모든 열에서 값 중복이 없습니다.")
        ok.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(ok)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.clicked.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.exec()
        return None

    hint = QLabel(
        "아래 탭에서 열별 중복 값을 확인하세요. "
        "표에 좁혀 볼 열을 고른 뒤 [표시] 버튼을 누르세요."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
    layout.addWidget(hint)

    tabs = QTabWidget()
    for report in reports:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(4, 8, 4, 4)
        if report.duplicate_value_count == 0:
            empty = QLabel(f"'{report.column}'에는 중복 값이 없습니다.")
            empty.setStyleSheet(f"color: {COLORS['success']};")
            page_layout.addWidget(empty)
        else:
            page_layout.addWidget(_dup_report_table(report), stretch=1)
            if report.duplicate_value_count > len(report.duplicate_counts):
                more = QLabel(
                    f"… 외 {report.duplicate_value_count - len(report.duplicate_counts):,}개 "
                    "(목록은 상위만 표시)"
                )
                more.setStyleSheet(f"color: {COLORS['text_muted']};")
                page_layout.addWidget(more)
        badge = "중복" if report.duplicate_value_count else "없음"
        tabs.addTab(page, f"{report.column} ({badge})")
    layout.addWidget(tabs, stretch=1)

    buttons = QDialogButtonBox()
    if len(reports) == 1:
        show_btn = buttons.addButton("이 행만 표에 표시", QDialogButtonBox.ButtonRole.AcceptRole)

        def _show_one() -> None:
            nonlocal result_cols
            result_cols = [reports[0].column]
            dlg.accept()

        show_btn.clicked.connect(_show_one)
    else:
        show_all = buttons.addButton(
            "중복 있는 열 전부 표시", QDialogButtonBox.ButtonRole.AcceptRole
        )
        show_tab = buttons.addButton(
            "현재 탭만 표시", QDialogButtonBox.ButtonRole.ActionRole
        )

        def _show_all() -> None:
            nonlocal result_cols
            result_cols = [r.column for r in reports if r.duplicate_value_count > 0]
            dlg.accept()

        def _show_tab() -> None:
            nonlocal result_cols
            idx = tabs.currentIndex()
            if 0 <= idx < len(reports):
                report = reports[idx]
                if report.duplicate_value_count == 0:
                    QMessageBox.information(
                        dlg,
                        "값 중복 찾기",
                        f"'{report.column}'에는 표시할 중복 행이 없습니다.",
                    )
                    return
                result_cols = [report.column]
                dlg.accept()

        show_all.clicked.connect(_show_all)
        show_tab.clicked.connect(_show_tab)

    close_btn = buttons.addButton("닫기", QDialogButtonBox.ButtonRole.RejectRole)
    close_btn.clicked.connect(dlg.reject)
    layout.addWidget(buttons)

    if dlg.exec() != QDialog.DialogCode.Accepted or not result_cols:
        return None
    return result_cols


def qt_find_replace_dialog(
    parent: QWidget | None,
    columns: list[str],
    *,
    selection_hint: str = "",
    has_selection: bool = False,
) -> tuple[str, str, str | None, bool] | None:
    dlg = _QtFormDialog(parent, "찾기 및 바꾸기", confirm_text="바꾸기", min_width=480)
    if selection_hint:
        hint = QLabel(f"현재 선택: {selection_hint}")
        hint.setStyleSheet(f"color: {COLORS['primary']};")
        dlg._layout.addWidget(hint)
    dlg._layout.addWidget(QLabel("찾을 내용:"))
    find_entry = QLineEdit()
    dlg._layout.addWidget(find_entry)
    dlg._layout.addWidget(QLabel("바꿀 내용:"))
    replace_entry = QLineEdit()
    dlg._layout.addWidget(replace_entry)
    dlg._layout.addWidget(QLabel("적용 범위:"))
    scope_combo = QComboBox()
    scope_values: list[str] = []
    if has_selection:
        scope_values.append("(선택 영역만)")
    scope_values.extend(["(전체 열)", *columns])
    scope_combo.addItems(scope_values)
    dlg._layout.addWidget(scope_combo)
    case_cb = QCheckBox("대소문자 구분")
    dlg._layout.addWidget(case_cb)
    dlg._layout.addWidget(dlg._buttons)
    find_entry.setFocus()
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    find_text = find_entry.text()
    if not find_text:
        QMessageBox.warning(parent, "입력 오류", "찾을 내용을 입력하세요.")
        return None
    scope = scope_combo.currentText()
    if scope == "(선택 영역만)":
        column: str | None = "__selection__"
    elif scope == "(전체 열)":
        column = None
    else:
        column = scope
    return find_text, replace_entry.text(), column, case_cb.isChecked()


class QtHelpDialog(QDialog):
    """도움말·가이드 문서 표시 (PyQt 네이티브)."""

    def __init__(
        self,
        parent: QWidget | None,
        content: str,
        *,
        title: str = "사용법",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(640, 480)
        self.resize(760, 640)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(content)
        text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(text, stretch=1)
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)
        self.setStyleSheet(_dialog_stylesheet())
