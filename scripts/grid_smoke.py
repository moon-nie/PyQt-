"""GridModel / GridView smoke test (headless)."""
from __future__ import annotations

import os
import sys

# headless Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication

from df_tool.grid import GridModel, GridView
from df_tool.grid.header import GridHeaderView, GridHorizontalHeader
from df_tool.qt_viewer import DataFrameViewer


def test_grid_model_int_columns() -> None:
    df = pd.DataFrame({0: ["a", "b"], 1: [1, 2]}, index=[10, 20])
    model = GridModel()
    model.set_dataframe(df)
    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.column_name_at(0) == 0
    assert model.data(model.index(0, 0)) == "a"
    assert model.source_index_at(0) == 10


def test_viewer_api() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = DataFrameViewer()
    df = pd.DataFrame({"name": ["x"], "val": [0]}, index=[0])
    viewer.set_dataframe(df, new_session=True)
    assert viewer.get_dataframe() is not None
    assert len(viewer.get_dataframe()) == 1
    sel = viewer.get_selection()
    assert sel.mode == "none"
    viewer.prepare_for_new_dataset()
    app.processEvents()


def test_cell_edit_sync() -> None:
    df = pd.DataFrame({"a": ["x"]}, index=[0])
    model = GridModel()
    model.set_dataframe(df)

    def commit(idx, col, text: str) -> bool:
        nonlocal df
        from df_tool.operations import set_cell_value

        df = set_cell_value(df, idx, col, text)
        model.replace_dataframe(df)
        return True

    model.set_commit_handler(commit)
    ok = model.setData(model.index(0, 0), "hello", Qt.ItemDataRole.EditRole)
    assert ok
    assert model.data(model.index(0, 0)) == "hello"


def test_column_insert_restructure() -> None:
    from df_tool.operations import insert_column

    df = pd.DataFrame({"a": [1], "b": [2]})
    model = GridModel()
    model.set_dataframe(df)
    assert model.columnCount() == 2
    new_df = insert_column(df, "a", "right", name="c")
    model.set_dataframe(new_df, reset_sort=False)
    assert model.columnCount() == 3
    assert "c" in model.all_column_names()


def test_header_context_menu() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = DataFrameViewer()
    df = pd.DataFrame({"a": [1], "b": [2]}, index=[0])
    viewer.set_dataframe(df, new_session=True)
    h_header = viewer._table.horizontalHeader()
    v_header = viewer._table.verticalHeader()
    assert isinstance(h_header, GridHorizontalHeader)
    assert isinstance(v_header, GridHeaderView)
    pos = QPoint(10, max(1, h_header.height() // 2))
    assert DataFrameViewer._header_section_at(h_header, pos) == 0
    assert DataFrameViewer._header_section_at(v_header, pos) == 0
    app.processEvents()


def test_column_reorder() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = DataFrameViewer()
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]}, index=[0])
    viewer.set_dataframe(df, new_session=True)
    viewer._on_column_reorder(2, 0)
    app.processEvents()
    cols = list(viewer.get_dataframe().columns)
    assert cols == ["c", "a", "b"]
    app.processEvents()


def test_column_selection_context() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = DataFrameViewer()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]}, index=[0, 1])
    viewer.set_dataframe(df, new_session=True)
    viewer._select_column("a")
    assert viewer._has_column_selection()
    assert viewer._column_menu_target("b") == "a"
    assert viewer._column_menu_target("a") == "a"
    app.processEvents()


def main() -> int:
    test_grid_model_int_columns()
    test_cell_edit_sync()
    test_column_insert_restructure()
    test_viewer_api()
    test_header_context_menu()
    test_column_reorder()
    test_column_selection_context()
    print("grid_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
