"""이상치 탐지·제거(IQR·Z-score·Isolation Forest) — `operations`에서 분리한 leaf 도메인.

공용 헬퍼(`null_mask`·`resolve_column_keys` 등)는 호출 시점에 `operations`에서
가져오므로 순환 import가 발생하지 않는다. 공개 진입점은 `operations`의 re-export다.
"""
from __future__ import annotations

import pandas as pd


def _outlier_mask_iqr(series: pd.Series, *, iqr_k: float = 1.5) -> pd.Series:
    import df_tool.operations as ops

    valid = series[~ops.null_mask(series)].astype(float)
    if len(valid) < 4:
        return pd.Series(False, index=series.index)
    q1 = valid.quantile(0.25)
    q3 = valid.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return pd.Series(False, index=series.index)
    k = max(0.1, float(iqr_k))
    low = q1 - k * iqr
    high = q3 + k * iqr
    numeric = pd.to_numeric(series, errors="coerce")
    return (numeric < low) | (numeric > high)


def _outlier_mask_zscore(series: pd.Series, *, z_threshold: float = 3.0) -> pd.Series:
    valid = pd.to_numeric(series, errors="coerce")
    mask_null = valid.isna()
    non_null = valid[~mask_null]
    if len(non_null) < 2:
        return pd.Series(False, index=series.index)
    mean = non_null.mean()
    std = non_null.std()
    if std == 0 or pd.isna(std):
        return pd.Series(False, index=series.index)
    z = (valid - mean).abs() / std
    return (z > z_threshold) & ~mask_null


def _outlier_mask_isolation_forest(
    df: pd.DataFrame,
    columns: list[str],
    *,
    contamination: float = 0.05,
) -> pd.Series:
    import df_tool.operations as ops
    from sklearn.ensemble import IsolationForest

    keys = ops.resolve_column_keys(df, columns)
    numeric_keys = [k for k in keys if ops.column_supports_numeric_fill(df[k])]
    if not numeric_keys:
        return pd.Series(False, index=df.index)
    numeric = df[numeric_keys].apply(pd.to_numeric, errors="coerce")
    valid = numeric.dropna()
    if len(valid) < 10:
        return pd.Series(False, index=df.index)
    contamination = max(0.01, min(contamination, 0.5))
    clf = IsolationForest(contamination=contamination, random_state=42, n_jobs=1)
    preds = clf.fit_predict(valid)
    mask = pd.Series(False, index=df.index)
    mask.loc[valid.index] = preds == -1
    return mask


def outlier_row_mask(
    df: pd.DataFrame,
    columns: list[str],
    method: str,
    *,
    z_threshold: float = 3.0,
    contamination: float = 0.05,
    iqr_k: float = 1.5,
) -> pd.Series:
    """선택 열 중 하나라도 이상치이면 True."""
    import df_tool.operations as ops

    if method == "isolation_forest":
        return _outlier_mask_isolation_forest(df, columns, contamination=contamination)
    keys = ops.resolve_column_keys(df, columns)
    numeric_keys = [k for k in keys if ops.column_supports_numeric_fill(df[k])]
    if not numeric_keys:
        return pd.Series(False, index=df.index)
    combined = pd.Series(False, index=df.index)
    for key in numeric_keys:
        if method == "iqr":
            col_mask = _outlier_mask_iqr(df[key], iqr_k=iqr_k)
        elif method == "zscore":
            col_mask = _outlier_mask_zscore(df[key], z_threshold=z_threshold)
        else:
            raise ValueError(f"지원하지 않는 이상치 방식: {method}")
        combined |= col_mask.fillna(False)
    return combined


def drop_outlier_rows(
    df: pd.DataFrame,
    columns: list[str],
    method: str,
    *,
    z_threshold: float = 3.0,
    contamination: float = 0.05,
    iqr_k: float = 1.5,
) -> tuple[pd.DataFrame, int, pd.Series]:
    """이상치 행 제거. (결과 df, 제거 건수, 이상치 마스크) 반환."""
    mask = outlier_row_mask(
        df,
        columns,
        method,
        z_threshold=z_threshold,
        contamination=contamination,
        iqr_k=iqr_k,
    )
    removed = int(mask.sum())
    return df.loc[~mask].copy(), removed, mask
