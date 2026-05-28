"""pandas 데이터 처리 — UI 없이 DataFrame만 변환.

새 기능: 여기에 def 함수 추가 → qt_app.py 또는 qt_viewer.py에서 호출
연결 지도: PROJECT_MAP.md § operations.py
"""
from __future__ import annotations

import pandas as pd

# 타입 변경 드롭다운 옵션 (pandas dtype 이름)
SELECTABLE_DTYPES: list[str] = [
    "object",
    "int64",
    "float64",
    "bool",
    "datetime64[ns]",
]


def column_dtype_display(series: pd.Series) -> str:
    """열의 pandas dtype 문자열 (예: float64, object)."""
    return str(series.dtype)


def is_null_value(value) -> bool:
    if value is None or pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def null_mask(series: pd.Series) -> pd.Series:
    if pd.api.types.is_string_dtype(series) or series.dtype == object:
        return series.map(is_null_value)
    return series.isna()


def count_nulls(series: pd.Series) -> int:
    return int(null_mask(series).sum())


def _normalize_dtype_choice(dtype_name: str) -> str:
    name = dtype_name.strip()
    aliases = {
        "int": "int64",
        "float": "float64",
        "str": "object",
        "string": "object",
        "text": "object",
        "datetime": "datetime64[ns]",
        "bool_": "bool",
    }
    return aliases.get(name, name)


def convert_column_dtype(df: pd.DataFrame, column: str, dtype_name: str) -> pd.DataFrame:
    key = resolve_column_key(df, column)
    if key is None:
        raise ValueError(f"열 '{column}'이(가) 없습니다.")
    target = _normalize_dtype_choice(dtype_name)
    if target not in SELECTABLE_DTYPES:
        raise ValueError(f"지원하지 않는 타입입니다: {dtype_name}")

    result = df.copy()
    series = result[key]
    if target == "object":
        result[key] = series.map(lambda v: pd.NA if pd.isna(v) else str(v)).astype(object)
    elif target == "int64":
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.isna().any():
            result[key] = numeric.round().astype("Int64")
        else:
            result[key] = numeric.round().astype("int64")
    elif target == "float64":
        result[key] = pd.to_numeric(series, errors="coerce").astype("float64")
    elif target == "bool":
        result[key] = _series_to_bool(series)
    elif target == "datetime64[ns]":
        result[key] = pd.to_datetime(series, errors="coerce")
    return result


def _series_to_bool(series: pd.Series) -> pd.Series:
    def to_bool(value):
        if pd.isna(value):
            return pd.NA
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "y", "t"}:
            return True
        if text in {"false", "0", "no", "n", "f"}:
            return False
        return pd.NA

    return series.map(to_bool).astype("boolean")


def rename_column(df: pd.DataFrame, old_name: str, new_name: str) -> pd.DataFrame:
    key = resolve_column_key(df, old_name)
    if key is None:
        raise ValueError(f"열 '{old_name}'이(가) 없습니다.")
    if new_name in df.columns and new_name != key:
        raise ValueError(f"열 이름 '{new_name}'이(가) 이미 존재합니다.")
    result = df.copy()
    result = result.rename(columns={key: new_name})
    return result


def set_cell_value(df: pd.DataFrame, index, column: str, value: str) -> pd.DataFrame:
    result = df.copy()
    col_key = resolve_column_key(result, column)
    if col_key is None:
        return result
    row_key = resolve_index_key(result, index)
    if row_key is None:
        return result
    parsed = _parse_value(value, result[col_key].dtype)
    result.at[row_key, col_key] = parsed
    return result


def clear_cells(df: pd.DataFrame, cells: list[tuple[object, str]]) -> pd.DataFrame:
    result = df.copy()
    for idx, col in cells:
        col_key = resolve_column_key(result, col)
        row_key = resolve_index_key(result, idx)
        if col_key is None or row_key is None:
            continue
        result = set_cell_value(result, row_key, col_key, "")
    return result


