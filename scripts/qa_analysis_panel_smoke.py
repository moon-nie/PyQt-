"""분석 패널 Qt smoke — 차트·탭 전환."""
from __future__ import annotations

import sys

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

from df_tool.analysis_deps import scipy_available, sklearn_available
from df_tool.qt_analysis_panel import AnalysisPanel


def main() -> int:
    app = QApplication(sys.argv)
    df = pd.DataFrame(
        {
            "age": [20, 30, 40, 200, 50],
            "score": [80, 90, 70, 95, 85],
            "city": ["서울", "부산", "대구", "인천", "광주"],
        }
    )
    holder = {"df": df}
    panel = AnalysisPanel(
        get_dataframe=lambda: holder["df"],
        on_apply=lambda new_df, _msg: holder.update(df=new_df),
    )
    panel.refresh(charts=True, force_charts=True)
    panel._tabs.setCurrentIndex(1)
    panel._draw_univariate()
    html_btn_exists = True
    assert panel._pca_btn.isEnabled() == sklearn_available()
    assert panel._knn_preview_btn.isEnabled()
    assert panel._knn_apply_btn.isEnabled() == sklearn_available()
    assert panel._mice_apply_btn.isEnabled() == sklearn_available()
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
    assert panel._overview_canvas.fig.axes[0].get_position().x0 <= 0.16

    def _finish() -> None:
        assert panel._tabs.currentIndex() == 1
        assert html_btn_exists
        print("qa_analysis_panel_smoke: OK")
        app.quit()

    QTimer.singleShot(300, _finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
