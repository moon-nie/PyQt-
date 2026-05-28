"""loader.py 파일 로드 smoke test."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

from df_tool.loader import _normalize_dataframe_columns, load_file, save_file


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    # CSV
    csv_path = root / "sample_data.csv"
    if csv_path.exists():
        loaded = load_file(csv_path)
        assert len(loaded.dataframe) > 0
        assert all(isinstance(c, str) for c in loaded.dataframe.columns)

    # int 열명 정규화
    raw = pd.DataFrame([[1, 2], [3, 4]])
    raw.columns = [0, 1]
    norm = _normalize_dataframe_columns(raw)
    assert list(norm.columns) == ["0", "1"]

    # HTML 위장 xls (int columns → str after load)
    html = b"""<html><body><table>
    <tr><td>id</td><td>name</td></tr>
    <tr><td>1</td><td>Alice</td></tr>
    <tr><td>2</td><td>Bob</td></tr>
    </table></body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        xls_path = Path(tmp) / "test_int_cols.xls"
        xls_path.write_bytes(html)
        loaded = load_file(xls_path)
        assert all(isinstance(c, str) for c in loaded.dataframe.columns)
        assert loaded.dataframe.shape[1] == 2

        # save round-trip csv
        out_csv = Path(tmp) / "out.csv"
        save_file(out_csv, loaded.dataframe, save_format="csv_utf8_sig")
        assert out_csv.exists()
        reloaded = load_file(out_csv)
        assert len(reloaded.dataframe) == len(loaded.dataframe)

    print("qa_loader_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
