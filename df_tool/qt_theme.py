"""PyQt6 공통 스타일 — theme.COLORS 기반."""
from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QComboBox, QFrame, QLabel, QPushButton, QSizePolicy

from df_tool.theme import COLORS
from df_tool.ui_fonts import monospace_font_family, ui_font_css_stack


def monospace_qfont(point_size: int = 10) -> QFont:
    """코드/로그용 모노스페이스 (Mac=Menlo, Windows=Consolas, Linux=DejaVu)."""
    font = QFont(monospace_font_family(), point_size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def app_stylesheet() -> str:
    c = COLORS
    ui_font = ui_font_css_stack()
    return f"""
    QMainWindow, QWidget {{
        background: {c['bg']};
        color: {c['text']};
        font-family: {ui_font};
        font-size: 10pt;
    }}
    QPushButton {{
        background: {c['surface']};
        color: {c['text']};
        border: 1px solid {c['border_subtle']};
        border-radius: 4px;
        padding: 5px 12px;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background: {c['surface_alt']};
        border-color: {c['border']};
    }}
    QPushButton:pressed {{
        background: {c['primary_soft']};
    }}
    QPushButton:disabled {{
        color: {c['text_muted']};
        background: {c['surface']};
    }}
    QPushButton#PrimaryButton {{
        background: {c['primary']};
        color: {c['text']};
        border-color: {c['primary_hover']};
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background: {c['primary_hover']};
    }}
    QComboBox {{
        background: {c['surface']};
        color: {c['text']};
        border: 1px solid {c['border_subtle']};
        border-radius: 4px;
        padding: 4px 28px 4px 8px;
        min-height: 22px;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 22px;
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background: {c['surface']};
        color: {c['text']};
        border: 1px solid {c['border']};
        selection-background-color: {c['row_selected']};
    }}
    QLineEdit, QPlainTextEdit {{
        background: {c['surface_alt']};
        color: {c['text']};
        border: 1px solid {c['border_subtle']};
        border-radius: 4px;
        padding: 4px 8px;
        selection-background-color: {c['row_selected']};
    }}
    QCheckBox {{
        spacing: 6px;
        color: {c['text_secondary']};
    }}
    QStatusBar {{
        background: {c['status_bg']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border_subtle']};
    }}
    QSplitter::handle {{
        background: {c['border_subtle']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    """


def toolbar_frame_style() -> str:
    c = COLORS
    return (
        f"QFrame#ToolbarFrame {{ background: {c['toolbar_bg']}; "
        f"border: 1px solid {c['border_subtle']}; border-radius: 6px; }}"
    )


def card_frame_style() -> str:
    c = COLORS
    return (
        f"QFrame#CardFrame {{ background: {c['surface']}; "
        f"border: 1px solid {c['border_subtle']}; border-radius: 6px; }}"
    )


def separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setStyleSheet(f"color: {COLORS['border_subtle']}; max-width: 1px;")
    line.setFixedWidth(1)
    return line


def muted_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 0 2px;")
    return lbl


def title_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600; font-size: 11pt;")
    return lbl


def tagline_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-left: 6px;")
    return lbl


def primary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("PrimaryButton")
    return btn


def nav_button(text: str, *, active: bool = False) -> QPushButton:
    btn = QPushButton(text)
    style_nav_button(btn, active=active)
    btn.setCursor(btn.cursor())
    return btn


def style_nav_button(btn: QPushButton, *, active: bool) -> None:
    c = COLORS
    if active:
        btn.setStyleSheet(
            f"QPushButton {{ background: {c['primary_soft']}; color: {c['primary']}; "
            f"border: 1px solid {c['primary_light']}; border-radius: 6px; "
            f"padding: 6px 16px; font-weight: 600; }}"
        )
    else:
        btn.setStyleSheet(
            f"QPushButton {{ background: {c['surface']}; color: {c['text_secondary']}; "
            f"border: 1px solid {c['border_subtle']}; border-radius: 6px; "
            f"padding: 6px 16px; }}"
            f"QPushButton:hover {{ background: {c['surface_alt']}; color: {c['text']}; }}"
        )


def configure_sheet_combo(combo: QComboBox) -> None:
    combo.setMinimumWidth(168)
    combo.setMaximumWidth(320)
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(12)
    combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)


def resize_sheet_combo(combo: QComboBox) -> None:
    fm = combo.fontMetrics()
    texts = [combo.itemText(i) for i in range(combo.count())] or ["해당 없음"]
    pad = 44
    max_text = max(fm.horizontalAdvance(t) for t in texts)
    combo.setMinimumWidth(max(168, min(max_text + pad, 320)))
