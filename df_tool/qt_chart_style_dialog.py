"""분석 차트 꾸미기 다이얼로그."""
from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

from df_tool.chart_style import (
    CMAP_OPTIONS,
    LEGEND_POSITIONS,
    ChartStyle,
    default_chart_style,
    save_chart_style,
)
from df_tool.theme import COLORS


def _valid_hex(value: str) -> bool:
    text = value.strip()
    return len(text) == 7 and text.startswith("#") and all(c in "0123456789abcdef#" for c in text.lower())


class _ColorRow(QFrame):
    def __init__(self, label: str, initial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(label))
        self._entry = QLineEdit(initial)
        self._entry.setMaxLength(7)
        self._swatch = QPushButton()
        self._swatch.setFixedSize(36, 22)
        self._swatch.clicked.connect(self._pick)
        pick = QPushButton("선택")
        pick.clicked.connect(self._pick)
        row.addWidget(self._swatch)
        row.addWidget(self._entry, stretch=1)
        row.addWidget(pick)
        self._entry.textChanged.connect(self._refresh_swatch)
        self._refresh_swatch()

    def _refresh_swatch(self) -> None:
        color = self.get_color() if _valid_hex(self.get_color()) else COLORS["primary"]
        self._swatch.setStyleSheet(f"background:{color}; border:1px solid {COLORS['border']};")

    def _pick(self) -> None:
        initial = QColor(self.get_color()) if _valid_hex(self.get_color()) else QColor(COLORS["primary"])
        chosen = QColorDialog.getColor(initial, self, "색상 선택")
        if chosen.isValid():
            self._entry.setText(chosen.name().lower())

    def get_color(self) -> str:
        return self._entry.text().strip()

    def set_color(self, value: str) -> None:
        self._entry.setText(value)


