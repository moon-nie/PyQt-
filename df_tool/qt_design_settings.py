"""PyQt 디자인 설정 — 색상 항목별 편집."""
from __future__ import annotations

from copy import deepcopy
from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

from df_tool.theme import COLORS, DEFAULT_COLORS, THEME_GROUPS, save_theme_config
from df_tool.ui_fonts import monospace_css_stack

_DIALOG = {
    "bg": "#12151c",
    "surface": "#1a1f2b",
    "surface_hover": "#222836",
    "border": "#2e3648",
    "text": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "primary": "#818cf8",
    "primary_hover": "#6366f1",
    "preview_border": "#3b4459",
}


def _valid_hex(value: str) -> bool:
    text = value.strip()
    if len(text) != 7 or not text.startswith("#"):
        return False
    try:
        int(text[1:], 16)
        return True
    except ValueError:
        return False


class _ColorRowWidget(QFrame):
    color_changed = pyqtSignal()

    def __init__(self, key: str, label: str, initial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._key = key
        d = _DIALOG
        self.setStyleSheet(
            f"QFrame {{ background: {d['surface']}; border: 1px solid {d['border']}; border-radius: 4px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel(label)
        title.setStyleSheet(f"color: {d['text']}; font-weight: 600;")
        key_lbl = QLabel(key)
        key_lbl.setStyleSheet(
            f"color: {d['text_muted']}; font-family: {monospace_css_stack()}; font-size: 9pt;"
        )
        top.addWidget(title)
        top.addStretch()
        top.addWidget(key_lbl)
        layout.addLayout(top)

        row = QHBoxLayout()
        self._swatch = QPushButton()
        self._swatch.setFixedSize(44, 26)
        self._swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._swatch.clicked.connect(self._pick_color)
        self._entry = QLineEdit(initial)
        self._entry.setMaxLength(7)
        self._entry.setPlaceholderText("#rrggbb")
        self._entry.setStyleSheet(
            f"background: {d['surface_hover']}; color: {d['text']}; "
            f"border: 1px solid {d['border']}; padding: 4px 6px;"
        )
        self._entry.textChanged.connect(self._on_text_changed)
        pick_btn = QPushButton("색상 선택")
        pick_btn.clicked.connect(self._pick_color)
        pick_btn.setStyleSheet(
            f"background: {d['surface_hover']}; color: {d['text_secondary']}; "
            f"border: 1px solid {d['border']}; padding: 4px 10px;"
        )
        row.addWidget(self._swatch)
        row.addWidget(self._entry, stretch=1)
        row.addWidget(pick_btn)
        layout.addLayout(row)
        self._update_swatch()

    def _on_text_changed(self) -> None:
        self._update_swatch()
        self.color_changed.emit()

    def _update_swatch(self) -> None:
        color = self.get_color()
        bg = color if _valid_hex(color) else _DIALOG["primary"]
        self._swatch.setStyleSheet(
            f"background: {bg}; border: 1px solid {_DIALOG['border']}; border-radius: 3px;"
        )

    def _pick_color(self) -> None:
        current = self.get_color()
        initial = QColor(current) if _valid_hex(current) else QColor(DEFAULT_COLORS.get(self._key, "#818cf8"))
        chosen = QColorDialog.getColor(initial, self, f"색상 선택 — {self._key}")
        if chosen.isValid():
            self._entry.setText(chosen.name().lower())

    def get_color(self) -> str:
        return self._entry.text().strip()

    def set_color(self, color: str) -> None:
        self._entry.setText(color.lower())


class QtDesignSettingsDialog(QDialog):
    """색상·디자인 세부 설정 (PyQt)."""

    def __init__(self, parent: QWidget | None, on_apply: Callable[[], None]) -> None:
        super().__init__(parent)
        self._on_apply = on_apply
        self._rows: dict[str, _ColorRowWidget] = {}
        self._draft = {key: COLORS.get(key, DEFAULT_COLORS[key]) for key in DEFAULT_COLORS}

        self.setWindowTitle("디자인 설정")
        self.setMinimumSize(560, 520)
        self.resize(640, 680)
        d = _DIALOG
        self.setStyleSheet(f"QDialog {{ background: {d['bg']}; color: {d['text']}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(10)

        title = QLabel("색상 테마")
        title.setStyleSheet(f"color: {d['primary']}; font-size: 16pt; font-weight: 600;")
        root.addWidget(title)
        hint = QLabel("색상을 바꾸면 미리보기에 즉시 반영됩니다. [적용]을 누르면 앱 전체에 저장됩니다.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {d['text_secondary']};")
        root.addWidget(hint)

        root.addWidget(self._build_preview())
        root.addWidget(self._build_tabs(), stretch=1)
        root.addLayout(self._build_footer())

        self._update_preview()

    def _build_preview(self) -> QFrame:
        d = _DIALOG
        outer = QFrame()
        outer.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        cap = QLabel("미리보기")
        cap.setStyleSheet(f"color: {d['text_muted']}; font-size: 8pt; font-weight: 600;")
        layout.addWidget(cap)

        box = QFrame()
        box.setObjectName("PreviewBox")
        box.setStyleSheet(
            f"QFrame#PreviewBox {{ border: 1px solid {d['preview_border']}; border-radius: 4px; }}"
        )
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(4)

        self._preview_toolbar = QLabel("  상단 메뉴 / 툴바  ")
        self._preview_header = QLabel("  열 A          열 B  ")
        self._preview_row1 = QLabel("  샘플 값 1      샘플 값 2  ")
        self._preview_row2 = QLabel("  샘플 값 3      샘플 값 4  ")
        self._preview_status = QLabel("  하단 상태바  ")
        for widget in (
            self._preview_toolbar,
            self._preview_header,
            self._preview_row1,
            self._preview_row2,
            self._preview_status,
        ):
            widget.setContentsMargins(8, 4, 8, 4)
            box_layout.addWidget(widget)
        layout.addWidget(box)
        return outer

    def _build_tabs(self) -> QTabWidget:
        d = _DIALOG
        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: 1px solid {d['border']}; background: {d['bg']}; }}
            QTabBar::tab {{
                background: {d['surface']}; color: {d['text_secondary']};
                padding: 8px 14px; margin-right: 2px; border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{ background: {d['surface_hover']}; color: {d['text']}; }}
            """
        )
        for group_name, items in THEME_GROUPS:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet(f"background: {d['bg']};")
            inner = QWidget()
            inner_layout = QVBoxLayout(inner)
            inner_layout.setSpacing(6)
            inner_layout.setContentsMargins(4, 8, 4, 8)
            for key, label in items:
                initial = self._draft.get(key, DEFAULT_COLORS[key])
                row = _ColorRowWidget(key, label, initial, inner)
                row.color_changed.connect(self._sync_from_rows)
                self._rows[key] = row
                inner_layout.addWidget(row)
            inner_layout.addStretch()
            scroll.setWidget(inner)
            tabs.addTab(scroll, group_name)
        return tabs

    def _build_footer(self) -> QHBoxLayout:
        d = _DIALOG
        row = QHBoxLayout()
        reset_btn = QPushButton("기본값 복원")
        reset_btn.clicked.connect(self._reset_defaults)
        reset_btn.setStyleSheet(
            f"background: {d['surface']}; color: {d['text']}; border: 1px solid {d['border']}; padding: 8px 14px;"
        )
        row.addWidget(reset_btn)
        row.addStretch()
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            f"background: {d['surface']}; color: {d['text']}; border: 1px solid {d['border']}; padding: 8px 14px;"
        )
        apply_btn = QPushButton("적용")
        apply_btn.clicked.connect(self._apply)
        apply_btn.setStyleSheet(
            f"QPushButton {{ background: {d['primary']}; color: #ffffff; border: none; "
            f"padding: 8px 18px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {d['primary_hover']}; }}"
        )
        row.addWidget(cancel_btn)
        row.addWidget(apply_btn)
        return row

    def _color(self, key: str) -> str:
        fb = DEFAULT_COLORS[key]
        value = self._draft.get(key, fb)
        return value if _valid_hex(value) else fb

    def _update_preview(self) -> None:
        text = self._color("text")
        self._preview_toolbar.setStyleSheet(
            f"background: {self._color('toolbar_bg')}; color: {text}; padding: 4px 8px;"
        )
        self._preview_header.setStyleSheet(
            f"background: {self._color('header_bg')}; color: {self._color('header_fg')}; "
            f"padding: 4px 8px; font-weight: 600;"
        )
        self._preview_row1.setStyleSheet(
            f"background: {self._color('surface')}; color: {text}; padding: 4px 8px;"
        )
        self._preview_row2.setStyleSheet(
            f"background: {self._color('row_alt')}; color: {text}; padding: 4px 8px;"
        )
        self._preview_status.setStyleSheet(
            f"background: {self._color('status_bg')}; color: {self._color('text_muted')}; padding: 4px 8px;"
        )

    def _sync_from_rows(self) -> None:
        for key, row in self._rows.items():
            color = row.get_color()
            if _valid_hex(color):
                self._draft[key] = color.lower()
        self._update_preview()

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "기본값 복원",
            "모든 색상을 기본값으로 되돌릴까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._draft = deepcopy(DEFAULT_COLORS)
        for key, row in self._rows.items():
            row.set_color(DEFAULT_COLORS[key])
        self._update_preview()

    def _apply(self) -> None:
        for key, row in self._rows.items():
            color = row.get_color().strip()
            if not _valid_hex(color):
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    f"'{key}' 색상 코드가 올바르지 않습니다.\n예: #1a2b3c",
                )
                return
            self._draft[key] = color.lower()
        for key in DEFAULT_COLORS:
            COLORS[key] = self._draft[key]
        save_theme_config()
        self._on_apply()
        self.accept()


def show_design_settings_dialog(parent: QWidget | None, on_apply: Callable[[], None]) -> None:
    QtDesignSettingsDialog(parent, on_apply).exec()
