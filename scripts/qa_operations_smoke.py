"""operations.py 핵심 함수 smoke test."""
from __future__ import annotations

import sys

import pandas as pd

from df_tool.operations import (
    clear_cells,
    delete_columns,
    duplicate_column,
    find_replace,
    group_summary,
    insert_column,
    reorder_columns,
    resolve_column_key,
    set_cell_value,
    sort_dataframe,
    vlookup,
)


def _int_cols_df() -> pd.DataFrame:
    df = pd.DataFrame([[10, 20], [30, 40]])
    df.columns = [0, 1]
    return df


def main() -> int:
    # int 열명 resolve
    df = _int_cols_df()
    assert resolve_column_key(df, "0") == 0
    assert resolve_column_key(df, 0) == 0

    # set_cell_value / clear
    df = set_cell_value(df, 0, "0", "99")
    assert df.at[0, 0] == 99
    df = clear_cells(df, [(0, 0)])
    assert pd.isna(df.at[0, 0])

    # reorder int columns
    df = _int_cols_df()
    reordered = reorder_columns(df, 0, 1)
    assert list(reordered.columns) == [1, 0]

    # sort int column 0
    df = pd.DataFrame({0: [3, 1, 2]})
    sorted_df = sort_dataframe(df, "0")
    assert sorted_df[0].tolist() == [1, 2, 3]

    # find_replace on column 0
    df = pd.DataFrame({0: ["abc", "xyz"]})
    replaced = find_replace(df, "a", "Z", column=0)
    assert replaced.at[0, 0] == "Zbc"

    # insert_column after int ref
    df = _int_cols_df()
    inserted = insert_column(df, 0, "right", name="new")
    assert list(inserted.columns) == [0, "new", 1]

    # duplicate / delete
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    dup = duplicate_column(df, "A", "A2")
    assert "A2" in dup.columns
    deleted = delete_columns(dup, ["A2"])
    assert list(deleted.columns) == ["A", "B"]

    # vlookup
    left = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    right = pd.DataFrame({"id": [1, 2], "score": [90, 80]})
    merged = vlookup(left, right, "id", "id", "score", "점수")
    assert merged["점수"].tolist() == [90, 80]

    # group_summary
    gdf = pd.DataFrame({"g": ["x", "x", "y"], "v": [1, 2, 3]})
    summary = group_summary(gdf, ["g"], "v", "sum")
    assert len(summary) == 2

    print("qa_operations_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