class QtChartStyleDialog(QDialog):
    def __init__(self, parent: QWidget | None, style: ChartStyle) -> None:
        super().__init__(parent)
        self.setWindowTitle("차트 꾸미기")
        self.setModal(True)
        self.resize(520, 560)
        self._style = deepcopy(style)
        self._result: ChartStyle | None = None
        self._build_ui()
        self.setStyleSheet(
            f"QDialog {{ background: {COLORS['surface']}; color: {COLORS['text']}; }}"
            f"QLabel {{ color: {COLORS['text_secondary']}; }}"
            f"QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ "
            f"background: {COLORS['surface_alt']}; color: {COLORS['text']}; "
            f"border: 1px solid {COLORS['border']}; padding: 4px; }}"
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint = QLabel("분석 탭의 모든 차트에 적용됩니다. 저장 후 현재 차트가 다시 그려집니다.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        tabs = QTabWidget()
        tabs.addTab(self._build_color_tab(), "색상")
        tabs.addTab(self._build_display_tab(), "표시·레이아웃")
        tabs.addTab(self._build_cmap_tab(), "색상맵")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox()
        reset_btn = QPushButton("기본값 복원")
        reset_btn.clicked.connect(self._reset_defaults)
        buttons.addButton(reset_btn, QDialogButtonBox.ButtonRole.ResetRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("적용")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_color_tab(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        s = self._style
        self._colors = {
            "color_primary": _ColorRow("막대·산점도 (주색)", s.color_primary),
            "color_accent": _ColorRow("추세선·강조 (보조색)", s.color_accent),
            "color_fill": _ColorRow("박스·바이올린 채움", s.color_fill),
            "color_edge": _ColorRow("테두리·눈금", s.color_edge),
            "color_warning": _ColorRow("결측·경고 막대", s.color_warning),
            "color_text": _ColorRow("제목·축 글자", s.color_text),
            "color_muted": _ColorRow("안내·빈 데이터", s.color_muted),
            "figure_bg": _ColorRow("차트 배경", s.figure_bg),
            "axes_bg": _ColorRow("플롯 영역 배경", s.axes_bg),
            "grid_color": _ColorRow("격자선", s.grid_color),
        }
        for row in self._colors.values():
            form.addRow(row)
        scroll.setWidget(inner)
        outer = QVBoxLayout(page)
        outer.addWidget(scroll)
        return page

    def _build_display_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        s = self._style
        self._show_title = QCheckBox("차트 제목 표시")
        self._show_title.setChecked(s.show_title)
        form.addRow(self._show_title)
        self._title_override = QLineEdit(s.title_override)
        self._title_override.setPlaceholderText("비우면 데이터·차트 종류로 자동 생성")
        form.addRow("제목 직접 입력:", self._title_override)
        self._title_font = QSpinBox()
        self._title_font.setRange(8, 24)
        self._title_font.setValue(s.title_font_size)
        form.addRow("제목 글자 크기:", self._title_font)
        self._label_font = QSpinBox()
        self._label_font.setRange(7, 18)
        self._label_font.setValue(s.label_font_size)
        form.addRow("축 이름 크기:", self._label_font)
        self._tick_font = QSpinBox()
        self._tick_font.setRange(6, 16)
        self._tick_font.setValue(s.tick_font_size)
        form.addRow("눈금 글자 크기:", self._tick_font)
        self._show_grid = QCheckBox("격자선 표시")
        self._show_grid.setChecked(s.show_grid)
        form.addRow(self._show_grid)
        self._grid_alpha = QDoubleSpinBox()
        self._grid_alpha.setRange(0.0, 1.0)
        self._grid_alpha.setSingleStep(0.05)
        self._grid_alpha.setValue(s.grid_alpha)
        form.addRow("격자 투명도:", self._grid_alpha)
        self._bar_alpha = QDoubleSpinBox()
        self._bar_alpha.setRange(0.1, 1.0)
        self._bar_alpha.setSingleStep(0.05)
        self._bar_alpha.setValue(s.bar_alpha)
        form.addRow("막대 투명도:", self._bar_alpha)
        self._scatter_alpha = QDoubleSpinBox()
        self._scatter_alpha.setRange(0.1, 1.0)
        self._scatter_alpha.setSingleStep(0.05)
        self._scatter_alpha.setValue(s.scatter_alpha)
        form.addRow("산점도 투명도:", self._scatter_alpha)
        self._scatter_size = QSpinBox()
        self._scatter_size.setRange(4, 80)
        self._scatter_size.setValue(s.scatter_size)
        form.addRow("산점도 점 크기:", self._scatter_size)
        self._x_rotation = QSpinBox()
        self._x_rotation.setRange(0, 90)
        self._x_rotation.setValue(s.x_label_rotation)
        form.addRow("X축 라벨 기울기(°):", self._x_rotation)
        self._legend = QComboBox()
        for code, label in LEGEND_POSITIONS.items():
            self._legend.addItem(label, code)
        idx = self._legend.findData(s.legend_position)
        if idx >= 0:
            self._legend.setCurrentIndex(idx)
        form.addRow("범례 위치:", self._legend)
        self._show_colorbar = QCheckBox("컬러바(색상 막대) 표시")
        self._show_colorbar.setChecked(s.show_colorbar)
        form.addRow(self._show_colorbar)
        self._dpi = QSpinBox()
        self._dpi.setRange(72, 200)
        self._dpi.setValue(s.dpi)
        form.addRow("해상도 (DPI):", self._dpi)
        return page

    def _build_cmap_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        s = self._style
        self._cmap_heat = QComboBox()
        self._cmap_count = QComboBox()
        self._cmap_hex = QComboBox()
        for combo, val in (
            (self._cmap_heat, s.cmap_heatmap),
            (self._cmap_count, s.cmap_count),
            (self._cmap_hex, s.cmap_hexbin),
        ):
            for name in CMAP_OPTIONS:
                combo.addItem(name, name)
            idx = combo.findData(val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        form.addRow("상관·히트맵:", self._cmap_heat)
        form.addRow("교차표·밀도:", self._cmap_count)
        form.addRow("육각 밀도(hexbin):", self._cmap_hex)
        return page

    def _reset_defaults(self) -> None:
        if QMessageBox.question(self, "기본값", "차트 스타일을 기본값으로 되돌릴까요?") != QMessageBox.StandardButton.Yes:
            return
        from df_tool.chart_style import reset_chart_style

        self._result = reset_chart_style()
        self.accept()

    def _apply(self) -> None:
        for key, row in self._colors.items():
            color = row.get_color()
            if not _valid_hex(color):
                QMessageBox.warning(self, "색상 오류", f"'{key}' 색상이 올바른 #rrggbb 형식이 아닙니다.")
                return
            setattr(self._style, key, color.lower())
        self._style.show_title = self._show_title.isChecked()
        self._style.title_override = self._title_override.text().strip()
        self._style.title_font_size = self._title_font.value()
        self._style.label_font_size = self._label_font.value()
        self._style.tick_font_size = self._tick_font.value()
        self._style.show_grid = self._show_grid.isChecked()
        self._style.grid_alpha = self._grid_alpha.value()
        self._style.bar_alpha = self._bar_alpha.value()
        self._style.scatter_alpha = self._scatter_alpha.value()
        self._style.scatter_size = self._scatter_size.value()
        self._style.x_label_rotation = self._x_rotation.value()
        self._style.legend_position = self._legend.currentData()
        self._style.show_colorbar = self._show_colorbar.isChecked()
        self._style.dpi = self._dpi.value()
        self._style.cmap_heatmap = self._cmap_heat.currentData()
        self._style.cmap_count = self._cmap_count.currentData()
        self._style.cmap_hexbin = self._cmap_hex.currentData()
        save_chart_style(self._style)
        self._result = deepcopy(self._style)
        self.accept()

    def get_style(self) -> ChartStyle | None:
        return self._result


def qt_chart_style_dialog(parent: QWidget | None, style: ChartStyle) -> ChartStyle | None:
    dlg = QtChartStyleDialog(parent, style)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.get_style()
