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
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QCheckBox,
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
