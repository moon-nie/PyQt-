"""PyQt 분석 탭 — EDA 개요·차트·결측·이상치."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFileDialog,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from df_tool.analysis_deps import (
    analysis_deps_message,
    charts_available,
    charts_deps_message,
    feature_requirement_message,
    scipy_available,
    sklearn_available,
)
from df_tool.qt_dependency import gate_combo_item, gate_widget, require
from df_tool.chart_style import ChartStyle, load_chart_style
from df_tool.eda_report import build_eda_html
from df_tool.qt_chart_style_dialog import qt_chart_style_dialog
from df_tool.analysis import (
    PLOT_MAX_ROWS,
    bivariate_chart_options,
    bivariate_crosstab_table,
    bivariate_numeric_correlation,
    bivariate_pair_info,
    column_kind,
    configure_matplotlib_font,
    compute_pca,
    correlation_matrix,
    count_outlier_rows,
    default_bivariate_pair,
    default_univariate_column,
    eda_overview,
    format_stat_number,
    knn_fill_preview,
    missing_summary,
    nice_axis_limits,
    numeric_columns,
    outlier_summary,
    sample_for_plot,
    suggest_bivariate_chart,
    suggest_univariate_chart,
    univariate_categorical_freq,
    univariate_categorical_stats,
    univariate_chart_options,
    univariate_numeric_stats,
)
from df_tool.operations import drop_outlier_rows, fill_na_knn, fill_na_mice, resolve_column_key
from df_tool.performance import should_defer_analysis_charts
from df_tool.qt_analysis_worker import run_analysis_task
from df_tool.qt_theme import primary_button
from df_tool.theme import COLORS

_CHART_LABELS = {
    "auto": "자동 (추천)",
    "histogram": "히스토그램",
    "kde": "KDE (밀도)",
    "boxplot": "박스플롯",
    "bar": "막대 (빈도)",
    "pie": "파이 (비율)",
    "scatter": "산점도",
    "hexbin": "육각 밀도",
    "corr_line": "산점도+추세선",
    "box": "박스 (그룹별)",
    "violin": "바이올린",
    "bar_mean": "그룹 평균 막대",
    "heatmap": "교차표 히트맵",
    "stacked_bar": "누적 막대",
    "grouped_bar": "그룹 막대",
    "corr_matrix": "상관 행렬",
}


def _readonly_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _truncate_chart_label(value: str, *, max_len: int = 14) -> str:
    """차트 축 라벨이 너무 길어 그래프를 덮지 않도록 짧게 표시."""
    text = str(value)
    return text if len(text) <= max_len else f"{text[: max_len - 1]}…"


class MplCanvas(FigureCanvas):
    def __init__(
        self,
        parent=None,
        chart_style: ChartStyle | None = None,
        *,
        width: float | None = None,
        height: float = 4,
    ) -> None:
        self._chart_style = chart_style
        style = chart_style or load_chart_style()
        fig_w = width if width is not None else style.figure_width
        configure_matplotlib_font()
        self.fig = Figure(figsize=(fig_w, height), dpi=style.dpi)
        self.fig.patch.set_facecolor(style.figure_bg)
        super().__init__(self.fig)
        self.setParent(parent)

    def _style(self) -> ChartStyle:
        return self._chart_style or load_chart_style()

    def clear_axes(self) -> None:
        style = self._style()
        self.fig.clear()
        self.fig.patch.set_facecolor(style.figure_bg)

    def begin_chart(self):
        """축을 비우고 단일 subplot을 만들어 스타일을 적용한 ``ax``를 반환한다.

        대부분의 ``_draw_*`` 차트가 공유하는 시작 보일러플레이트.
        (격자형 Pair plot처럼 여러 subplot이 필요한 경우는 직접 구성한다.)
        """
        self.clear_axes()
        ax = self.fig.add_subplot(111)
        self.style_axes(ax)
        return ax

    def finish_chart(self) -> None:
        """레이아웃을 정리하고 캔버스를 다시 그린다(차트 마무리 보일러플레이트)."""
        self.fig.tight_layout()
        self.draw()

    def style_axes(self, ax) -> None:
        style = self._style()
        ax.set_facecolor(style.axes_bg)
        ax.tick_params(
            colors=style.color_text,
            labelsize=style.tick_font_size,
            width=1,
            length=4,
        )
        ax.xaxis.label.set_color(style.color_text)
        ax.yaxis.label.set_color(style.color_text)
        ax.title.set_color(style.color_text)
        ax.title.set_fontsize(style.title_font_size)
        ax.xaxis.label.set_fontsize(style.label_font_size)
        ax.yaxis.label.set_fontsize(style.label_font_size)
        if style.show_grid:
            ax.grid(
                True,
                color=style.grid_color,
                alpha=style.grid_alpha,
                linestyle="--",
                linewidth=0.8,
            )
        else:
            ax.grid(False)
        for spine in ax.spines.values():
            spine.set_color(style.color_border)
            spine.set_linewidth(1.0)


class AnalysisPanel(QWidget):
    def __init__(
        self,
        *,
        get_dataframe: Callable[[], pd.DataFrame | None],
        on_apply: Callable[[pd.DataFrame, str], None],
        on_log: Callable[[str, str, str | None], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._get_df = get_dataframe
        self._on_apply = on_apply
        self._on_log = on_log
        self._df: pd.DataFrame | None = None
        self._charts_dirty = True
        self._deps_ok = charts_available()
        self._worker_busy = False
        self._analysis_token = 0
        self._chart_style = load_chart_style()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._title_label = QLabel("분석 — 데이터를 열면 EDA를 시작할 수 있습니다")
        self._title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")
        header.addWidget(self._title_label)
        header.addStretch()
        eda_btn = primary_button("EDA 요약 실행")
        eda_btn.clicked.connect(self._run_eda_summary)
        header.addWidget(eda_btn)
        report_btn = QPushButton("HTML 리포트")
        report_btn.clicked.connect(self._export_html_report)
        header.addWidget(report_btn)
        style_btn = QPushButton("차트 꾸미기")
        style_btn.clicked.connect(self._open_chart_style_dialog)
        header.addWidget(style_btn)
        refresh_btn = QPushButton("분석 새로고침")
        refresh_btn.clicked.connect(lambda: self.refresh(charts=True, force_charts=True))
        header.addWidget(refresh_btn)
        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet(f"color: {COLORS['accent']};")
        self._progress_label.hide()
        header.addWidget(self._progress_label)
        layout.addLayout(header)

        self._dep_banner = QLabel("")
        self._dep_banner.setWordWrap(True)
        self._dep_banner.hide()
        layout.addWidget(self._dep_banner)
        self._update_dep_banner()

        self._large_banner = QFrame()
        self._large_banner.setStyleSheet(
            f"background: {COLORS['primary_soft']}; border: 1px solid {COLORS['border']}; border-radius: 4px;"
        )
        large_row = QHBoxLayout(self._large_banner)
        large_row.setContentsMargins(8, 6, 8, 6)
        self._large_banner_label = QLabel(self._defer_message())
        self._large_banner_label.setWordWrap(True)
        self._large_banner_label.setStyleSheet(f"color: {COLORS['warning']};")
        large_row.addWidget(self._large_banner_label, stretch=1)
        draw_now_btn = QPushButton("지금 그리기")
        draw_now_btn.setToolTip("대용량 데이터도 5,000행 샘플 기준으로 차트를 그립니다.")
        draw_now_btn.clicked.connect(lambda: self.refresh(charts=True, force_charts=True))
        large_row.addWidget(draw_now_btn)
        self._large_banner.hide()
        layout.addWidget(self._large_banner)

        self._tabs = QTabWidget()
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.addTab(self._build_overview_tab(), "개요")
        self._tabs.addTab(self._build_univariate_tab(), "단변량")
        self._tabs.addTab(self._build_bivariate_tab(), "이변량")
        self._tabs.addTab(self._build_multivariate_tab(), "다변량")
        self._tabs.addTab(self._build_missing_tab(), "결측·대체")
        self._tabs.addTab(self._build_outlier_tab(), "이상치")
        layout.addWidget(self._tabs, stretch=1)
        self._sync_dependency_controls()

    def _build_axis_row(self, prefix: str) -> QHBoxLayout:
        row = QHBoxLayout()
        auto = QCheckBox("축 범위 자동")
        auto.setChecked(True)
        auto.toggled.connect(lambda checked: self._on_axis_auto_toggled(prefix, checked))
        row.addWidget(auto)
        row.addWidget(QLabel("X"))
        xmin = QDoubleSpinBox()
        xmin.setRange(-1e15, 1e15)
        xmin.setDecimals(4)
        xmin.setEnabled(False)
        row.addWidget(xmin)
        row.addWidget(QLabel("~"))
        xmax = QDoubleSpinBox()
        xmax.setRange(-1e15, 1e15)
        xmax.setDecimals(4)
        xmax.setEnabled(False)
        row.addWidget(xmax)
        row.addWidget(QLabel("Y"))
        ymin = QDoubleSpinBox()
        ymin.setRange(-1e15, 1e15)
        ymin.setDecimals(4)
        ymin.setEnabled(False)
        row.addWidget(ymin)
        row.addWidget(QLabel("~"))
        ymax = QDoubleSpinBox()
        ymax.setRange(-1e15, 1e15)
        ymax.setDecimals(4)
        ymax.setEnabled(False)
        row.addWidget(ymax)
        row.addStretch()
        setattr(self, f"_{prefix}_axis_auto", auto)
        setattr(self, f"_{prefix}_xmin", xmin)
        setattr(self, f"_{prefix}_xmax", xmax)
        setattr(self, f"_{prefix}_ymin", ymin)
        setattr(self, f"_{prefix}_ymax", ymax)
        if prefix == "uni":
            self._uni_horizontal = False
        return row

    def _on_axis_auto_toggled(self, prefix: str, checked: bool) -> None:
        for name in ("xmin", "xmax", "ymin", "ymax"):
            getattr(self, f"_{prefix}_{name}").setEnabled(not checked)

    def _resolve_chart_title(self, default: str, local_override: str = "") -> str | None:
        local = local_override.strip()
        base = local if local else default
        return self._chart_style.resolve_title(base)

    def _set_chart_title(self, ax, default: str, *, local_override: str = "") -> None:
        title = self._resolve_chart_title(default, local_override)
        if title:
            ax.set_title(title, pad=10, fontsize=self._chart_style.title_font_size)

    def _open_chart_style_dialog(self) -> None:
        updated = qt_chart_style_dialog(self, self._chart_style)
        if updated is None:
            return
        self._chart_style = updated
        for attr in (
            "_overview_canvas",
            "_uni_canvas",
            "_bi_canvas",
            "_multi_canvas",
            "_missing_canvas",
            "_outlier_canvas",
        ):
            canvas = getattr(self, attr, None)
            if canvas is not None:
                canvas._chart_style = self._chart_style
        self._charts_dirty = True
        self.refresh(charts=True, force_charts=True)

    def _set_progress(self, message: str | None) -> None:
        if message:
            self._progress_label.setText(message)
            self._progress_label.show()
        else:
            self._progress_label.hide()

    def invalidate_pending_work(self) -> None:
        """데이터가 외부에서 바뀌면 이전 백그라운드 분석 결과를 버립니다."""
        self._analysis_token += 1

    def _export_html_report(self) -> None:
        if self._df is None or self._df.empty:
            QMessageBox.information(self, "HTML 리포트", "먼저 데이터를 열어 주세요.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "HTML EDA 리포트 저장", "eda_report.html", "HTML 파일 (*.html)"
        )
        if not path:
            return
        try:
            html = build_eda_html(self._df)
            Path(path).write_text(html, encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "HTML 리포트", str(exc))
            if self._on_log:
                self._on_log("error", "HTML 리포트 저장 실패", str(exc))
            return
        if self._on_log:
            self._on_log("success", f"HTML 리포트 저장: {Path(path).name}", path)
        QMessageBox.information(self, "HTML 리포트", f"저장 완료:\n{path}")

    def _toggle_uni_orientation(self) -> None:
        self._uni_horizontal = not getattr(self, "_uni_horizontal", False)
        if self._df is not None:
            self._draw_univariate()

    def _swap_bi_axes(self) -> None:
        x = self._bi_x.currentText()
        y = self._bi_y.currentText()
        self._bi_x.blockSignals(True)
        self._bi_y.blockSignals(True)
        self._bi_x.setCurrentText(y)
        self._bi_y.setCurrentText(x)
        self._bi_x.blockSignals(False)
        self._bi_y.blockSignals(False)
        self._on_bi_cols_changed()
        if self._df is not None:
            self._draw_bivariate()

    def _format_numeric_axis(self, ax, *, axis: str = "both") -> None:
        from matplotlib.ticker import FuncFormatter, ScalarFormatter

        def _tick_fmt(val, _pos):
            return format_stat_number(val, max_decimals=3)

        fmt = FuncFormatter(_tick_fmt)
        if axis in {"both", "x"}:
            ax.xaxis.set_major_formatter(fmt)
        if axis in {"both", "y"}:
            sf = ScalarFormatter(useOffset=False)
            sf.set_scientific(False)
            ax.yaxis.set_major_formatter(fmt)

    def _set_spin_limits(self, prefix: str, xlo, xhi, ylo, yhi) -> None:
        for name, val in (("xmin", xlo), ("xmax", xhi), ("ymin", ylo), ("ymax", yhi)):
            spin = getattr(self, f"_{prefix}_{name}")
            spin.blockSignals(True)
            spin.setValue(float(val))
            spin.blockSignals(False)

    def _apply_axis_limits(
        self,
        ax,
        prefix: str,
        *,
        x_vals=None,
        y_vals=None,
    ) -> None:
        auto = getattr(self, f"_{prefix}_axis_auto").isChecked()
        if auto:
            xlo = xhi = ylo = yhi = None
            if x_vals is not None:
                xs = pd.Series(x_vals).dropna()
                if len(xs):
                    xlo, xhi = nice_axis_limits(float(xs.min()), float(xs.max()))
            if y_vals is not None:
                ys = pd.Series(y_vals).dropna()
                if len(ys):
                    ylo, yhi = nice_axis_limits(float(ys.min()), float(ys.max()))
                    if float(ys.min()) >= 0 and ylo < 0:
                        ylo = 0
            if xlo is not None and xhi is not None:
                ax.set_xlim(xlo, xhi)
            if ylo is not None and yhi is not None:
                ax.set_ylim(ylo, yhi)
            self._set_spin_limits(
                prefix,
                xlo if xlo is not None else getattr(self, f"_{prefix}_xmin").value(),
                xhi if xhi is not None else getattr(self, f"_{prefix}_xmax").value(),
                ylo if ylo is not None else getattr(self, f"_{prefix}_ymin").value(),
                yhi if yhi is not None else getattr(self, f"_{prefix}_ymax").value(),
            )
        else:
            ax.set_xlim(
                getattr(self, f"_{prefix}_xmin").value(),
                getattr(self, f"_{prefix}_xmax").value(),
            )
            ax.set_ylim(
                getattr(self, f"_{prefix}_ymin").value(),
                getattr(self, f"_{prefix}_ymax").value(),
            )

    def _build_overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        self._overview_table = QTableWidget(0, 8)
        self._overview_table.setHorizontalHeaderLabels(
            ["컬럼", "종류", "타입", "결측", "결측%", "고유값", "평균", "표준편차"]
        )
        self._overview_table.horizontalHeader().setStretchLastSection(True)
        self._overview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        splitter.addWidget(self._overview_table)
        self._overview_canvas = MplCanvas(page, self._chart_style, height=3.8)
        self._overview_canvas.setMinimumHeight(140)
        self._overview_canvas.setToolTip("개요 표와 결측 비율 그래프 사이 경계선을 드래그해 높이를 조절할 수 있습니다.")
        splitter.addWidget(self._overview_canvas)
        splitter.setSizes([460, 300])
        self._overview_splitter = splitter
        layout.addWidget(splitter, stretch=1)
        return page

    def _build_univariate_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel("열:"))
        self._uni_col = QComboBox()
        self._uni_col.currentTextChanged.connect(self._on_uni_col_changed)
        row.addWidget(self._uni_col, stretch=1)
        row.addWidget(QLabel("차트:"))
        self._uni_chart = QComboBox()
        row.addWidget(self._uni_chart)
        row.addWidget(QLabel("bins:"))
        self._uni_bins = QSpinBox()
        self._uni_bins.setRange(5, 100)
        self._uni_bins.setValue(20)
        row.addWidget(self._uni_bins)
        row.addWidget(QLabel("top-N:"))
        self._uni_topn = QSpinBox()
        self._uni_topn.setRange(5, 50)
        self._uni_topn.setValue(15)
        row.addWidget(self._uni_topn)
        draw_btn = QPushButton("분석·차트")
        draw_btn.clicked.connect(self._draw_univariate)
        row.addWidget(draw_btn)
        swap_btn = QPushButton("가로↔세로")
        swap_btn.setToolTip("값 축과 빈도 축을 바꿉니다 (막대·히스토그램)")
        swap_btn.clicked.connect(self._toggle_uni_orientation)
        row.addWidget(swap_btn)
        layout.addLayout(row)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("제목:"))
        self._uni_title = QLineEdit()
        self._uni_title.setPlaceholderText("비우면 자동 (차트 꾸미기에서 전역 제목도 설정 가능)")
        title_row.addWidget(self._uni_title, stretch=1)
        layout.addLayout(title_row)
        layout.addLayout(self._build_axis_row("uni"))
        self._uni_kind_label = QLabel("")
        self._uni_kind_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self._uni_kind_label)
        self._uni_sample_label = QLabel("")
        self._uni_sample_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self._uni_sample_label)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._uni_stats_table = QTableWidget(0, 2)
        self._uni_stats_table.setHorizontalHeaderLabels(["통계", "값"])
        self._uni_stats_table.horizontalHeader().setStretchLastSection(True)
        self._uni_stats_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        splitter.addWidget(self._uni_stats_table)
        self._uni_canvas = MplCanvas(page, self._chart_style, height=4)
        splitter.addWidget(self._uni_canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)
        return page

    def _build_bivariate_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel("X:"))
        self._bi_x = QComboBox()
        self._bi_x.currentTextChanged.connect(self._on_bi_cols_changed)
        row.addWidget(self._bi_x, stretch=1)
        row.addWidget(QLabel("Y:"))
        self._bi_y = QComboBox()
        self._bi_y.currentTextChanged.connect(self._on_bi_cols_changed)
        row.addWidget(self._bi_y, stretch=1)
        row.addWidget(QLabel("차트:"))
        self._bi_chart = QComboBox()
        row.addWidget(self._bi_chart)
        draw_btn = QPushButton("분석·차트")
        draw_btn.clicked.connect(self._draw_bivariate)
        row.addWidget(draw_btn)
        swap_btn = QPushButton("X↔Y 교환")
        swap_btn.clicked.connect(self._swap_bi_axes)
        row.addWidget(swap_btn)
        layout.addLayout(row)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("제목:"))
        self._bi_title = QLineEdit()
        self._bi_title.setPlaceholderText("비우면 자동")
        title_row.addWidget(self._bi_title, stretch=1)
        layout.addLayout(title_row)
        layout.addLayout(self._build_axis_row("bi"))
        self._bi_pair_label = QLabel("")
        self._bi_pair_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self._bi_pair_label)
        self._bi_stats_label = QLabel("")
        self._bi_stats_label.setWordWrap(True)
        self._bi_stats_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self._bi_stats_label)
        self._bi_sample_label = QLabel("")
        self._bi_sample_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self._bi_sample_label)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._bi_table = QTableWidget(0, 0)
        self._bi_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        splitter.addWidget(self._bi_table)
        self._bi_canvas = MplCanvas(page, self._chart_style, height=4)
        splitter.addWidget(self._bi_canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)
        return page

    def _build_multivariate_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel("수치형 열 (다중 선택, 비우면 전체):"))
        self._multi_cols = QListWidget()
        self._multi_cols.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._multi_cols.setMaximumHeight(120)
        row.addWidget(self._multi_cols, stretch=1)
        corr_btn = QPushButton("상관 행렬")
        corr_btn.clicked.connect(self._draw_multivariate)
        row.addWidget(corr_btn)
        pair_btn = QPushButton("Pair plot")
        pair_btn.clicked.connect(self._draw_pair_plot)
        row.addWidget(pair_btn)
        self._pca_btn = QPushButton("PCA")
        self._pca_btn.clicked.connect(self._draw_pca)
        row.addWidget(self._pca_btn)
        layout.addLayout(row)
        self._multi_hint = QLabel("2개 이상 숫자 열 — 상관·Pair plot(4열)·PCA(2D).")
        self._multi_hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self._multi_hint)
        self._multi_canvas = MplCanvas(page, self._chart_style, height=5)
        layout.addWidget(self._multi_canvas, stretch=1)
        return page

    def _build_missing_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("KNN 대체 대상 (숫자 열, 다중 선택):"))
        self._missing_cols = QListWidget()
        self._missing_cols.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        left_layout.addWidget(self._missing_cols)
        knn_row = QHBoxLayout()
        knn_row.addWidget(QLabel("n_neighbors:"))
        self._knn_neighbors = QSpinBox()
        self._knn_neighbors.setRange(1, 15)
        self._knn_neighbors.setValue(5)
        knn_row.addWidget(self._knn_neighbors)
        knn_row.addStretch()
        left_layout.addLayout(knn_row)
        self._missing_preview = QLabel("미리보기: —")
        self._missing_preview.setWordWrap(True)
        self._missing_preview.setStyleSheet(f"color: {COLORS['text_muted']};")
        left_layout.addWidget(self._missing_preview)
        self._knn_preview_btn = QPushButton("미리보기")
        self._knn_preview_btn.clicked.connect(self._preview_knn)
        self._knn_apply_btn = primary_button("KNN 적용")
        self._knn_apply_btn.clicked.connect(self._apply_knn)
        self._mice_apply_btn = QPushButton("MICE 적용")
        self._mice_apply_btn.clicked.connect(self._apply_mice)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._knn_preview_btn)
        btn_row.addWidget(self._knn_apply_btn)
        btn_row.addWidget(self._mice_apply_btn)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)
        self._missing_canvas = MplCanvas(page, self._chart_style, height=3)
        splitter.addWidget(self._missing_canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return page

    def _build_outlier_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        form = QFormLayout()
        self._outlier_method = QComboBox()
        self._outlier_method.addItem("IQR (1.5×)", "iqr")
        self._outlier_method.addItem("Z-score", "zscore")
        self._outlier_method.addItem("Isolation Forest", "isolation_forest")
        form.addRow("방식:", self._outlier_method)
        self._outlier_z = QDoubleSpinBox()
        self._outlier_z.setRange(1.0, 10.0)
        self._outlier_z.setValue(3.0)
        self._outlier_z.setSingleStep(0.5)
        form.addRow("Z 임계값:", self._outlier_z)
        self._outlier_contamination = QDoubleSpinBox()
        self._outlier_contamination.setRange(0.01, 0.5)
        self._outlier_contamination.setValue(0.05)
        self._outlier_contamination.setSingleStep(0.01)
        form.addRow("IF 오염도:", self._outlier_contamination)
        self._outlier_method.currentIndexChanged.connect(self._sync_outlier_option_visibility)
        left_layout.addLayout(form)
        left_layout.addWidget(QLabel("대상 열 (숫자, 다중 선택):"))
        self._outlier_cols = QListWidget()
        self._outlier_cols.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        left_layout.addWidget(self._outlier_cols)
        self._outlier_preview = QLabel("미리보기: —")
        self._outlier_preview.setWordWrap(True)
        self._outlier_preview.setStyleSheet(f"color: {COLORS['text_muted']};")
        left_layout.addWidget(self._outlier_preview)
        self._outlier_preview_btn = QPushButton("미리보기")
        self._outlier_preview_btn.clicked.connect(self._preview_outliers_async)
        if hasattr(self, "_outlier_method"):
            self._sync_outlier_option_visibility()
        self._outlier_apply_btn = primary_button("이상치 행 제거 적용")
        self._outlier_apply_btn.clicked.connect(self._apply_outliers)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._outlier_preview_btn)
        btn_row.addWidget(self._outlier_apply_btn)
        left_layout.addLayout(btn_row)
        self._outlier_sample = QTableWidget(0, 0)
        self._outlier_sample.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        left_layout.addWidget(self._outlier_sample, stretch=1)
        splitter.addWidget(left)
        self._outlier_canvas = MplCanvas(page, self._chart_style, height=3)
        splitter.addWidget(self._outlier_canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return page

    def _update_dep_banner(self) -> None:
        self._deps_ok = charts_available()
        msg = analysis_deps_message()
        if msg:
            self._dep_banner.setText(msg)
            self._dep_banner.setStyleSheet(f"color: {COLORS['warning']}; background: {COLORS['primary_soft']}; padding: 8px; border-radius: 4px;")
            self._dep_banner.show()
        else:
            self._dep_banner.hide()
        self._sync_dependency_controls()

    def _sync_dependency_controls(self) -> None:
        sklearn_ok = sklearn_available()
        scipy_ok = scipy_available()
        for attr in ("_pca_btn", "_knn_apply_btn", "_mice_apply_btn"):
            btn = getattr(self, attr, None)
            if btn is not None:
                gate_widget(btn, sklearn_ok, "sklearn")
        if hasattr(self, "_outlier_method"):
            gate_combo_item(self._outlier_method, "isolation_forest", sklearn_ok, "sklearn")
        if hasattr(self, "_uni_chart"):
            gate_combo_item(self._uni_chart, "kde", scipy_ok, "scipy")
        if hasattr(self, "_outlier_method"):
            self._sync_outlier_option_visibility()

    def refresh_light(self) -> None:
        """메타데이터만 갱신 (차트·무거운 미리보기 생략)."""
        self._analysis_token += 1
        self._update_dep_banner()
        self._df = self._get_df()
        if self._df is None or self._df.empty:
            self._title_label.setText("분석 — 데이터를 열면 EDA를 시작할 수 있습니다")
            self._large_banner.hide()
            return
        n, c = len(self._df), len(self._df.columns)
        self._title_label.setText(f"분석 — {n:,}행 × {c:,}열")
        self._large_banner.setVisible(should_defer_analysis_charts(n, c))
        self._populate_combos()
        self._refresh_overview_table()
        self._charts_dirty = True

    def refresh(self, *, charts: bool = True, force_charts: bool = False) -> None:
        self.refresh_light()
        if charts and self._df is not None and not self._df.empty:
            self._refresh_charts(force=force_charts)
            deferred = should_defer_analysis_charts(len(self._df), len(self._df.columns))
            if force_charts or not deferred:
                self._charts_dirty = False

    def _defer_message(self) -> str:
        return "대용량 데이터 — [분석 새로고침] 또는 각 탭 [분석·차트]로 그리세요 (5,000행 샘플)."

    def _refresh_charts(self, *, force: bool = False) -> None:
        if not self._deps_ok or self._df is None:
            return
        if should_defer_analysis_charts(len(self._df), len(self._df.columns)) and not force:
            msg = self._defer_message()
            if hasattr(self, "_uni_sample_label"):
                self._uni_sample_label.setText(msg)
            if hasattr(self, "_bi_sample_label"):
                self._bi_sample_label.setText(msg)
            return
        self._draw_missing_overview_chart()
        self._draw_missing_chart()
        self._preview_knn()
        self._draw_active_tab_chart()

    def _on_tab_changed(self, _index: int) -> None:
        if self._df is None or not self._deps_ok:
            return
        self._draw_active_tab_chart()

    def _draw_active_tab_chart(self) -> None:
        idx = self._tabs.currentIndex()
        if idx == 1:
            self._draw_univariate()
        elif idx == 2:
            self._draw_bivariate()
        elif idx == 3:
            pass
        elif idx == 4:
            self._draw_missing_chart()
        elif idx == 5:
            if self._df is None:
                return
            cols = self._selected_list_items(self._outlier_cols)
            if not cols:
                cols = numeric_columns(self._df)
            if cols:
                self._draw_outlier_boxplot(cols[0])

    def _sync_outlier_option_visibility(self) -> None:
        method = self._outlier_method.currentData()
        self._outlier_z.setEnabled(method == "zscore")
        self._outlier_contamination.setEnabled(method == "isolation_forest")

    def _run_eda_summary(self) -> None:
        if not self._deps_ok:
            QMessageBox.warning(self, "EDA 요약", charts_deps_message() or "패키지가 없습니다.")
            return
        self.refresh(charts=True, force_charts=True)
        if self._df is None:
            return
        self._tabs.setCurrentIndex(0)
        nums = numeric_columns(self._df) if self._df is not None else []
        if nums:
            self._tabs.setCurrentIndex(1)
            self._uni_col.setCurrentText(nums[0])
            self._draw_univariate()
        if len(nums) >= 2:
            self._tabs.setCurrentIndex(2)
            self._bi_x.setCurrentText(nums[0])
            self._bi_y.setCurrentText(nums[1])
            self._draw_bivariate()
        if len(nums) >= 2:
            self._tabs.setCurrentIndex(3)
            self._draw_multivariate()
        self._tabs.setCurrentIndex(0)

    def _populate_combos(self) -> None:
        if self._df is None:
            return
        cols = [str(c) for c in self._df.columns]
        for combo in (self._uni_col, self._bi_x, self._bi_y):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(cols)
            combo.blockSignals(False)
        default_uni = default_univariate_column(self._df)
        if default_uni:
            idx = self._uni_col.findText(default_uni)
            if idx >= 0:
                self._uni_col.setCurrentIndex(idx)
        x, y = default_bivariate_pair(self._df)
        if x:
            self._bi_x.setCurrentText(x)
        if y:
            self._bi_y.setCurrentText(y)
        self._missing_cols.clear()
        for col in numeric_columns(self._df):
            self._missing_cols.addItem(col)
        self._outlier_cols.clear()
        for col in numeric_columns(self._df):
            self._outlier_cols.addItem(col)
        self._multi_cols.clear()
        for col in numeric_columns(self._df):
            self._multi_cols.addItem(col)
        self._on_uni_col_changed()
        self._on_bi_cols_changed()

    def _refresh_overview_table(self) -> None:
        if self._df is None:
            return
        overview = eda_overview(self._df)
        self._overview_table.setRowCount(len(overview.columns))
        for i, col in enumerate(overview.columns):
            self._overview_table.setItem(i, 0, _readonly_item(col.name))
            self._overview_table.setItem(i, 1, _readonly_item(col.kind))
            self._overview_table.setItem(i, 2, _readonly_item(col.dtype))
            self._overview_table.setItem(i, 3, _readonly_item(f"{col.null_count:,}"))
            self._overview_table.setItem(i, 4, _readonly_item(f"{col.null_pct:.1f}%"))
            self._overview_table.setItem(i, 5, _readonly_item(f"{col.unique_count:,}"))
            self._overview_table.setItem(
                i, 6, _readonly_item(format_stat_number(col.mean) if col.mean is not None else "—")
            )
            self._overview_table.setItem(
                i, 7, _readonly_item(format_stat_number(col.std) if col.std is not None else "—")
            )

    def _refresh_overview(self) -> None:
        self._refresh_overview_table()
        self._draw_missing_overview_chart()

    def _draw_missing_overview_chart(self) -> None:
        if self._df is None:
            return
        data = missing_summary(self._df)[:20]
        canvas = self._overview_canvas
        current_height = canvas.height() if canvas.height() > 0 else 0
        recommended_height = 220 if not data else min(430, max(240, 100 + len(data) * 14))
        draw_height = current_height if current_height >= 140 else recommended_height
        canvas.fig.set_size_inches(canvas.fig.get_size_inches()[0], draw_height / canvas.fig.dpi, forward=True)
        ax = canvas.begin_chart()
        st = self._chart_style
        if not data:
            ax.text(0.5, 0.5, "결측치 없음", ha="center", va="center", color=st.color_muted)
        else:
            names = [_truncate_chart_label(d[0]) for d in data]
            pcts = [d[2] for d in data]
            ax.barh(
                names, pcts,
                color=st.color_primary, edgecolor=st.color_border, alpha=st.bar_alpha,
            )
            ax.set_xlabel("결측 비율 (%)")
            self._set_chart_title(ax, "열별 결측 비율 (상위 20)")
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=max(6, st.tick_font_size - 2), pad=2)
            ax.margins(y=0.02)
            self._apply_axis_limits(ax, "uni", x_vals=pcts)
            self._format_numeric_axis(ax, axis="x")
            canvas.fig.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.15)
        canvas.draw()

    def _selected_list_items(self, widget: QListWidget) -> list[str]:
        return [item.text() for item in widget.selectedItems()]

    def _resolve_series(self, name: str) -> pd.Series | None:
        if self._df is None:
            return None
        key = resolve_column_key(self._df, name)
        if key is None:
            return None
        return self._df[key]

    def _set_combo_options(self, combo: QComboBox, codes: list[str], *, include_auto: bool = True) -> None:
        combo.blockSignals(True)
        combo.clear()
        if include_auto:
            combo.addItem(_CHART_LABELS["auto"], "auto")
        for code in codes:
            combo.addItem(_CHART_LABELS.get(code, code), code)
        combo.blockSignals(False)

    def _on_uni_col_changed(self) -> None:
        if self._df is None:
            return
        series = self._resolve_series(self._uni_col.currentText())
        if series is None:
            return
        kind = column_kind(series)
        kind_kr = {"numeric": "수치형", "categorical": "범주형", "datetime": "날짜/시간", "other": "기타"}.get(
            kind, kind
        )
        self._uni_kind_label.setText(f"변수 유형: {kind_kr} — 추천 차트: {_CHART_LABELS.get(suggest_univariate_chart(series), '')}")
        self._set_combo_options(self._uni_chart, univariate_chart_options(series))
        self._sync_dependency_controls()

    def _on_bi_cols_changed(self) -> None:
        if self._df is None:
            return
        xs = self._resolve_series(self._bi_x.currentText())
        ys = self._resolve_series(self._bi_y.currentText())
        if xs is None or ys is None:
            return
        info = bivariate_pair_info(xs, ys)
        self._bi_pair_label.setText(f"조합: {info.label}")
        self._set_combo_options(self._bi_chart, bivariate_chart_options(xs, ys))

    def _fill_stats_table(self, table: QTableWidget, rows: list[tuple[str, str]]) -> None:
        table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            table.setItem(i, 0, _readonly_item(k))
            table.setItem(i, 1, _readonly_item(v))

    def _fill_uni_stats(self, series: pd.Series) -> None:
        kind = column_kind(series)
        if kind == "numeric":
            stats = univariate_numeric_stats(series)
            if stats is None:
                self._fill_stats_table(self._uni_stats_table, [])
                return
            rows = [
                ("개수", f"{stats.count:,}"),
                ("평균", format_stat_number(stats.mean)),
                ("표준편차", format_stat_number(stats.std)),
                ("분산", format_stat_number(stats.variance)),
                ("최소", format_stat_number(stats.min_val)),
                ("Q1 (25%)", format_stat_number(stats.q1)),
                ("중앙값", format_stat_number(stats.median)),
                ("Q3 (75%)", format_stat_number(stats.q3)),
                ("최대", format_stat_number(stats.max_val)),
                ("범위", format_stat_number(stats.range_val)),
                ("IQR", format_stat_number(stats.iqr)),
            ]
            self._fill_stats_table(self._uni_stats_table, rows)
        else:
            stats = univariate_categorical_stats(series)
            freqs = univariate_categorical_freq(series, self._uni_topn.value())
            rows: list[tuple[str, str]] = []
            if stats:
                rows.extend([
                    ("개수", f"{stats.count:,}"),
                    ("고유값", f"{stats.unique:,}"),
                    ("최빈값", stats.mode),
                    ("최빈 빈도", f"{stats.mode_count:,} ({stats.mode_pct:.1f}%)"),
                ])
            rows.append(("—", "—"))
            for name, cnt, pct in freqs:
                rows.append((name, f"{cnt:,} ({pct:.1f}%)"))
            self._fill_stats_table(self._uni_stats_table, rows)

    def _sample_label_text(self, plot_df, sampled: bool) -> str:
        """차트 표본 안내 문구. 샘플링됐으면 전체 대비 표본 크기를 덧붙인다."""
        total = len(self._df) if self._df is not None else len(plot_df)
        text = f"표시: {len(plot_df):,}행"
        if sampled:
            text += f" (전체 {total:,}행 중 무작위 {PLOT_MAX_ROWS:,}행 샘플)"
        return text

    def _draw_univariate(self) -> None:
        if self._df is None:
            return
        col_name = self._uni_col.currentText()
        series = self._resolve_series(col_name)
        if series is None:
            return
        self._fill_uni_stats(series)
        chart = self._uni_chart.currentData()
        if chart == "auto":
            chart = suggest_univariate_chart(series)
        plot_df, sampled = sample_for_plot(self._df)
        self._uni_sample_label.setText(self._sample_label_text(plot_df, sampled))
        key = resolve_column_key(plot_df, col_name)
        if key is None:
            self._uni_sample_label.setText(f"열 '{col_name}'을(를) 찾을 수 없습니다. 새로고침 후 다시 시도하세요.")
            return
        s = plot_df[key]
        canvas = self._uni_canvas
        ax = canvas.begin_chart()
        st = self._chart_style
        horizontal = getattr(self, "_uni_horizontal", False)
        kind = column_kind(series)
        bar_color = st.color_primary
        edge_color = st.color_edge
        if chart in {"histogram", "kde", "boxplot"} or kind == "numeric":
            nums = pd.to_numeric(s, errors="coerce").dropna()
            if chart == "boxplot":
                bp = ax.boxplot(
                    nums,
                    vert=not horizontal,
                    patch_artist=True,
                    medianprops={"color": st.color_accent, "linewidth": 2},
                    whiskerprops={"color": st.color_edge},
                    capprops={"color": st.color_edge},
                )
                for patch in bp["boxes"]:
                    patch.set_facecolor(st.color_fill)
                    patch.set_edgecolor(bar_color)
                    patch.set_alpha(st.bar_alpha)
                if horizontal:
                    ax.set_xlabel(col_name)
                else:
                    ax.set_ylabel(col_name)
                val_axis = "x" if horizontal else "y"
                self._apply_axis_limits(ax, "uni", x_vals=nums if horizontal else None, y_vals=nums if not horizontal else None)
                self._format_numeric_axis(ax, axis=val_axis)
            elif chart == "kde":
                dens_curve = None
                if horizontal:
                    ax.hist(
                        nums, bins=self._uni_bins.value(), density=True, alpha=0.4,
                        color=bar_color, edgecolor=edge_color, orientation="horizontal",
                    )
                else:
                    ax.hist(
                        nums, bins=self._uni_bins.value(), density=True, alpha=0.4,
                        color=bar_color, edgecolor=edge_color,
                    )
                if not scipy_available():
                    ax.text(
                        0.5, 0.92,
                        "KDE 곡선은 scipy 설치 후 표시됩니다.",
                        transform=ax.transAxes,
                        ha="center",
                        color=st.color_warning,
                        fontsize=st.tick_font_size,
                    )
                else:
                    try:
                        from scipy.stats import gaussian_kde
                        import numpy as np

                        kde = gaussian_kde(nums)
                        xr = np.linspace(nums.min(), nums.max(), 200)
                        dens_curve = kde(xr)
                        if horizontal:
                            ax.plot(dens_curve, xr, color=st.color_accent, linewidth=2.5)
                            ax.set_ylabel(col_name)
                            ax.set_xlabel("밀도")
                        else:
                            ax.plot(xr, dens_curve, color=st.color_accent, linewidth=2.5)
                            ax.set_xlabel(col_name)
                            ax.set_ylabel("밀도")
                    except Exception as exc:
                        ax.text(
                            0.5, 0.92,
                            f"KDE 곡선 생략: {exc}",
                            transform=ax.transAxes,
                            ha="center",
                            color=st.color_warning,
                            fontsize=st.tick_font_size,
                        )
                if horizontal:
                    ax.set_ylabel(col_name)
                    ax.set_xlabel("밀도")
                else:
                    ax.set_xlabel(col_name)
                    ax.set_ylabel("밀도")
                if horizontal:
                    self._apply_axis_limits(
                        ax, "uni",
                        x_vals=dens_curve if dens_curve is not None else None,
                        y_vals=nums,
                    )
                else:
                    self._apply_axis_limits(
                        ax, "uni",
                        x_vals=nums,
                        y_vals=dens_curve if dens_curve is not None else None,
                    )
                self._format_numeric_axis(ax, axis="both")
            else:
                if horizontal:
                    ax.hist(
                        nums, bins=self._uni_bins.value(), color=bar_color,
                        edgecolor=edge_color, alpha=st.bar_alpha, orientation="horizontal",
                    )
                    ax.set_ylabel(col_name)
                    ax.set_xlabel("빈도")
                    self._apply_axis_limits(ax, "uni", y_vals=nums)
                    self._format_numeric_axis(ax, axis="both")
                else:
                    ax.hist(
                        nums, bins=self._uni_bins.value(), color=bar_color,
                        edgecolor=edge_color, alpha=st.bar_alpha,
                    )
                    ax.set_xlabel(col_name)
                    ax.set_ylabel("빈도")
                    self._apply_axis_limits(ax, "uni", x_vals=nums)
                    self._format_numeric_axis(ax, axis="both")
        elif chart == "pie":
            counts = s.astype(str).value_counts().head(self._uni_topn.value())
            other = len(s) - counts.sum()
            labels = list(counts.index.astype(str))
            sizes = list(counts.values)
            if other > 0:
                labels.append("기타")
                sizes.append(other)
            ax.pie(
                sizes, labels=labels, autopct="%1.1f%%",
                textprops={"color": st.color_text, "fontsize": st.tick_font_size},
                wedgeprops={"edgecolor": st.color_border, "linewidth": 1},
            )
            ax.grid(False)
        else:
            counts = s.astype(str).value_counts().head(self._uni_topn.value())
            labels = counts.index.astype(str).tolist()
            values = counts.values
            if horizontal:
                ax.barh(labels, values, color=st.color_accent, edgecolor=edge_color, alpha=st.bar_alpha)
                ax.set_ylabel(col_name)
                ax.set_xlabel("빈도")
                self._apply_axis_limits(ax, "uni", x_vals=values)
                self._format_numeric_axis(ax, axis="x")
            else:
                ax.bar(labels, values, color=st.color_accent, edgecolor=edge_color, alpha=st.bar_alpha)
                ax.set_xlabel(col_name)
                ax.set_ylabel("빈도")
                ax.tick_params(axis="x", rotation=st.x_label_rotation)
                self._apply_axis_limits(ax, "uni", y_vals=values)
                self._format_numeric_axis(ax, axis="y")
        self._set_chart_title(
            ax,
            f"{col_name} — {_CHART_LABELS.get(chart, chart)}",
            local_override=self._uni_title.text(),
        )
        canvas.finish_chart()

    def _cat_num_axes(self, xs: pd.Series, ys: pd.Series, x_name: str, y_name: str) -> tuple[pd.Series, pd.Series, str, str]:
        info = bivariate_pair_info(xs, ys)
        if info.pair_kind == "cat_num":
            return xs.astype(str), pd.to_numeric(ys, errors="coerce"), x_name, y_name
        if info.pair_kind == "num_cat":
            return ys.astype(str), pd.to_numeric(xs, errors="coerce"), y_name, x_name
        return xs.astype(str), pd.to_numeric(ys, errors="coerce"), x_name, y_name

    def _fill_bi_table(self, xs: pd.Series, ys: pd.Series, x_name: str, y_name: str) -> None:
        info = bivariate_pair_info(xs, ys)
        if info.pair_kind == "num_num":
            corr = bivariate_numeric_correlation(xs, ys)
            if corr is None:
                self._bi_table.setRowCount(0)
                self._bi_table.setColumnCount(0)
                return
            self._bi_table.setColumnCount(2)
            self._bi_table.setHorizontalHeaderLabels(["지표", "값"])
            rows = [
                ("피어슨 r", f"{corr.pearson_r:.4f}"),
                ("스피어만 ρ", f"{corr.spearman_r:.4f}" if corr.spearman_r is not None else "—"),
                ("p-value", format_stat_number(corr.pearson_p, max_decimals=8) if corr.pearson_p is not None else "—"),
                ("유효 쌍", f"{corr.n:,}"),
            ]
            self._fill_stats_table(self._bi_table, rows)
            p_txt = f"p={format_stat_number(corr.pearson_p, max_decimals=8)}" if corr.pearson_p is not None else ""
            self._bi_stats_label.setText(
                f"피어슨 r = {corr.pearson_r:.4f}, 스피어만 ρ = {corr.spearman_r:.4f} (n={corr.n:,}) {p_txt}"
            )
        elif info.pair_kind in {"cat_num", "num_cat"}:
            cats, nums, cat_name, num_name = self._cat_num_axes(xs, ys, x_name, y_name)
            grp = pd.DataFrame({"g": cats, "v": nums}).dropna()
            summary = grp.groupby("g")["v"].agg(["count", "mean", "std", "median"]).head(15)
            self._bi_table.setColumnCount(len(summary.columns) + 1)
            self._bi_table.setHorizontalHeaderLabels(["그룹"] + [str(c) for c in summary.columns])
            self._bi_table.setRowCount(len(summary))
            for r, (g, row) in enumerate(summary.iterrows()):
                self._bi_table.setItem(r, 0, _readonly_item(str(g)))
                for c, col in enumerate(summary.columns):
                    val = row[col]
                    text = format_stat_number(val) if pd.notna(val) else "—"
                    self._bi_table.setItem(r, c + 1, _readonly_item(text))
            self._bi_stats_label.setText(f"{cat_name}(범주) × {num_name}(수치) — 그룹별 요약")
        else:
            ct = bivariate_crosstab_table(xs, ys)
            self._bi_table.setColumnCount(len(ct.columns) + 1)
            self._bi_table.setHorizontalHeaderLabels([""] + [str(c) for c in ct.columns])
            self._bi_table.setRowCount(len(ct))
            for r, (idx, row) in enumerate(ct.iterrows()):
                self._bi_table.setItem(r, 0, _readonly_item(str(idx)))
                for c, col in enumerate(ct.columns):
                    self._bi_table.setItem(r, c + 1, _readonly_item(str(int(row[col]))))
            self._bi_stats_label.setText(f"{x_name} × {y_name} — 교차표 (범주 × 범주)")

    def _draw_bivariate(self) -> None:
        if self._df is None:
            return
        x_name = self._bi_x.currentText()
        y_name = self._bi_y.currentText()
        x_series = self._resolve_series(x_name)
        y_series = self._resolve_series(y_name)
        if x_series is None or y_series is None:
            return
        self._fill_bi_table(x_series, y_series, x_name, y_name)
        chart = self._bi_chart.currentData()
        if chart == "auto":
            chart = suggest_bivariate_chart(x_series, y_series)
        plot_df, sampled = sample_for_plot(self._df)
        self._bi_sample_label.setText(self._sample_label_text(plot_df, sampled))
        xk = resolve_column_key(plot_df, x_name)
        yk = resolve_column_key(plot_df, y_name)
        if xk is None or yk is None:
            self._bi_sample_label.setText("선택한 열을 찾을 수 없습니다. 새로고침 후 다시 시도하세요.")
            return
        xs = plot_df[xk]
        ys = plot_df[yk]
        info = bivariate_pair_info(xs, ys)
        canvas = self._bi_canvas
        ax = canvas.begin_chart()
        st = self._chart_style

        if info.pair_kind == "num_num":
            xv = pd.to_numeric(xs, errors="coerce")
            yv = pd.to_numeric(ys, errors="coerce")
            mask = xv.notna() & yv.notna()
            if chart == "hexbin" and mask.any():
                hb = ax.hexbin(
                    xv[mask], yv[mask], gridsize=35, cmap=st.cmap_hexbin,
                    mincnt=1, edgecolors=st.figure_bg, linewidths=0.2,
                )
                if st.show_colorbar:
                    cbar = canvas.fig.colorbar(hb, ax=ax, fraction=0.046)
                    cbar.ax.yaxis.set_tick_params(color=st.color_edge, labelcolor=st.color_text)
            else:
                ax.scatter(
                    xv[mask], yv[mask], alpha=st.scatter_alpha, color=st.color_primary,
                    s=st.scatter_size, edgecolors=st.figure_bg, linewidths=0.3,
                )
                if chart == "corr_line" and mask.sum() >= 2:
                    import numpy as np

                    coeffs = np.polyfit(xv[mask], yv[mask], 1)
                    xr = np.linspace(xv[mask].min(), xv[mask].max(), 50)
                    ax.plot(xr, coeffs[0] * xr + coeffs[1], color=st.color_accent, linewidth=2.5)
            ax.set_xlabel(x_name)
            ax.set_ylabel(y_name)
            self._apply_axis_limits(
                ax, "bi",
                x_vals=xv[mask] if mask.any() else None,
                y_vals=yv[mask] if mask.any() else None,
            )
            self._format_numeric_axis(ax, axis="both")
        elif info.pair_kind in {"cat_num", "num_cat"}:
            cats, nums, cat_label, num_label = self._cat_num_axes(xs, ys, x_name, y_name)
            groups = cats.dropna().unique()[:15]
            data = []
            labels = []
            for g in groups:
                vals = nums[cats == g].dropna()
                if len(vals):
                    data.append(vals)
                    labels.append(str(g))
            if chart == "violin" and data:
                parts = ax.violinplot(data, showmeans=True, showmedians=True)
                for body in parts["bodies"]:
                    body.set_facecolor(st.color_fill)
                    body.set_edgecolor(st.color_primary)
                    body.set_alpha(st.bar_alpha)
                ax.set_xticks(range(1, len(labels) + 1))
                ax.set_xticklabels(labels, rotation=st.x_label_rotation, ha="right", fontsize=st.tick_font_size)
            elif chart == "bar_mean" and data:
                means = [d.mean() for d in data]
                ax.bar(labels, means, color=st.color_accent, edgecolor=st.color_border, alpha=st.bar_alpha)
                ax.tick_params(axis="x", rotation=st.x_label_rotation)
                self._apply_axis_limits(ax, "bi", y_vals=means)
                self._format_numeric_axis(ax, axis="y")
            elif data:
                bp = ax.boxplot(data, labels=labels, patch_artist=True)
                for patch in bp["boxes"]:
                    patch.set_facecolor(st.color_fill)
                    patch.set_edgecolor(st.color_primary)
                    patch.set_alpha(st.bar_alpha)
                ax.tick_params(axis="x", rotation=st.x_label_rotation)
                flat = pd.concat(data)
                self._apply_axis_limits(ax, "bi", y_vals=flat)
                self._format_numeric_axis(ax, axis="y")
            ax.set_xlabel(cat_label)
            ax.set_ylabel(num_label)
        else:
            ct = bivariate_crosstab_table(xs, ys)
            if chart == "stacked_bar":
                bottom = None
                x_pos = range(len(ct.columns))
                for i, (idx, row) in enumerate(ct.iterrows()):
                    vals = row.values
                    ax.bar(x_pos, vals, bottom=bottom, label=str(idx))
                    bottom = vals if bottom is None else bottom + vals
                ax.set_xticks(list(x_pos))
                ax.set_xticklabels([str(c) for c in ct.columns], rotation=45, ha="right")
                ax.legend(fontsize=st.tick_font_size, loc=st.legend_position)
                ax.set_xlabel(y_name)
            elif chart == "grouped_bar":
                import numpy as np

                x_pos = np.arange(len(ct.index))
                width = 0.8 / max(len(ct.columns), 1)
                for j, col in enumerate(ct.columns):
                    ax.bar(x_pos + j * width, ct[col].values, width, label=str(col))
                ax.set_xticks(x_pos + width * (len(ct.columns) - 1) / 2)
                ax.set_xticklabels([str(i) for i in ct.index], rotation=st.x_label_rotation, ha="right")
                ax.legend(fontsize=st.tick_font_size, loc=st.legend_position)
                ax.set_xlabel(x_name)
            else:
                im = ax.imshow(ct.values, aspect="auto", cmap=st.cmap_count)
                ax.set_xticks(range(len(ct.columns)))
                ax.set_xticklabels([str(c) for c in ct.columns], rotation=st.x_label_rotation, ha="right")
                ax.set_yticks(range(len(ct.index)))
                ax.set_yticklabels([str(i) for i in ct.index])
                ax.set_xlabel(y_name)
                ax.set_ylabel(x_name)
                if st.show_colorbar:
                    canvas.fig.colorbar(im, ax=ax, fraction=0.046)
        self._set_chart_title(
            ax,
            f"{x_name} × {y_name} — {_CHART_LABELS.get(chart, chart)}",
            local_override=self._bi_title.text(),
        )
        canvas.finish_chart()

    def _draw_multivariate(self) -> None:
        if self._df is None:
            return
        cols = self._selected_list_items(self._multi_cols)
        if not cols:
            cols = numeric_columns(self._df)
        corr = correlation_matrix(self._df, cols)
        canvas = self._multi_canvas
        ax = canvas.begin_chart()
        st = self._chart_style
        if corr.empty or len(corr) < 2:
            ax.text(0.5, 0.5, "숫자 열 2개 이상 필요", ha="center", va="center", color=st.color_muted)
        else:
            labels = [str(c) for c in corr.columns]
            im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap=st.cmap_heatmap, aspect="auto")
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=st.x_label_rotation, ha="right")
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels)
            for i in range(len(labels)):
                for j in range(len(labels)):
                    ax.text(
                        j, i, f"{corr.values[i, j]:.2f}",
                        ha="center", va="center", color=st.color_text, fontsize=st.tick_font_size,
                    )
            if st.show_colorbar:
                canvas.fig.colorbar(im, ax=ax, fraction=0.046)
            self._set_chart_title(ax, f"피어슨 상관 행렬 ({len(labels)}개 열)")
        canvas.finish_chart()

    def _draw_pair_plot(self) -> None:
        if self._df is None:
            return
        cols = self._selected_list_items(self._multi_cols)
        if not cols:
            cols = numeric_columns(self._df)
        cols = cols[:4]
        if len(cols) < 2:
            QMessageBox.information(self, "Pair plot", "숫자 열 2개 이상 선택하세요.")
            return
        keys = [resolve_column_key(self._df, c) for c in cols]
        keys = [k for k in keys if k is not None]
        if len(keys) < 2:
            QMessageBox.information(self, "Pair plot", "유효한 숫자 열이 부족합니다.")
            return
        plot_df, sampled = sample_for_plot(self._df[keys], max_rows=PLOT_MAX_ROWS)
        note = f" (샘플 n={len(plot_df):,})" if sampled else f" (n={len(self._df):,})"
        st = self._chart_style
        n = len(keys)
        canvas = self._multi_canvas
        canvas.clear_axes()
        for i, yi in enumerate(keys):
            for j, xj in enumerate(keys):
                ax = canvas.fig.add_subplot(n, n, i * n + j + 1)
                canvas.style_axes(ax)
                if i == j:
                    nums = pd.to_numeric(plot_df[yi], errors="coerce").dropna()
                    if len(nums) == 0:
                        ax.text(0.5, 0.5, "—", ha="center", va="center", color=st.color_muted, fontsize=8)
                    else:
                        ax.hist(
                            nums, bins=min(30, max(10, len(nums) // 20)),
                            color=st.color_primary, alpha=st.bar_alpha,
                        )
                    if j == 0:
                        ax.set_ylabel(str(yi), fontsize=7)
                    if i == n - 1:
                        ax.set_xlabel(str(xj), fontsize=7)
                else:
                    xvals = pd.to_numeric(plot_df[xj], errors="coerce")
                    yvals = pd.to_numeric(plot_df[yi], errors="coerce")
                    valid = xvals.notna() & yvals.notna()
                    if valid.sum() == 0:
                        ax.text(0.5, 0.5, "—", ha="center", va="center", color=st.color_muted, fontsize=8)
                    else:
                        ax.scatter(
                            xvals[valid], yvals[valid],
                            s=max(4, st.scatter_size // 3), alpha=st.scatter_alpha, color=st.color_primary,
                        )
                    if j == 0:
                        ax.set_ylabel(str(yi), fontsize=7)
                    if i == n - 1:
                        ax.set_xlabel(str(xj), fontsize=7)
                ax.tick_params(labelsize=6)
        canvas.fig.suptitle(f"Pair plot — {', '.join(str(k) for k in keys)}{note}", fontsize=10)
        canvas.finish_chart()

    def _draw_pca(self) -> None:
        if self._df is None:
            return
        cols = self._selected_list_items(self._multi_cols)
        if not cols:
            cols = numeric_columns(self._df)
        result = compute_pca(self._df, cols, n_components=2)
        canvas = self._multi_canvas
        ax = canvas.begin_chart()
        st = self._chart_style
        if result is None or result.scores.shape[1] < 2:
            ax.text(0.5, 0.5, "숫자 열 2개 이상·유효 행 3개 이상 필요", ha="center", va="center", color=st.color_muted)
        else:
            plot_df, sampled = sample_for_plot(result.scores, max_rows=PLOT_MAX_ROWS)
            pc1, pc2 = result.component_labels[0], result.component_labels[1]
            note = f" (샘플 n={len(plot_df):,})" if sampled else f" (n={len(result.scores):,})"
            ax.scatter(
                plot_df[pc1], plot_df[pc2],
                alpha=st.scatter_alpha, color=st.color_primary, s=st.scatter_size,
                edgecolors=st.figure_bg, linewidths=0.3,
            )
            ev = result.explained_variance_ratio
            ax.set_xlabel(f"{pc1} ({ev[0] * 100:.1f}%)")
            ax.set_ylabel(f"{pc2} ({ev[1] * 100:.1f}%)")
            self._set_chart_title(ax, f"PCA{note}")
            self._format_numeric_axis(ax, axis="both")
        canvas.finish_chart()

    def _draw_missing_chart(self) -> None:
        if self._df is None:
            return
        data = missing_summary(self._df)[:15]
        canvas = self._missing_canvas
        ax = canvas.begin_chart()
        st = self._chart_style
        if not data:
            ax.text(0.5, 0.5, "결측치 없음", ha="center", va="center", color=st.color_muted)
        else:
            names = [d[0] for d in data]
            counts = [d[1] for d in data]
            ax.barh(names, counts, color=st.color_warning, alpha=st.bar_alpha)
            ax.set_xlabel("결측 개수")
            self._set_chart_title(ax, "결측 현황")
            ax.invert_yaxis()
        canvas.draw()

    def _preview_knn(self) -> None:
        if self._df is None:
            self._missing_preview.setText("미리보기: 데이터 없음")
            return
        cols = self._selected_list_items(self._missing_cols)
        if not cols:
            cols = numeric_columns(self._df)
        before, _, targets = knn_fill_preview(self._df, cols)
        if not targets:
            self._missing_preview.setText("미리보기: 숫자 열이 없습니다.")
            return
        cells = len(self._df) * len(targets)
        warn = ""
        if cells > 100_000:
            warn = "\n⚠ 대용량 데이터 — KNN 적용에 시간이 걸릴 수 있습니다."
        self._missing_preview.setText(
            f"미리보기: 대상 열 {len(targets)}개 ({', '.join(targets[:5])}"
            f"{'…' if len(targets) > 5 else ''})\n"
            f"결측 {before:,}개 → KNN 대체 후 0개 (숫자 열만){warn}"
        )

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "분석 작업 실패", message)
        if self._on_log:
            self._on_log("error", "분석 작업 실패", message)

    def _apply_knn(self) -> None:
        if self._df is None:
            return
        if not require(self, sklearn_available(), "sklearn", feature="KNN 대체"):
            return
        cols = self._selected_list_items(self._missing_cols)
        if not cols:
            cols = numeric_columns(self._df)
        if not cols:
            QMessageBox.warning(self, "KNN 대체", "숫자 열을 선택하세요.")
            return
        df = self._df.copy(deep=True)
        n_neighbors = self._knn_neighbors.value()
        self._missing_preview.setText("KNN 적용 중… (잠시만 기다려 주세요)")

        def work():
            return fill_na_knn(df, cols, n_neighbors=n_neighbors)

        def on_ok(result) -> None:
            msg = f"KNN 결측 대체 (n={n_neighbors}, 열 {len(cols)}개)"
            self._on_apply(result, msg)
            if self._on_log:
                self._on_log("success", msg, f"{len(cols)}개 숫자 열")
            self._preview_knn()

        self._run_analysis_task(work, on_ok, progress="KNN 적용 중…")

    def _apply_mice(self) -> None:
        if self._df is None:
            return
        if not require(self, sklearn_available(), "sklearn", feature="MICE 대체"):
            return
        cols = self._selected_list_items(self._missing_cols)
        if not cols:
            cols = numeric_columns(self._df)
        if not cols:
            QMessageBox.warning(self, "MICE 대체", "숫자 열을 선택하세요.")
            return
        df = self._df.copy(deep=True)
        self._missing_preview.setText("MICE 적용 중…")

        def work():
            return fill_na_mice(df, cols)

        def on_ok(result) -> None:
            msg = f"MICE 결측 대체 (열 {len(cols)}개)"
            self._on_apply(result, msg)
            if self._on_log:
                self._on_log("success", msg, f"{len(cols)}개 숫자 열")
            self._preview_knn()

        self._run_analysis_task(work, on_ok, progress="MICE 적용 중…")

    def _run_analysis_task(self, work, on_ok, *, progress: str = "처리 중…") -> None:
        if self._worker_busy:
            QMessageBox.information(self, "분석 작업", "이전 작업이 끝날 때까지 기다려 주세요.")
            return
        self._worker_busy = True
        token = self._analysis_token
        self._set_progress(progress)

        def _log_stale_result() -> None:
            if self._on_log:
                self._on_log("warning", "분석 작업 결과 폐기", "작업 중 데이터가 변경되어 오래된 결과를 적용하지 않았습니다.")

        def _done(result) -> None:
            self._worker_busy = False
            self._set_progress(None)
            if token != self._analysis_token:
                _log_stale_result()
                return
            on_ok(result)

        def _fail(message: str) -> None:
            self._worker_busy = False
            self._set_progress(None)
            if token != self._analysis_token:
                _log_stale_result()
                return
            self._on_worker_error(message)

        run_analysis_task(self, work, _done, _fail)

    def _outlier_params(self) -> tuple[list[str], str, float, float]:
        cols = self._selected_list_items(self._outlier_cols)
        if not cols and self._df is not None:
            cols = numeric_columns(self._df)
        method = self._outlier_method.currentData()
        return cols, method, self._outlier_z.value(), self._outlier_contamination.value()

    def _compute_outlier_preview(
        self,
        df: pd.DataFrame,
        cols: list[str],
        method: str,
        z: float,
        contam: float,
    ) -> dict:
        from df_tool.operations import outlier_row_mask

        if not cols:
            return {"error": "no_cols"}
        summary = outlier_summary(df, cols, method, z_threshold=z, contamination=contam)
        row_count = count_outlier_rows(df, cols, method, z_threshold=z, contamination=contam)
        mask = outlier_row_mask(df, cols, method, z_threshold=z, contamination=contam)
        return {
            "summary": summary,
            "row_count": row_count,
            "mask": mask,
            "cols": cols,
            "method": method,
            "row_total": len(df),
        }

    def _preview_outliers_async(self) -> None:
        if self._df is None:
            self._outlier_preview.setText("미리보기: 데이터 없음")
            return
        cols, method, z, contam = self._outlier_params()
        if not cols:
            self._outlier_preview.setText("미리보기: 숫자 열이 없습니다.")
            return
        if method == "isolation_forest" and not sklearn_available():
            self._outlier_preview.setText(feature_requirement_message("sklearn", feature="Isolation Forest", inline=True))
            return
        df = self._df.copy(deep=True)
        self._outlier_preview.setText("이상치 미리보기 계산 중…")

        def on_ok(payload) -> None:
            if not payload or payload.get("error") == "no_cols":
                self._outlier_preview.setText("미리보기: 숫자 열이 없습니다.")
                return
            summary = payload["summary"]
            row_count = payload["row_count"]
            method = payload["method"]
            cols = payload["cols"]
            row_total = payload.get("row_total", len(self._df) if self._df is not None else 0)
            lines = [f"· {name}: {cnt:,}개 ({pct:.1f}%)" for name, cnt, pct in summary[:8]]
            hint = ""
            if method == "isolation_forest" and row_total < 10:
                hint = "\n※ Isolation Forest는 유효 행 10개 이상에서 동작합니다."
            self._outlier_preview.setText(
                f"미리보기 ({method}): 제거 예상 행 {row_count:,}개 / {row_total:,}행\n"
                + "\n".join(lines)
                + hint
            )
            self._fill_outlier_sample_from_mask(payload["mask"], cols)
            self._draw_outlier_boxplot(cols[0])

        self._run_analysis_task(
            lambda: self._compute_outlier_preview(df, cols, method, z, contam),
            on_ok,
            progress="이상치 미리보기…",
        )

    def _fill_outlier_sample_from_mask(self, mask: pd.Series, cols: list[str]) -> None:
        if self._df is None:
            return
        sample = self._df.loc[mask].head(100)
        display_cols = cols[:6]
        keys = [resolve_column_key(self._df, c) for c in display_cols]
        keys = [k for k in keys if k is not None]
        self._outlier_sample.setColumnCount(len(keys))
        self._outlier_sample.setHorizontalHeaderLabels([str(k) for k in keys])
        self._outlier_sample.setRowCount(len(sample))
        for r, (_, row) in enumerate(sample.iterrows()):
            for c, key in enumerate(keys):
                val = row[key]
                text = "" if pd.isna(val) else str(val)
                self._outlier_sample.setItem(r, c, _readonly_item(text))

    def _draw_outlier_boxplot(self, col_name: str) -> None:
        if self._df is None:
            return
        key = resolve_column_key(self._df, col_name)
        if key is None:
            return
        nums = pd.to_numeric(self._df[key], errors="coerce").dropna()
        canvas = self._outlier_canvas
        ax = canvas.begin_chart()
        st = self._chart_style
        if len(nums) == 0:
            ax.text(0.5, 0.5, "숫자 데이터 없음", ha="center", va="center", color=st.color_muted)
        else:
            plot_nums, sampled = sample_for_plot(nums.to_frame("_"), max_rows=PLOT_MAX_ROWS)
            note = f" (n={len(plot_nums):,})" if sampled else f" (n={len(nums):,})"
            bp = ax.boxplot(plot_nums["_"].values, vert=True, patch_artist=True)
            for patch in bp["boxes"]:
                patch.set_facecolor(st.color_fill)
                patch.set_edgecolor(st.color_primary)
                patch.set_alpha(st.bar_alpha)
            self._set_chart_title(ax, f"{col_name} 박스플롯{note}")
        canvas.draw()

    def _apply_outliers(self) -> None:
        if self._df is None:
            return
        cols = self._selected_list_items(self._outlier_cols)
        if not cols:
            cols = numeric_columns(self._df)
        if not cols:
            QMessageBox.warning(self, "이상치 제거", "숫자 열을 선택하세요.")
            return
        method = self._outlier_method.currentData()
        z = self._outlier_z.value()
        contam = self._outlier_contamination.value()
        if method == "isolation_forest" and not require(self, sklearn_available(), "sklearn", feature="Isolation Forest", title="이상치 제거"):
            return
        if method == "isolation_forest" and len(self._df) < 10:
            QMessageBox.information(
                self,
                "Isolation Forest",
                "Isolation Forest는 유효 행 10개 이상에서 동작합니다.",
            )
            return
        df = self._df.copy(deep=True)
        self._outlier_preview.setText("이상치 제거 적용 중…")

        def work():
            return drop_outlier_rows(df, cols, method, z_threshold=z, contamination=contam)

        def on_ok(payload) -> None:
            result, removed, _ = payload
            if removed == 0:
                QMessageBox.information(self, "이상치 제거", "제거할 이상치 행이 없습니다.")
                self._preview_outliers_async()
                return
            if method == "iqr":
                label = "IQR"
            elif method == "isolation_forest":
                label = f"IF({contam})"
            else:
                label = f"Z>{z}"
            msg = f"이상치 행 제거 ({label}, {removed:,}행)"
            if QMessageBox.question(
                self,
                "이상치 행 제거 확인",
                f"{removed:,}행을 제거합니다.\n적용 후 Ctrl+Z로 되돌릴 수 있습니다.\n계속할까요?",
            ) != QMessageBox.StandardButton.Yes:
                self._outlier_preview.setText("이상치 제거가 취소되었습니다.")
                return
            self._on_apply(result, msg)
            if self._on_log:
                self._on_log("success", msg, f"열: {', '.join(cols[:5])}")

        self._run_analysis_task(work, on_ok, progress="이상치 제거 적용 중…")

    def apply_theme(self) -> None:
        self._title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")
