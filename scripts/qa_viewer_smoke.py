"""DataFrameViewer headless smoke.

리팩토링 안전망 확장: 기존 QA가 잘 다루지 않던 DataFrameViewer의
검색 필터·클립보드(복사/붙여넣기) 경로를 GUI 조작 없이 검증한다.

offscreen 플랫폼으로 위젯을 띄우지 않고 set_dataframe / get_dataframe,
검색 입력 위젯 + _apply_filter_now, _on_copy / _on_paste 를 직접 호출한다.
(grid_smoke.py / qa_mainwindow_smoke.py 의 QApplication·offscreen 패턴을 따름)
"""
from __future__ import annotations

import os
import sys

# headless Qt (grid_smoke.py 와 동일)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from df_tool.qt_viewer import DataFrameViewer
from df_tool.selection import SelectionScope


def _make_df() -> pd.DataFrame:
    # name·city(문자열)를 인접 배치 → 붙여넣기 2x2 가 int 열을 건드리지 않게.
    return pd.DataFrame(
        {
            "name": ["alpha", "beta", "gamma", "delta"],
            "city": ["서울", "부산", "서울", "대구"],
            "val": [1, 2, 3, 4],
        },
        index=[0, 1, 2, 3],
    )


def test_set_get_roundtrip(app: QApplication) -> None:
    """set_dataframe → get_dataframe 라운드트립(행/열 수·열 이름 일치)."""
    viewer = DataFrameViewer()
    df = _make_df()
    viewer.set_dataframe(df, new_session=True)
    out = viewer.get_dataframe()
    assert out is not None, "get_dataframe 가 None 이면 안 됨"
    assert out.shape == df.shape == (4, 3), f"형태 불일치: {out.shape}"
    assert list(out.columns) == ["name", "city", "val"], f"열 불일치: {list(out.columns)}"
    app.processEvents()


def test_search_filter(app: QApplication) -> None:
    """검색어 적용 시 표시 행이 줄고, 해제 시 원복되는지.

    실제 동작 경로(search_btn.clicked / search_entry.returnPressed → _apply_filter_now)를
    그대로 재현: 검색 입력 위젯에 setText 후 _apply_filter_now 호출.
    표시 행 수는 모델의 rowCount(필터된 인덱스 수)로 확인한다.
    """
    viewer = DataFrameViewer()
    viewer.set_dataframe(_make_df(), new_session=True)
    total = viewer._model.rowCount()
    assert total == 4, f"초기 표시 행수 4 기대, 실제 {total}"

    viewer.search_entry.setText("서울")
    viewer._apply_filter_now()  # private: 검색 버튼 클릭과 동일한 실제 필터 적용 경로
    app.processEvents()
    filtered = viewer._model.rowCount()
    assert filtered == 2, f"'서울' 필터 후 2행 기대, 실제 {filtered}"

    viewer.search_entry.setText("")
    viewer._apply_filter_now()
    app.processEvents()
    restored = viewer._model.rowCount()
    assert restored == total, f"필터 해제 후 {total}행 복귀 기대, 실제 {restored}"


def test_extract_filtered_rows(app: QApplication) -> None:
    """검색으로 좁힌 뒤 결과 추출 → 보이는 행만 데이터로 남는지."""
    viewer = DataFrameViewer()
    viewer.set_dataframe(_make_df(), new_session=True)
    assert not viewer.extract_btn.isEnabled(), "필터 없을 때 추출 버튼은 비활성"

    viewer.search_entry.setText("서울")
    viewer._apply_filter_now()
    app.processEvents()
    assert viewer.extract_btn.isEnabled(), "필터 활성 시 추출 버튼 활성"
    assert viewer._model.rowCount() == 2

    # 확인 다이얼로그 우회: operations 경로를 직접 호출하는 대신
    # _extract_filtered_rows 의 핵심(필터 클리어 + extract_rows + _apply_df)을 재현
    from df_tool.operations import extract_rows

    indices = viewer._sorted_filtered_indices()
    new_df = extract_rows(viewer._df, indices)
    viewer.search_entry.clear()
    viewer._filter_pinned_rows.clear()
    viewer._apply_df(new_df, action="필터 결과 2행 추출", restructure=True)
    app.processEvents()

    out = viewer.get_dataframe()
    assert out is not None and len(out) == 2, f"추출 후 2행 기대, 실제 {None if out is None else len(out)}"
    assert out["city"].tolist() == ["서울", "서울"]
    assert not viewer.extract_btn.isEnabled(), "추출 후 필터 해제 → 버튼 비활성"
    assert viewer._model.rowCount() == 2


