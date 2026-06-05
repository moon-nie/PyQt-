"""PyQt viewer — 열/행 구조 변경 operations (Tk viewer.py 동등)."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import QWidget

from df_tool.qt_dialogs import (
    qt_add_column_dialog,
    qt_confirm,
    qt_duplicate_column_dialog,
    qt_insert_row_dialog,
    qt_merge_columns_dialog,
    qt_rename_column_dialog,
    qt_split_column_dialog,
    qt_sequential_fill_dialog,
)


def insert_row_with_dialog(
    df: pd.DataFrame,
    reference_index,
    position: str,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import insert_row

    label = (
        "선택한 행 위에 빈 행을 추가합니다."
        if position == "above"
        else "선택한 행 아래에 빈 행을 추가합니다."
    )
    result = qt_insert_row_dialog(parent, position_label=label)
    if not result:
        return None
    return insert_row(df, reference_index, position, count=result)


def insert_column_with_dialog(
    df: pd.DataFrame,
    reference_column,
    position: str,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import insert_column

    side = "왼쪽" if position == "left" else "오른쪽"
    hint = f"'{reference_column}' 열의 {side}에 새 열을 추가합니다."
    result = qt_add_column_dialog(parent, position_hint=hint)
    if not result:
        return None
    name, default = result
    try:
        return insert_column(df, reference_column, position, name=name, default=default or pd.NA)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def rename_column_with_dialog(
    df: pd.DataFrame,
    column,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import rename_column

    result = qt_rename_column_dialog(parent, str(column))
    if not result:
        return None
    return rename_column(df, column, result)


def duplicate_column_with_dialog(
    df: pd.DataFrame,
    column,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import duplicate_column, _unique_column_name

    suggested = _unique_column_name(df, f"{column}_copy")
    result = qt_duplicate_column_dialog(parent, str(column), suggested)
    if not result:
        return None
    return duplicate_column(df, column, result)


def merge_columns_with_dialog(
    df: pd.DataFrame,
    columns: list[str],
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import merge_columns

    result = qt_merge_columns_dialog(parent, [str(c) for c in columns])
    if not result:
        return None
    new_name, separator, drop_sources = result
    try:
        return merge_columns(
            df,
            columns,
            new_name,
            separator=separator,
            drop_sources=drop_sources,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def split_column_with_dialog(
    df: pd.DataFrame,
    column,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import parse_separator, split_column

    result = qt_split_column_dialog(parent, str(column))
    if not result:
        return None
    separator, prefix, drop_source = result
    try:
        return split_column(
            df,
            column,
            parse_separator(separator),
            name_prefix=prefix,
            drop_source=drop_source,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def fill_column_with_dialog(
    df: pd.DataFrame,
    column,
    method: str,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import fill_column

    label = "위로 채우기" if method == "ffill" else "아래로 채우기"
    ok = qt_confirm(
        parent,
        label,
        f"'{column}' 열의 빈 칸을 {label}로 채울까요?",
        confirm_text=label,
    )
    if not ok:
        return None
    return fill_column(df, column, method)


def fill_sequential_with_dialog(
    df: pd.DataFrame,
    column,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import fill_sequential

    result = qt_sequential_fill_dialog(parent, str(column))
    if not result:
        return None
    start, step = result
    return fill_sequential(df, column, start=start, step=step)


def delete_column_with_dialog(
    df: pd.DataFrame,
    column,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import delete_column, resolve_column_key

    ok = qt_confirm(
        parent,
        "열 삭제",
        f"'{column}' 열을 삭제할까요?\n\n되돌리려면 Ctrl+Z를 사용하세요.",
        confirm_text="삭제",
    )
    if not ok:
        return None
    if resolve_column_key(df, column) is None:
        raise ValueError(f"열 '{column}'을(를) 찾을 수 없습니다.")
    new_df = delete_column(df, column)
    if len(new_df.columns) == len(df.columns):
        raise ValueError(f"열 '{column}'을(를) 삭제하지 못했습니다.")
    return new_df


def delete_columns_with_dialog(
    df: pd.DataFrame,
    columns: list,
    *,
    parent: QWidget | None = None,
) -> pd.DataFrame | None:
    from df_tool.operations import delete_columns, resolve_column_keys

    n = len(columns)
    if n == 1:
        body = f"'{columns[0]}' 열을 삭제할까요?"
    else:
        preview = ", ".join(str(c) for c in columns[:8])
        if n > 8:
            preview += f" … 외 {n - 8}개"
        body = f"선택한 {n}개 열을 삭제할까요?\n\n{preview}"
    ok = qt_confirm(
        parent,
        "열 삭제",
        f"{body}\n\n되돌리려면 Ctrl+Z를 사용하세요.",
        confirm_text="삭제",
    )
    if not ok:
        return None
    keys = resolve_column_keys(df, columns)
    if not keys:
        raise ValueError("삭제할 열을 찾을 수 없습니다.")
    new_df = delete_columns(df, columns)
    if len(new_df.columns) == len(df.columns):
        raise ValueError("선택한 열을 삭제하지 못했습니다.")
    return new_df
