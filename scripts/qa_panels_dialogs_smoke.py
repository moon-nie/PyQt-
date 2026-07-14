"""CodePanel·VLookup 다이얼로그 headless smoke (#13).

파일 선택·exec() 모달은 띄우지 않는다.
- CodePanel: editor 코드 주입 후 execute() → on_run 콜백
- QtVLookupDialog: 참조 DF를 주입한 뒤 preview/apply 경로 검증
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt6.QtWidgets import QApplication

from df_tool.qt_data_dialogs import QtVLookupDialog
from df_tool.qt_panels import CodePanel
from df_tool.qt_theme import monospace_qfont
from df_tool.ui_fonts import (
    html_body_font_css_stack,
    monospace_font_family,
    ui_font_css_stack,
)


def _test_ui_fonts() -> None:
    ui = ui_font_css_stack()
    mono = monospace_font_family()
    html = html_body_font_css_stack()
    assert "sans-serif" in ui and '"' in ui
    assert mono and isinstance(mono, str)
    assert "AppleGothic" in html and "Malgun Gothic" in html
    font = monospace_qfont(10)
    assert font.family() == mono
    assert font.pointSize() == 10


def _test_code_panel_execute(app: QApplication) -> None:
    source = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    captured: list[pd.DataFrame] = []
    notifies: list[tuple[bool, str]] = []

    panel = CodePanel(
        on_run=lambda df: captured.append(df.copy()),
        get_dataframe=lambda: source,
        on_notify=lambda ok, msg: notifies.append((ok, msg)),
    )
    panel.editor.setPlainText("df = df[df['a'] >= 2].copy()\ndf['c'] = df['a'] * 10")
    panel.execute()
    app.processEvents()

    assert panel.output_label.text() == "완료", f"성공 시 '완료' 기대, 실제 {panel.output_label.text()!r}"
    assert len(captured) == 1, "on_run이 한 번 호출돼야 함"
    out = captured[0]
    assert list(out.columns) == ["a", "b", "c"]
    assert out["a"].tolist() == [2, 3]
    assert out["c"].tolist() == [20, 30]

    # 오류 경로: df를 DataFrame이 아닌 값으로 덮어쓰기
    panel.editor.setPlainText("df = 123")
    panel.execute()
    app.processEvents()
    assert panel.output_label.text() == "df가 DataFrame이 아님"
    assert notifies and notifies[-1][0] is False


def _test_vlookup_dialog_preview_apply(app: QApplication) -> None:
    left = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    ref = pd.DataFrame({"id": [1, 2, 3], "score": [100, 200, 300]})

    dlg = QtVLookupDialog(None, [str(c) for c in left.columns], left)
    # 파일 다이얼로그 우회: 참조 DF·콤보 직접 주입
    dlg._ref_df = ref
    cols = [str(c) for c in ref.columns]
    dlg.right_key.clear()
    dlg.return_col.clear()
    dlg.right_key.addItems(cols)
    dlg.return_col.addItems(cols)
    dlg.left_key.setCurrentText("id")
    dlg.right_key.setCurrentText("id")
    dlg.return_col.setCurrentText("score")
    dlg.new_name.setText("score")
    dlg._update_preview()
    app.processEvents()

    assert "매칭" in dlg.stats_label.text(), f"미리보기 통계 문구 이상: {dlg.stats_label.text()!r}"
    assert dlg.preview_table.rowCount() >= 1, "미리보기 표에 행이 있어야 함"
    assert dlg.preview_table.columnCount() >= 1, "미리보기 표에 열이 있어야 함"

    dlg._apply()
    app.processEvents()
    assert dlg._result is not None, "적용 후 결과가 있어야 함"
    ref_df, left_key, right_key, return_col, new_name = dlg._result
    assert left_key == "id" and right_key == "id"
    assert return_col == "score" and new_name == "score"
    assert list(ref_df.columns) == ["id", "score"]


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    _test_ui_fonts()
    _test_code_panel_execute(app)
    _test_vlookup_dialog_preview_apply(app)
    print("qa_panels_dialogs_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
