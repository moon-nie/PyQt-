"""MainWindow·데이터 다이얼로그 headless smoke.

리팩토링 안전망: GUI 조작 없이 메인 창의 데이터 수명주기(로드→적용→undo)와
결측 채우기 다이얼로그의 미리보기/의존성 게이트를 검증한다.

파일 다이얼로그·exec()는 띄우지 않는다(임시 CSV + 내부 메서드 직접 호출).
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
from PyQt6.QtWidgets import QApplication

from df_tool.analysis_deps import sklearn_available
from df_tool.loader import load_file
from df_tool.qt_app import MainWindow
from df_tool.qt_data_dialogs import QtFillNaDialog


def _make_csv(tmp: Path) -> Path:
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 5],
            "score": [10.0, None, 30.0, 40.0, None, 50.0],
            "city": ["서울", "부산", "서울", "대구", "부산", "부산"],
        }
    )
    path = tmp / "mw_smoke.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _test_mainwindow_lifecycle(tmp: Path) -> None:
    window = MainWindow()
    loaded = load_file(_make_csv(tmp))
    window._apply_loaded_data(loaded, new_file=True)

    base = window.viewer.get_dataframe()
    assert len(base) == 6, f"로드 행수 불일치: {len(base)}"
    assert window._data_token > 0

    token_before = window._data_token
    undo_before = len(window._undo_stack)

    # 데이터 변경: 첫 행 제거 → undo 스택·토큰 증가 확인 (결정적)
    trimmed = base.iloc[1:].reset_index(drop=True)
    window._apply_dataframe(trimmed, message="첫 행 제거(smoke)")
    assert window._data_token > token_before, "데이터 변경 후 토큰이 증가해야 함"
    assert len(window._undo_stack) == undo_before + 1, "undo 스택에 직전 상태가 쌓여야 함"
    assert len(window.viewer.get_dataframe()) == 5, "행 제거 결과(5행)가 반영돼야 함"

    # undo → 원래 6행 복원
    window.undo()
    assert len(window.viewer.get_dataframe()) == 6, "undo 후 원래 6행으로 복원돼야 함"

    # 페이지 전환이 예외 없이 동작
    window._show_page("analysis")
    window._show_page("main")
    window._sync_mode_badges()

    window.close()


def _test_fillna_dialog_preview(tmp: Path) -> None:
    df = pd.DataFrame({"score": [10.0, None, 30.0, None, 50.0]})
    dlg = QtFillNaDialog(None, df, "score")

    # 숫자 통계 방식(mean)은 항상 사용 가능 → 미리보기 표시 + 적용 버튼 활성
    mean_idx = dlg._method_codes.index("mean")
    dlg.method_combo.setCurrentIndex(mean_idx)
    dlg._update_preview()
    assert dlg.preview_label.text().strip(), "mean 미리보기 문구가 비어 있으면 안 됨"
    assert dlg._ok_btn.isEnabled(), "mean 방식은 적용 버튼이 활성이어야 함"

    # KNN은 scikit-learn 유무에 따라 적용 버튼 활성 상태가 갈린다
    if "knn" in dlg._method_codes:
        dlg.method_combo.setCurrentIndex(dlg._method_codes.index("knn"))
        dlg._update_preview()
        assert dlg._ok_btn.isEnabled() == sklearn_available(), (
            "KNN 적용 버튼 활성 상태가 scikit-learn 설치 여부와 일치해야 함"
        )
        if not sklearn_available():
            assert "scikit-learn" in dlg.preview_label.text(), "KNN 미설치 안내 문구 필요"

    dlg.close()


def _pump_until(app: QApplication, predicate, timeout_s: float = 5.0) -> bool:
    """이벤트 루프를 돌리며 predicate가 True가 되면 멈춘다(비동기 경로 검증용)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _test_async_load(app: QApplication, tmp: Path) -> None:
    window = MainWindow()
    window.load_path(_make_csv(tmp))
    ok = _pump_until(app, lambda: window._loaded is not None)
    assert ok, "비동기 파일 로드가 완료되지 않음"
    assert len(window.viewer.get_dataframe()) == 6, "로드된 데이터가 6행이어야 함"
    window.close()


def _test_async_fill(app: QApplication, tmp: Path) -> None:
    if not sklearn_available():
        return  # KNN 비동기 경로는 scikit-learn 필요
    window = MainWindow()
    window._apply_loaded_data(load_file(_make_csv(tmp)), new_file=True)
    window._fill_missing_in_column_async(
        window._loaded.dataframe.copy(deep=True),
        "score",
        "knn",
        n_neighbors=2,
        message="KNN(smoke)",
    )
    ok = _pump_until(app, lambda: int(window.viewer.get_dataframe()["score"].isna().sum()) == 0)
    assert ok, "KNN 비동기 적용 후 결측이 0이어야 함"
    window.close()


def main() -> int:
    app = QApplication(sys.argv)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _test_mainwindow_lifecycle(tmp)
        _test_fillna_dialog_preview(tmp)
        _test_async_load(app, tmp)
        _test_async_fill(app, tmp)
    print("qa_mainwindow_smoke: OK")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
