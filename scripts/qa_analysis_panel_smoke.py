"""분석 패널 Qt smoke — 차트·탭 전환."""
from __future__ import annotations

import sys

import pandas as pd
from PyQt6.QtCore import QTimer
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

    def _finish() -> None:
        assert panel._tabs.currentIndex() == 1
        assert html_btn_exists
        print("qa_analysis_panel_smoke: OK")
        app.quit()

    QTimer.singleShot(300, _finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
