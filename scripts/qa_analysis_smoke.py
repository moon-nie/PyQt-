"""analysis.py · operations EDA 함수 smoke test."""
from __future__ import annotations

import sys

import pandas as pd

from df_tool.analysis import (
    bivariate_chart_options,
    bivariate_numeric_correlation,
    bivariate_pair_info,
    column_kind,
    correlation_matrix,
    count_outlier_rows,
    eda_overview,
    format_stat_number,
    nice_axis_limits,
    missing_summary,
    outlier_summary,
    suggest_bivariate_chart,
    suggest_univariate_chart,
    univariate_chart_options,
    univariate_numeric_stats,
)
from df_tool.analysis_deps import analysis_deps_message, sklearn_available
from df_tool.analysis import compute_pca
from df_tool.eda_report import build_eda_html
from df_tool.operations import drop_outlier_rows, fill_na_knn, fill_na_mice
from df_tool.chart_style import ChartStyle, reset_chart_style, save_chart_style
from df_tool.performance import should_defer_analysis_charts


def main() -> int:
    df = pd.DataFrame(
        {
            "age": [20, 30, None, 40, 200],
            "city": ["서울", "부산", "서울", None, "대구"],
            "score": [80, 90, 70, 85, 95],
        }
    )

    overview = eda_overview(df)
    assert overview.row_count == 5
    assert overview.col_count == 3
    assert len(overview.columns) == 3

    assert column_kind(df["age"]) == "numeric"
    assert column_kind(df["city"]) == "categorical"

    missing = missing_summary(df)
    assert any(name == "age" for name, _, _ in missing)

    assert "histogram" in univariate_chart_options(df["age"])
    assert "kde" in univariate_chart_options(df["age"])
    assert "pie" in univariate_chart_options(df["city"])
    assert suggest_univariate_chart(df["age"]) == "histogram"
    assert suggest_univariate_chart(df["city"]) == "bar"

    nstats = univariate_numeric_stats(df["age"].dropna())
    assert nstats is not None
    assert nstats.std >= 0
    assert nstats.iqr >= 0

    assert bivariate_pair_info(df["age"], df["score"]).pair_kind == "num_num"
    assert bivariate_pair_info(df["city"], df["score"]).pair_kind == "cat_num"
    assert "scatter" in bivariate_chart_options(df["age"], df["score"])
    assert "box" in bivariate_chart_options(df["city"], df["score"])
    assert suggest_bivariate_chart(df["age"], df["score"]) == "scatter"

    corr = bivariate_numeric_correlation(df["age"], df["score"])
    assert corr is not None and corr.n >= 2

    cm = correlation_matrix(df, ["age", "score"])
    assert cm.shape == (2, 2)

    big = format_stat_number(1_500_000.5)
    assert "e" not in big.lower()
    assert "1,500,000" in big
    lo, hi = nice_axis_limits(10, 20)
    assert lo < 10 and hi > 20

    filled = fill_na_knn(df, ["age", "score"], n_neighbors=2)
    assert filled["age"].notna().all()

    try:
        fill_na_knn(pd.DataFrame({"a": [float("nan")]}), ["a"])
        assert False, "expected error"
    except ValueError as exc:
        assert "2개 이상" in str(exc)

    outlier_df, removed, mask = drop_outlier_rows(df, ["age"], "iqr")
    assert removed >= 0
    assert len(mask) == len(df)

    rows = count_outlier_rows(df, ["age"], "iqr")
    assert rows >= 0

    if sklearn_available():
        if_out, if_removed, _ = drop_outlier_rows(
            df, ["age", "score"], "isolation_forest", contamination=0.2
        )
        assert len(if_out) <= len(df)
        assert if_removed >= 0
        if_summary = outlier_summary(df, ["age", "score"], "isolation_forest", contamination=0.2)
        assert len(if_summary) == 1

    assert should_defer_analysis_charts(9000, 10) is True
    assert should_defer_analysis_charts(100, 40) is True
    assert should_defer_analysis_charts(100, 10) is False
    assert analysis_deps_message() is None or isinstance(analysis_deps_message(), str)

    style = ChartStyle(color_primary="#aabbcc", title_override="테스트")
    save_chart_style(style)
    from df_tool.chart_style import load_chart_style

    loaded = load_chart_style()
    assert loaded.color_primary == "#aabbcc"
    assert loaded.title_override == "테스트"
    assert loaded.resolve_title("자동") == "테스트"
    reset_chart_style()

    html = build_eda_html(df)
    assert "<table>" in html and "age" in html
    assert "data:image/png;base64" in html
    assert "무작위 표본" in html

    pca = compute_pca(df, ["age", "score"])
    assert pca is not None and len(pca.explained_variance_ratio) >= 2

    if sklearn_available():
        mice_df = fill_na_mice(df, ["age", "score"])
        assert mice_df["age"].notna().all()
        try:
            fill_na_mice(pd.DataFrame({"a": [float("nan")]}), ["a"])
            assert False, "expected error"
        except ValueError as exc:
            assert "2개 이상" in str(exc)

    print("qa_analysis_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