def paste_cells(df: pd.DataFrame, assignments: list[tuple[object, str, str]]) -> pd.DataFrame:
    """(행 인덱스, 열 이름, 값) 목록을 한 번에 붙여넣기."""
    result = df.copy()
    for idx, col, value in assignments:
        col_key = resolve_column_key(result, col)
        row_key = resolve_index_key(result, idx)
        if col_key is None or row_key is None:
            continue
        result = set_cell_value(result, row_key, col_key, value)
    return result


def clear_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for col in resolve_column_keys(result, columns):
        result[col] = pd.NA
    return result


def clear_rows(df: pd.DataFrame, indices: list) -> pd.DataFrame:
    result = df.copy()
    valid = resolve_index_keys(result, indices)
    if not valid:
        return result
    for col in result.columns:
        result.loc[valid, col] = pd.NA
    return result


def resolve_index_key(df: pd.DataFrame, index) -> object | None:
    """표시·선택용 인덱스 → DataFrame 실제 행 인덱스."""
    if index in df.index:
        return index
    target = str(index)
    for idx in df.index:
        if str(idx) == target:
            return idx
    return None


def resolve_index_keys(df: pd.DataFrame, indices) -> list:
    keys: list = []
    seen: set = set()
    for index in indices:
        key = resolve_index_key(df, index)
        if key is not None and key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def resolve_column_key(df: pd.DataFrame, column: str | object) -> object | None:
    """표시용 문자열 이름 → DataFrame 실제 열 키 (int 등 비문자열 열명 포함)."""
    if column in df.columns:
        return column
    target = str(column)
    for col in df.columns:
        if str(col) == target:
            return col
    return None


def resolve_column_keys(df: pd.DataFrame, columns: list[str]) -> list:
    keys: list = []
    seen: set = set()
    for column in columns:
        key = resolve_column_key(df, column)
        if key is not None and key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def delete_rows(df: pd.DataFrame, indices) -> pd.DataFrame:
    result = df.copy()
    drop_idx = resolve_index_keys(result, list(indices))
    if not drop_idx:
        return result
    return result.drop(index=drop_idx)


def delete_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    result = df.copy()
    key = resolve_column_key(result, column)
    if key is None:
        return result
    return result.drop(columns=[key])


def delete_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    drop_cols = resolve_column_keys(result, columns)
    if not drop_cols:
        return result
    return result.drop(columns=drop_cols)


def add_column(df: pd.DataFrame, name: str, default="") -> pd.DataFrame:
    if name in df.columns:
        raise ValueError(f"열 이름 '{name}'이(가) 이미 존재합니다.")
    result = df.copy()
    result[name] = default
    return result


def duplicate_column(df: pd.DataFrame, column: str, new_name: str | None = None) -> pd.DataFrame:
    key = resolve_column_key(df, column)
    if key is None:
        raise ValueError(f"열 '{column}'이(가) 없습니다.")
    result = df.copy()
    name = new_name or _unique_column_name(df, f"{key}_copy")
    if name in df.columns:
        raise ValueError(f"열 이름 '{name}'이(가) 이미 존재합니다.")
    result[name] = result[key]
    return result


def sort_dataframe(df: pd.DataFrame, column: str, ascending: bool = True) -> pd.DataFrame:
    key = resolve_column_key(df, column)
    if key is None:
        return df
    return df.sort_values(by=key, ascending=ascending, kind="stable")


def reorder_columns(df: pd.DataFrame, source_column: str, target_column: str) -> pd.DataFrame:
    """source_column을 target_column 위치로 이동."""
    src_key = resolve_column_key(df, source_column)
    tgt_key = resolve_column_key(df, target_column)
    if src_key is None or tgt_key is None or src_key == tgt_key:
        return df
    cols = list(df.columns)
    src_idx = cols.index(src_key)
    tgt_idx = cols.index(tgt_key)
    cols.pop(src_idx)
    cols.insert(tgt_idx, src_key)
    return df[cols]


