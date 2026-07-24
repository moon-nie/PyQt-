"""EDA 분석 — 통계·차트 추천 (PyQt import 금지)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from df_tool.operations import (
    column_supports_numeric_fill,
    count_nulls,
    null_mask,
    outlier_row_mask,
    resolve_column_key,
)

PLOT_MAX_ROWS = 5000


def format_stat_number(value: float | int | None, *, max_decimals: int = 6) -> str:
    """통계·축 눈금용 — 지수 표기(e+06) 없이 읽기 쉬운 문자열."""
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        pass
    v = float(value)
    if abs(v) < 1e-12:
        return "0"
    if abs(v - round(v)) < 1e-9 and abs(v) < 1e15:
        return f"{int(round(v)):,}"
    av = abs(v)
    if av >= 1000:
        text = f"{v:,.2f}"
    elif av >= 1:
        text = f"{v:,.4f}"
    else:
        text = f"{v:,.{max_decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def nice_axis_limits(
    lo: float,
    hi: float,
    *,
    padding: float = 0.06,
) -> tuple[float, float]:
    """차트 축 여백을 두고 보기 좋은 범위."""
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi:
        delta = abs(lo) * 0.1 if lo != 0 else 1.0
        return lo - delta, hi + delta
    span = hi - lo
    return lo - span * padding, hi + span * padding


def column_kind(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if column_supports_numeric_fill(series):
        return "numeric"
    if pd.api.types.is_bool_dtype(series):
        return "categorical"
    nunique = series.nunique(dropna=True)
    if nunique <= 30 or isinstance(series.dtype, pd.CategoricalDtype):
        return "categorical"
    return "other"


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if column_supports_numeric_fill(df[c])]


def categorical_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if column_kind(df[c]) == "categorical"]


def all_column_names(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns]


def sample_for_plot(df: pd.DataFrame, max_rows: int = PLOT_MAX_ROWS) -> tuple[pd.DataFrame, bool]:
    if len(df) <= max_rows:
        return df, False
    return df.sample(max_rows, random_state=42), True


@dataclass
class ColumnOverview:
    name: str
    kind: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    mean: float | None = None
    std: float | None = None
    min_val: float | None = None
    max_val: float | None = None


@dataclass
class EdaOverview:
    row_count: int
    col_count: int
    columns: list[ColumnOverview] = field(default_factory=list)


def eda_overview(df: pd.DataFrame) -> EdaOverview:
    cols: list[ColumnOverview] = []
    n = len(df)
    for col in df.columns:
        series = df[col]
        nulls = count_nulls(series)
        kind = column_kind(series)
        entry = ColumnOverview(
            name=str(col),
            kind=kind,
            dtype=str(series.dtype),
            null_count=nulls,
            null_pct=(nulls / n * 100) if n else 0.0,
            unique_count=int(series.nunique(dropna=True)),
        )
        if kind == "numeric":
            valid = pd.to_numeric(series, errors="coerce").dropna()
            if len(valid):
                entry.mean = float(valid.mean())
                entry.std = float(valid.std()) if len(valid) > 1 else 0.0
                entry.min_val = float(valid.min())
                entry.max_val = float(valid.max())
        cols.append(entry)
    return EdaOverview(row_count=n, col_count=len(df.columns), columns=cols)


def missing_summary(df: pd.DataFrame) -> list[tuple[str, int, float]]:
    n = len(df)
    out: list[tuple[str, int, float]] = []
    for col in df.columns:
        nulls = count_nulls(df[col])
        if nulls > 0:
            pct = (nulls / n * 100) if n else 0.0
            out.append((str(col), nulls, pct))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


@dataclass
class NumericUnivariateStats:
    count: int
    mean: float
    std: float
    variance: float
    min_val: float
    q1: float
    median: float
    q3: float
    max_val: float
    range_val: float
    iqr: float


@dataclass
class CategoricalUnivariateStats:
    count: int
    unique: int
    mode: str
    mode_count: int
    mode_pct: float


@dataclass
class BivariatePairInfo:
    pair_kind: str  # num_num | cat_num | num_cat | cat_cat | other
    x_kind: str
    y_kind: str
    label: str


@dataclass
class BivariateNumericStats:
    pearson_r: float
    pearson_p: float | None
    spearman_r: float | None
    n: int


def univariate_numeric_stats(series: pd.Series) -> NumericUnivariateStats | None:
    nums = pd.to_numeric(series, errors="coerce").dropna()
    if len(nums) == 0:
        return None
    q1 = float(nums.quantile(0.25))
    q3 = float(nums.quantile(0.75))
    min_v = float(nums.min())
    max_v = float(nums.max())
    std = float(nums.std()) if len(nums) > 1 else 0.0
    return NumericUnivariateStats(
        count=int(len(nums)),
        mean=float(nums.mean()),
        std=std,
        variance=float(nums.var()) if len(nums) > 1 else 0.0,
        min_val=min_v,
        q1=q1,
        median=float(nums.median()),
        q3=q3,
        max_val=max_v,
        range_val=max_v - min_v,
        iqr=q3 - q1,
    )


def univariate_categorical_freq(series: pd.Series, top_n: int = 20) -> list[tuple[str, int, float]]:
    valid = series[~null_mask(series)].astype(str)
    n = len(valid)
    if n == 0:
        return []
    counts = valid.value_counts()
    out: list[tuple[str, int, float]] = []
    for name, cnt in counts.head(top_n).items():
        out.append((str(name), int(cnt), cnt / n * 100))
    return out


def univariate_categorical_stats(series: pd.Series) -> CategoricalUnivariateStats | None:
    valid = series[~null_mask(series)].astype(str)
    if len(valid) == 0:
        return None
    counts = valid.value_counts()
    mode = str(counts.index[0])
    mode_count = int(counts.iloc[0])
    return CategoricalUnivariateStats(
        count=len(valid),
        unique=int(valid.nunique()),
        mode=mode,
        mode_count=mode_count,
        mode_pct=mode_count / len(valid) * 100,
    )


def univariate_chart_options(series: pd.Series) -> list[str]:
    kind = column_kind(series)
    if kind == "numeric":
        return ["histogram", "kde", "boxplot"]
    if kind == "categorical":
        return ["bar", "pie"]
    return ["bar"]


def suggest_univariate_chart(series: pd.Series) -> str:
    opts = univariate_chart_options(series)
    return opts[0] if opts else "bar"


def bivariate_pair_info(x: pd.Series, y: pd.Series) -> BivariatePairInfo:
    xk = column_kind(x)
    yk = column_kind(y)
    if xk == "numeric" and yk == "numeric":
        return BivariatePairInfo("num_num", xk, yk, "수치 × 수치")
    if xk == "categorical" and yk == "numeric":
        return BivariatePairInfo("cat_num", xk, yk, "범주 × 수치")
    if xk == "numeric" and yk == "categorical":
        return BivariatePairInfo("num_cat", xk, yk, "수치 × 범주")
    if xk == "categorical" and yk == "categorical":
        return BivariatePairInfo("cat_cat", xk, yk, "범주 × 범주")
    return BivariatePairInfo("other", xk, yk, "기타 조합")


def bivariate_chart_options(x: pd.Series, y: pd.Series) -> list[str]:
    info = bivariate_pair_info(x, y)
    if info.pair_kind == "num_num":
        return ["scatter", "hexbin", "corr_line"]
    if info.pair_kind in {"cat_num", "num_cat"}:
        return ["box", "violin", "bar_mean"]
    if info.pair_kind == "cat_cat":
        return ["heatmap", "stacked_bar", "grouped_bar"]
    return ["heatmap"]


def suggest_bivariate_chart(x: pd.Series, y: pd.Series) -> str:
    opts = bivariate_chart_options(x, y)
    return opts[0] if opts else "heatmap"


def bivariate_numeric_correlation(x: pd.Series, y: pd.Series) -> BivariateNumericStats | None:
    xv = pd.to_numeric(x, errors="coerce")
    yv = pd.to_numeric(y, errors="coerce")
    mask = xv.notna() & yv.notna()
    if mask.sum() < 2:
        return None
    xs = xv[mask]
    ys = yv[mask]
    pearson_r = float(xs.corr(ys))
    spearman_r = float(xs.corr(ys, method="spearman"))
    pearson_p = None
    try:
        from scipy.stats import pearsonr

        pearson_p = float(pearsonr(xs, ys).pvalue)
    except Exception:
        pass
    return BivariateNumericStats(pearson_r=pearson_r, pearson_p=pearson_p, spearman_r=spearman_r, n=int(mask.sum()))


def bivariate_crosstab_table(
    x: pd.Series,
    y: pd.Series,
    *,
    max_rows: int = 15,
    max_cols: int = 15,
) -> pd.DataFrame:
    ct = pd.crosstab(x.astype(str), y.astype(str))
    if len(ct) > max_rows:
        ct = ct.iloc[:max_rows]
    if len(ct.columns) > max_cols:
        ct = ct.iloc[:, :max_cols]
    return ct


def correlation_matrix(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    cols = columns or numeric_columns(df)
    keys = [resolve_column_key(df, c) for c in cols]
    keys = [k for k in keys if k is not None and column_supports_numeric_fill(df[k])]
    if len(keys) < 2:
        return pd.DataFrame()
    numeric = df[keys].apply(pd.to_numeric, errors="coerce")
    return numeric.corr()


def outlier_summary(
    df: pd.DataFrame,
    columns: list[str],
    method: str,
    *,
    z_threshold: float = 3.0,
    contamination: float = 0.05,
    iqr_k: float = 1.5,
) -> list[tuple[str, int, float]]:
    """열별 이상치 건수·비율."""
    if method == "isolation_forest":
        n = len(df)
        cnt = int(outlier_row_mask(df, columns, method, contamination=contamination).sum())
        pct = (cnt / n * 100) if n else 0.0
        return [("전체 행 (Isolation Forest)", cnt, pct)]
    n = len(df)
    out: list[tuple[str, int, float]] = []
    for col in columns:
        key = resolve_column_key(df, col)
        if key is None or not column_supports_numeric_fill(df[key]):
            continue
        if method == "iqr":
            from df_tool.operations import _outlier_mask_iqr

            mask = _outlier_mask_iqr(df[key], iqr_k=iqr_k)
        else:
            from df_tool.operations import _outlier_mask_zscore

            mask = _outlier_mask_zscore(df[key], z_threshold=z_threshold)
        cnt = int(mask.sum())
        pct = (cnt / n * 100) if n else 0.0
        out.append((str(key), cnt, pct))
    return out


def count_outlier_rows(
    df: pd.DataFrame,
    columns: list[str],
    method: str,
    *,
    z_threshold: float = 3.0,
    contamination: float = 0.05,
    iqr_k: float = 1.5,
) -> int:
    return int(
        outlier_row_mask(
            df,
            columns,
            method,
            z_threshold=z_threshold,
            contamination=contamination,
            iqr_k=iqr_k,
        ).sum()
    )


def knn_fill_preview(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[int, int | None, list[str]]:
    """KNN 대상 열·적용 전 결측 건수.

    두 번째 값(after)은 미리보기에서 실제 impute를 돌리지 않으므로 항상 ``None``.
    (UI는 ‘적용 시 채움’으로 안내해야 함 — 예전에 before를 after로 쓰던 오해 방지.)
    """
    from df_tool.operations import resolve_column_keys

    keys = resolve_column_keys(df, columns)
    numeric_keys = [k for k in keys if column_supports_numeric_fill(df[k])]
    before = sum(count_nulls(df[k]) for k in numeric_keys)
    return before, None, [str(k) for k in numeric_keys]


def default_univariate_column(df: pd.DataFrame) -> str | None:
    nums = numeric_columns(df)
    if nums:
        return nums[0]
    cols = all_column_names(df)
    return cols[0] if cols else None


@dataclass
class PcaResult:
    scores: pd.DataFrame
    explained_variance_ratio: list[float]
    component_labels: list[str]


def compute_pca(
    df: pd.DataFrame,
    columns: list[str],
    *,
    n_components: int = 2,
) -> PcaResult | None:
    """숫자 열 PCA — 결측 행 제외 후 주성분 점수."""
    from sklearn.decomposition import PCA

    keys = [resolve_column_key(df, c) for c in columns]
    keys = [k for k in keys if k is not None and column_supports_numeric_fill(df[k])]
    if len(keys) < 2:
        return None
    numeric = df[keys].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric) < 3:
        return None
    n_comp = min(n_components, len(keys), len(numeric))
    pca = PCA(n_components=n_comp)
    transformed = pca.fit_transform(numeric)
    labels = [f"PC{i + 1}" for i in range(n_comp)]
    scores = pd.DataFrame(transformed, index=numeric.index, columns=labels)
    return PcaResult(
        scores=scores,
        explained_variance_ratio=[float(v) for v in pca.explained_variance_ratio_],
        component_labels=labels,
    )


def default_bivariate_pair(df: pd.DataFrame) -> tuple[str | None, str | None]:
    nums = numeric_columns(df)
    if len(nums) >= 2:
        return nums[0], nums[1]
    cols = all_column_names(df)
    if len(cols) >= 2:
        return cols[0], cols[1]
    if cols:
        return cols[0], cols[0]
    return None, None


def _available_matplotlib_font_names() -> set[str]:
    """Matplotlib이 실제로 찾을 수 있는 폰트 family 이름."""
    from matplotlib import font_manager

    return {font.name for font in font_manager.fontManager.ttflist}


def preferred_korean_matplotlib_font() -> str | None:
    """현재 OS에 설치된 한글 표시 가능성이 높은 Matplotlib 폰트 이름.

    macOS에서는 `AppleGothic` 또는 `Apple SD Gothic Neo`, Windows에서는
    `Malgun Gothic`, Linux에서는 Noto/Nanum 계열을 우선한다.
    """
    candidates = (
        "AppleGothic",
        "Apple SD Gothic Neo",
        "Malgun Gothic",
        "NanumGothic",
        "Nanum Gothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "Noto Sans CJK",
        "Source Han Sans KR",
        "Source Han Sans",
    )
    available = _available_matplotlib_font_names()
    for family in candidates:
        if family in available:
            return family
    return None


def configure_matplotlib_font() -> None:
    """한글 차트용 기본 폰트.

    Matplotlib은 없는 폰트 이름을 지정해도 즉시 예외를 내지 않고 나중에
    렌더링 단계에서 fallback을 시도할 수 있다. 그래서 설치된 폰트를 먼저
    font_manager로 확인한 뒤 지정한다. (macOS 한글 네모 표시 방지)
    """
    import matplotlib.pyplot as plt

    family = preferred_korean_matplotlib_font()
    if family:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [family, "DejaVu Sans"]
    else:
        plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.titlesize"] = 12
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["xtick.labelsize"] = 10
    plt.rcParams["ytick.labelsize"] = 10
