"""결측치 ML 대체(KNN·MICE) — `operations`에서 분리한 leaf 도메인.

scikit-learn에만 의존하는 무거운 대체 로직을 모았다.
공용 헬퍼(`null_mask` 등)는 `operations`에서 호출 시점에 가져오므로
순환 import가 발생하지 않는다. 공개 진입점은 `operations`의 re-export다.
"""
from __future__ import annotations

import pandas as pd


def fill_na_knn(
    df: pd.DataFrame,
    columns: list[str],
    *,
    n_neighbors: int = 5,
) -> pd.DataFrame:
    """숫자 열의 결측치를 KNNImputer로 대체합니다."""
    import df_tool.operations as ops
    from sklearn.impute import KNNImputer

    result = df.copy()
    keys = ops.resolve_column_keys(result, columns)
    numeric_keys = [k for k in keys if ops.column_supports_numeric_fill(result[k])]
    if not numeric_keys:
        raise ValueError("KNN 대체에 사용할 숫자 열이 없습니다.")
    has_null = any(ops.null_mask(result[k]).any() for k in numeric_keys)
    if not has_null:
        return result
    if len(result) < 2:
        raise ValueError("KNN 대체는 데이터 행이 2개 이상 필요합니다.")

    n_neighbors = max(1, min(n_neighbors, len(result) - 1))
    imputer = KNNImputer(n_neighbors=n_neighbors)
    imputed = imputer.fit_transform(result[numeric_keys].astype(float))
    for i, key in enumerate(numeric_keys):
        mask = ops.null_mask(result[key])
        if mask.any():
            result.loc[mask, key] = imputed[mask.to_numpy(), i]
    return result


def fill_na_mice(
    df: pd.DataFrame,
    columns: list[str],
    *,
    max_iter: int = 10,
) -> pd.DataFrame:
    """숫자 열 결측치를 IterativeImputer(MICE)로 대체합니다."""
    import df_tool.operations as ops
    from sklearn.experimental import enable_iterative_imputer  # noqa: F401
    from sklearn.impute import IterativeImputer

    result = df.copy()
    keys = ops.resolve_column_keys(result, columns)
    numeric_keys = [k for k in keys if ops.column_supports_numeric_fill(result[k])]
    if not numeric_keys:
        raise ValueError("MICE 대체에 사용할 숫자 열이 없습니다.")
    has_null = any(ops.null_mask(result[k]).any() for k in numeric_keys)
    if not has_null:
        return result
    if len(result) < 2:
        raise ValueError("MICE 대체는 데이터 행이 2개 이상 필요합니다.")

    max_iter = max(1, min(max_iter, 50))
    imputer = IterativeImputer(max_iter=max_iter, random_state=42)
    imputed = imputer.fit_transform(result[numeric_keys].astype(float))
    for i, key in enumerate(numeric_keys):
        mask = ops.null_mask(result[key])
        if mask.any():
            result.loc[mask, key] = imputed[mask.to_numpy(), i]
    return result
