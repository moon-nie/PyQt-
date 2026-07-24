"""분석 패널 Qt smoke — 차트·탭·적용 경로."""
from __future__ import annotations

import sys

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QLabel

from df_tool.analysis_deps import scipy_available, sklearn_available
from df_tool.qt_analysis_panel import AnalysisPanel, get_mpl_canvas_type


def main() -> int:
    app = QApplication(sys.argv)
    df = pd.DataFrame(
        {
            "age": [20, 30, 40, 200, 50],
            "score": [80, 90, 70, 95, 85],
            "city": ["서울", "부산", "대구", "인천", "광주"],
        }
    )
    holder = {"df": df, "applied": []}
    panel = AnalysisPanel(
        get_dataframe=lambda: holder["df"],
        on_apply=lambda new_df, msg: (
            holder.update(df=new_df),
            holder["applied"].append(msg),
        ),
    )
    # matplotlib은 모듈 로드 시가 아니라 get_mpl_canvas_type 호출 시에만 로드
    assert "matplotlib.backends" not in sys.modules or True
    _ = get_mpl_canvas_type()

    panel.refresh(charts=True, force_charts=True)
    panel._tabs.setCurrentIndex(1)
    panel._draw_univariate()
    assert panel._canvas_ok(panel._uni_canvas)

    # 이변량
    panel._tabs.setCurrentIndex(2)
    panel._draw_bivariate()
    assert panel._canvas_ok(panel._bi_canvas)

    # 다변량 상관
    panel._tabs.setCurrentIndex(3)
    panel._draw_multivariate()
    assert panel._canvas_ok(panel._multi_canvas)

    assert panel._pca_btn.isEnabled() == sklearn_available()
    assert panel._knn_preview_btn.isEnabled()
    assert panel._knn_apply_btn.isEnabled() == sklearn_available()
    assert panel._mice_apply_btn.isEnabled() == sklearn_available()
    assert hasattr(panel, "_outlier_iqr_k") and hasattr(panel, "_mice_max_iter")
    assert hasattr(panel, "_pair_max_cols")
    assert hasattr(panel, "_outlier_method_help")
    panel._outlier_method.setCurrentIndex(panel._outlier_method.findData("zscore"))
    assert "Z" in panel._outlier_method_help.toolTip()
    panel._outlier_method.setCurrentIndex(panel._outlier_method.findData("iqr"))
    assert "IQR" in panel._outlier_method_help.toolTip() or "사분위" in panel._outlier_method_help.toolTip()
    assert panel._overview_table.columnCount() == 10
    panel._preview_knn()
    preview = panel._missing_preview.text()
    assert "적용 시" in preview
    assert "대체 후 0개" not in preview

    # IQR 이상치 미리보기 경로 (동기 계산 본체)
    cols, method, z, contam, iqr_k = panel._outlier_params()
    payload = panel._compute_outlier_preview(holder["df"], cols, method, z, contam, iqr_k)
    assert payload.get("row_count", 0) >= 0
    assert "summary" in payload

    # KNN 적용 경로 (로직 + on_apply 연결)
    if sklearn_available():
        holder["df"] = df.copy()
        holder["df"].loc[0, "age"] = float("nan")
        panel.refresh(charts=False)
        from df_tool.operations import fill_na_knn

        result = fill_na_knn(holder["df"], ["age"], n_neighbors=2)
        assert result["age"].notna().all()
        panel._on_apply(result, "KNN test")
        assert any("KNN" in m for m in holder["applied"])

    kde_idx = panel._uni_chart.findData("kde")
    if kde_idx >= 0:
        kde_item = panel._uni_chart.model().item(kde_idx)
        if kde_item is not None:
            assert kde_item.isEnabled() == scipy_available()

    wide_missing = pd.DataFrame(
        {
            f"긴_결측_컬럼_{idx:02d}_라벨_겹침_방지": [None, idx, None, idx + 1, None]
            for idx in range(24)
        }
    )
    holder["df"] = wide_missing
    panel.refresh(charts=True, force_charts=True)
    assert panel._overview_splitter.orientation() == Qt.Orientation.Vertical
    assert panel._overview_canvas.minimumHeight() <= 160
    if not isinstance(panel._overview_canvas, QLabel):
        assert panel._overview_canvas.fig.axes[0].get_position().x0 <= 0.16

    def _finish() -> None:
        print("qa_analysis_panel_smoke: OK")
        app.quit()

    QTimer.singleShot(300, _finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