def find_replace(
    df: pd.DataFrame,
    find: str,
    replace: str,
    column: str | None = None,
    match_case: bool = False,
    row_indices=None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    result = df.copy()

    if columns:
        targets = resolve_column_keys(result, list(columns))
    elif column is not None:
        key = resolve_column_key(result, column)
        targets = [key] if key is not None else []
    else:
        targets = list(result.columns)

    if not targets:
        return result

    row_filter = set(row_indices) if row_indices is not None else None

    for col in targets:
        series = result[col]
        if row_filter is not None:
            mask = series.index.isin(row_filter)
        else:
            mask = pd.Series(True, index=series.index)

        if result[col].dtype == object or pd.api.types.is_string_dtype(result[col]):
            if match_case:
                hit = series.astype(str).str.contains(find, na=False, regex=False) & mask
                result.loc[hit, col] = result.loc[hit, col].astype(str).str.replace(find, replace, regex=False)
            else:
                text = series.astype(str)
                lower_find = find.lower()
                hit = text.str.lower().str.contains(lower_find, na=False, regex=False) & mask
                result.loc[hit, col] = text[hit].apply(
                    lambda value: _replace_ignore_case(value, find, replace)
                )
        else:
            hit = series.astype(str).str.contains(find, na=False, regex=False) & mask
            result.loc[hit, col] = replace

    return result


def insert_row(df: pd.DataFrame, reference_index, position: str = "below", count: int = 1) -> pd.DataFrame:
    result = df.copy()
    ref_key = resolve_index_key(result, reference_index)
    if ref_key is None:
        return result
    loc = result.index.get_loc(ref_key)
    if isinstance(loc, slice):
        loc = loc.start or 0
    insert_pos = loc + 1 if position == "below" else loc

    blank = [{col: pd.NA for col in result.columns} for _ in range(count)]
    new_rows = pd.DataFrame(blank)
    top = result.iloc[:insert_pos]
    bottom = result.iloc[insert_pos:]
    return pd.concat([top, new_rows, bottom], ignore_index=True)


def insert_row_at_end(df: pd.DataFrame, count: int = 1) -> pd.DataFrame:
    blank = [{col: pd.NA for col in df.columns} for _ in range(count)]
    return pd.concat([df, pd.DataFrame(blank)], ignore_index=True)


def insert_column(
    df: pd.DataFrame,
    reference_column: str,
    position: str = "right",
    name: str | None = None,
    default=pd.NA,
) -> pd.DataFrame:
    result = df.copy()
    ref_key = resolve_column_key(result, reference_column)
    if ref_key is None:
        raise ValueError(f"열 '{reference_column}'이(가) 없습니다.")
    col_name = name or _unique_column_name(df, "새열")
    if col_name in result.columns:
        raise ValueError(f"열 이름 '{col_name}'이(가) 이미 존재합니다.")

    cols = list(result.columns)
    loc = cols.index(ref_key)
    insert_pos = loc + 1 if position == "right" else loc
    result.insert(insert_pos, col_name, default)
    return result


def insert_column_at_end(df: pd.DataFrame, name: str | None = None, default=pd.NA) -> pd.DataFrame:
    col_name = name or _unique_column_name(df, "새열")
    return add_column(df, col_name, default)


def fill_sequential(
    df: pd.DataFrame,
    column: str,
    *,
    start: int = 1,
    step: int = 1,
) -> pd.DataFrame:
    """열 전체를 시작값·간격으로 순차 번호 채우기."""
    result = df.copy()
    key = resolve_column_key(result, column)
    if key is None:
        return result
    n = len(result)
    if n == 0:
        return result
    result[key] = [start + i * step for i in range(n)]
    return result


def fill_column(df: pd.DataFrame, column: str, method: str = "ffill") -> pd.DataFrame:
    result = df.copy()
    key = resolve_column_key(result, column)
    if key is None:
        return result
    if method == "ffill":
        result[key] = result[key].ffill()
    elif method == "bfill":
        result[key] = result[key].bfill()
    elif method == "value":
        raise ValueError("값 채우기는 fill_with_value를 사용하세요.")
    return result


def fill_with_value(df: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    result = df.copy()
    key = resolve_column_key(result, column)
    if key is None:
        return result
    parsed = _parse_value(value, result[key].dtype)
    result[key] = result[key].fillna(parsed)
    return result


def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    return df.drop_duplicates(subset=subset, keep="first")


def drop_na_rows(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    targets = resolve_column_keys(df, list(subset)) if subset else list(df.columns)
    if not targets:
        return df.copy()
    mask = pd.Series(False, index=df.index)
    for col in targets:
        mask |= null_mask(df[col])
    return df.loc[~mask].copy()


def concat_dataframes(dfs: list[pd.DataFrame], ignore_index: bool = True) -> pd.DataFrame:
    if not dfs:
        raise ValueError("병합할 데이터가 없습니다.")
    return pd.concat(dfs, axis=0, ignore_index=ignore_index)


def merge_dataframes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_on: str | list[str],
    right_on: str | list[str],
    how: str = "inner",
    suffixes: tuple[str, str] = ("_left", "_right"),
) -> pd.DataFrame:
    return pd.merge(left, right, how=how, left_on=left_on, right_on=right_on, suffixes=suffixes)


def vlookup(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_key: str,
    right_key: str,
    return_column: str,
    new_column: str | None = None,
) -> pd.DataFrame:
    left_key_col = resolve_column_key(left, left_key)
    right_key_col = resolve_column_key(right, right_key)
    return_col = resolve_column_key(right, return_column)
    if left_key_col is None:
        raise ValueError(f"원본에 '{left_key}' 열이 없습니다.")
    if right_key_col is None:
        raise ValueError(f"참조 파일에 '{right_key}' 열이 없습니다.")
    if return_col is None:
        raise ValueError(f"참조 파일에 '{return_column}' 열이 없습니다.")

    lookup = right[[right_key_col, return_col]].drop_duplicates(subset=[right_key_col], keep="first")
    merged = left.merge(
        lookup,
        how="left",
        left_on=left_key_col,
        right_on=right_key_col,
    )

    output_name = new_column or return_column
    if output_name != return_col:
        merged[output_name] = merged[return_col]
        if return_col in merged.columns and return_col != left_key_col:
            merged = merged.drop(columns=[return_col])

    if right_key_col != left_key_col and right_key_col in merged.columns:
        merged = merged.drop(columns=[right_key_col])

    return merged


def vlookup_stats(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_key: str,
    right_key: str,
    return_column: str,
    new_column: str | None = None,
) -> dict[str, int]:
    """VLOOKUP 매칭 통계 (미리보기용)."""
    output_name = new_column or return_column
    result = vlookup(left, right, left_key, right_key, return_column, output_name)
    if output_name not in result.columns:
        return {"total": len(left), "matched": 0, "unmatched": len(left)}
    matched = int(result[output_name].notna().sum())
    total = len(result)
    return {"total": total, "matched": matched, "unmatched": total - matched}


def group_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    value_column: str,
    agg: str,
) -> pd.DataFrame:
    group_keys = resolve_column_keys(df, list(group_columns))
    value_key = resolve_column_key(df, value_column)
    if not group_keys or value_key is None:
        raise ValueError("그룹 열 또는 값 열을 찾을 수 없습니다.")
    grouped = df.groupby(group_keys, dropna=False)[value_key].agg(agg)
    return grouped.reset_index()


def _parse_value(value: str, dtype):
    text = value.strip()
    if text == "":
        return pd.NA

    if pd.api.types.is_numeric_dtype(dtype):
        try:
            if pd.api.types.is_integer_dtype(dtype):
                return int(float(text))
            return float(text)
        except ValueError:
            return text

    if pd.api.types.is_bool_dtype(dtype):
        lowered = text.lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
        return text

    return text


def _unique_column_name(df: pd.DataFrame, base: str) -> str:
    name = base
    counter = 1
    while name in df.columns:
        name = f"{base}_{counter}"
        counter += 1
    return name


def _replace_ignore_case(text: str, find: str, replace: str) -> str:
    lower_text = text.lower()
    lower_find = find.lower()
    result = []
    start = 0
    while True:
        idx = lower_text.find(lower_find, start)
        if idx == -1:
            result.append(text[start:])
            break
        result.append(text[start:idx])
        result.append(replace)
        start = idx + len(find)
    return "".join(result)
