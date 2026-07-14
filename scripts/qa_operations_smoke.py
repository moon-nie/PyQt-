"""operations.py 핵심 함수 smoke test."""
from __future__ import annotations

import sys

import pandas as pd

from df_tool.operations import (
    clear_cells,
    count_nulls,
    delete_columns,
    duplicate_column,
    fill_na,
    find_replace,
    merge_columns,
    parse_separator,
    split_column,
    group_summary,
    insert_column,
    insert_row_at_end,
    paste_cells,
    reorder_columns,
    resolve_column_key,
    extract_rows,
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

    same_key = pd.DataFrame({"상품명": ["사과", "배"], "가격": [1, 2]})
    ref = pd.DataFrame({"상품명": ["사과", "배"], "재고": [10, 20]})
    out = vlookup(same_key, ref, "상품명", "상품명", "재고", "재고")
    assert out["재고"].tolist() == [10, 20]

    # merge_columns
    mdf = pd.DataFrame({"A": ["서울", "부산"], "B": ["강남", "해운대"]})
    merged_cols = merge_columns(mdf, ["A", "B"], "주소", separator=" ", drop_sources=True)
    assert list(merged_cols.columns) == ["주소"]
    assert merged_cols["주소"].tolist() == ["서울 강남", "부산 해운대"]

    assert parse_separator(r"\t") == "\t"
    sdf = pd.DataFrame({"addr": ["서울-강남", "부산-해운대", None]})
    split_df = split_column(sdf, "addr", "-", name_prefix="주소")
    assert "주소_1" in split_df.columns and "주소_2" in split_df.columns
    assert split_df["주소_1"].tolist()[0] == "서울"

    # fill_na
    na_df = pd.DataFrame({"score": [1.0, None, 3.0, None]})
    filled = fill_na(na_df, "score", "median")
    assert count_nulls(filled["score"]) == 0
    assert filled["score"].tolist()[1] == 2.0

    # group_summary
    gdf = pd.DataFrame({"g": ["x", "x", "y"], "v": [1, 2, 3]})
    summary = group_summary(gdf, ["g"], "v", "sum")
    assert len(summary) == 2

    # paste_cells (엑셀 TSV 격자 붙여넣기)
    pdf = pd.DataFrame({"A": [None, None], "B": [None, None]})
    pasted = paste_cells(
        pdf,
        [
            (0, "A", "1"),
            (0, "B", "2"),
            (1, "A", "3"),
            (1, "B", "4"),
        ],
    )
    assert pasted["A"].tolist() == ["1", "3"]
    assert pasted["B"].tolist() == ["2", "4"]

    extended = insert_row_at_end(pdf, 1)
    assert len(extended) == 3

    # extract_rows: 지정 행만 유지·순서 보존
    src = pd.DataFrame({"city": ["서울", "부산", "서울", "대구"], "n": [1, 2, 3, 4]})
    extracted = extract_rows(src, [0, 2])
    assert list(extracted.index) == [0, 2]
    assert extracted["city"].tolist() == ["서울", "서울"]
    assert extract_rows(src, []).empty and list(extract_rows(src, []).columns) == ["city", "n"]

    print("qa_operations_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