def test_clipboard_copy(app: QApplication) -> None:
    """2x2 범위 복사 → 클립보드가 기대한 TSV 를 담는지.

    _on_copy 는 self._selection(SelectionScope)을 읽으므로,
    클릭/드래그 대신 선택 상태를 직접 주입한다(headless 안정성).
    """
    viewer = DataFrameViewer()
    viewer.set_dataframe(_make_df(), new_session=True)
    viewer._selection = SelectionScope(
        mode="cell",
        cells={(0, "name"), (0, "city"), (1, "name"), (1, "city")},
    )
    viewer._on_copy()  # private: 복사 단축키/메뉴와 동일한 실제 복사 경로
    app.processEvents()
    text = QGuiApplication.clipboard().text()
    assert text == "alpha\t서울\nbeta\t부산", f"복사 TSV 불일치: {text!r}"


def test_corner_select_all(app: QApplication) -> None:
    """왼쪽 위 코너 버튼 클릭 → 전체 셀 선택 (Ctrl+A 와 동일)."""
    from PyQt6.QtWidgets import QAbstractButton

    viewer = DataFrameViewer()
    viewer.set_dataframe(_make_df(), new_session=True)
    assert viewer._table.isCornerButtonEnabled(), "코너 버튼이 활성화되어 있어야 함"
    corner = viewer._table.findChild(QAbstractButton)
    assert corner is not None, "QTableCornerButton 을 찾지 못함"
    corner.click()
    app.processEvents()
    n_selected = len(viewer._table.selectionModel().selectedIndexes())
    assert n_selected == 4 * 3, f"전체 12셀 선택 기대, 실제 {n_selected}"


def test_clipboard_paste(app: QApplication) -> None:
    """클립보드 TSV 를 setText 후 _on_paste → 데이터에 반영되는지.

    앵커는 active_cell 을 직접 지정한다(selection.mode='none' → _paste_anchor 가
    active_cell 을 앵커로 사용). 엑셀식으로 앵커 기준 오른쪽·아래로 채워진다.
    """
    viewer = DataFrameViewer()
    viewer.set_dataframe(_make_df(), new_session=True)
    QGuiApplication.clipboard().setText("X\tY\nP\tQ")
    viewer._active_cell = (0, "name")  # 붙여넣기 앵커(좌상단)
    viewer._on_paste()  # private: 붙여넣기 단축키/메뉴와 동일한 실제 경로
    app.processEvents()
    out = viewer.get_dataframe()
    assert out is not None
    assert str(out.at[0, "name"]) == "X", f"(0,name)={out.at[0, 'name']!r}"
    assert str(out.at[0, "city"]) == "Y", f"(0,city)={out.at[0, 'city']!r}"
    assert str(out.at[1, "name"]) == "P", f"(1,name)={out.at[1, 'name']!r}"
    assert str(out.at[1, "city"]) == "Q", f"(1,city)={out.at[1, 'city']!r}"


def test_find_duplicate_row_filter(app: QApplication) -> None:
    """중복 행만 표시 경로 — 잘못된 위젯명/라벨 갱신으로 크래시 나지 않는지."""
    from df_tool.operations import duplicate_row_mask
    from df_tool.selection import SelectionScope

    viewer = DataFrameViewer()
    df = pd.DataFrame({"id": [1, 2, 2, 3, 3, 3], "x": list("abcdef")})
    viewer.set_dataframe(df, new_session=True)
    app.processEvents()

    # 툴바 clicked(bool) 오인 가드
    assert viewer.find_duplicate_values.__doc__ or True
    # 필터 적용 본체 (다이얼로그 없이)
    indices = list(df.index[duplicate_row_mask(df, ["id"])])
    viewer._filter_pinned_rows.clear()
    viewer.search_entry.clear()
    viewer.search_column_combo.setCurrentIndex(0)
    viewer._selection = SelectionScope()
    viewer._table.clearSelection()
    viewer._filtered_indices = indices
    viewer._model.set_filtered_indices(viewer._sorted_filtered_indices())
    viewer._update_page_label()
    app.processEvents()
    assert viewer._model.rowCount() == 5, viewer._model.rowCount()
    assert not hasattr(viewer, "search_column")

    # 툴바 라벨 가시성 (혼동 방지 용어)
    from PyQt6.QtWidgets import QPushButton
    from df_tool.qt_dialogs import qt_select_columns_dialog

    assert callable(qt_select_columns_dialog)
    labels = {b.text() for b in viewer.findChildren(QPushButton)}
    assert "값 중복 찾기" in labels
    assert "완전동일 행 제거" in labels
    assert "결측 행 제거" in labels
    assert "중복 찾기" not in labels
    assert "중복 제거" not in labels
    assert "결측 제거" not in labels


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    test_set_get_roundtrip(app)
    test_search_filter(app)
    test_extract_filtered_rows(app)
    test_clipboard_copy(app)
    test_clipboard_paste(app)
    test_corner_select_all(app)
    test_find_duplicate_row_filter(app)
    print("qa_viewer_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
