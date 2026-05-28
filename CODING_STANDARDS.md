# Gridloom — 코드 작성 규칙

> PyQt (`gridloom.pyw`) 기준.

---

## 1. 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **SSOT for data** | pandas 변환은 `operations.py` 한곳 |
| **얇은 UI** | `qt_app.py` / `qt_viewer.py`에 긴 pandas 코드 금지 |
| **PyQt 다이얼로그 우선** | 새 팝업은 `qt_dialogs.py` 또는 전용 `qt_*.py` |
| **최소 diff** | 요청과 무관한 리팩터링·포맷 변경 금지 |
| **기존 패턴 따르기** | 새 파일보다 기존 함수·클래스 확장 |

---

## 2. 파일 배치 규칙

| 종류 | 넣을 위치 | 예 |
|------|-----------|-----|
| 데이터 변환 | `df_tool/operations.py` | `drop_duplicates`, `find_replace` |
| 표 표시·입력 | `df_tool/grid/` | `GridModel`, `GridHeaderView` |
| 표 Facade (메뉴·선택·단축키) | `df_tool/qt_viewer.py` | `_on_paste`, `_popup_column_menu` |
| 구조 변경 + 다이얼로그 | `df_tool/qt_viewer_ops.py` | `insert_column_with_dialog` |
| PyQt 팝업 | `df_tool/qt_dialogs.py` | `qt_find_replace_dialog` |
| 복잡 PyQt 전용 UI | `df_tool/qt_*.py` | `qt_data_dialogs.py`, `qt_design_settings.py` |
| 메인 창·파일·undo | `df_tool/qt_app.py` | `open_file`, `_apply_dataframe` |
| 공통 타입 | `df_tool/selection.py` | `SelectionScope` |
| 스타일 | `df_tool/qt_theme.py` + `theme.py` | `COLORS`, `app_stylesheet()` |

---

## 3. 네이밍

| 대상 | 규칙 | 예 |
|------|------|-----|
| operations 함수 | `snake_case`, 동사 시작 | `insert_row`, `reorder_columns` |
| Qt 클래스 | `PascalCase`, `Qt` 접두사(다이얼로그) | `QtHelpDialog`, `GridModel` |
| private 메서드 | `_leading_underscore` | `_apply_df`, `_sync_model` |
| 콜백 | `on_*` | `on_change`, `on_action` |
| 상수 | `UPPER_SNAKE` | `COL_DRAG_THRESHOLD` |

---

## 4. `operations.py` 작성 규칙

```python
def my_operation(df: pd.DataFrame, column: str) -> pd.DataFrame:
    result = df.copy()          # 원본 변경 금지
    key = resolve_column_key(result, column)
    if key is None:
        return result           # 또는 ValueError
    # ... 변환 ...
    return result
```

- **입력 `df`를 직접 수정하지 않음** — 항상 `.copy()` 후 반환
- 열 이름은 `resolve_column_key` / `resolve_column_keys` 사용 (int 열명 `0`, `1` 대응)
- UI 문자열·메시지는 operations에 넣지 않음

---

## 5. PyQt UI 작성 규칙

### 5-1. DataFrame 반영

| 변경 종류 | 호출 |
|-----------|------|
| 셀 값만 변경 | `_apply_df(df, restructure=False)` → `replace_dataframe` |
| 행·열 추가/삭제·순서 변경 | `_apply_df(df, restructure=True)` → `_sync_model` |

### 5-2. 다이얼로그

```python
# ✅ PyQt (권장)
result = qt_confirm(self, "제목", "메시지")
QtHelpDialog(self, text).exec()
```

메뉴에서 다이얼로그를 열 때는 `QTimer.singleShot(0, ...)`로 **메뉴가 닫힌 뒤** 실행 (필요 시).

### 5-3. 스타일

- 색상은 `theme.COLORS` 참조 — 하드코딩 `#fff` 지양
- 전역 스타일: `qt_theme.app_stylesheet()`
- 위젯 개별: `setStyleSheet(f"... {COLORS['text']} ...")`
- 테마 변경 후: `viewer.apply_theme()`, `info_panel.apply_theme()` 등 호출

---

## 6. 선택(Selection) 규칙

- 내부 표현: `SelectionScope` (`df_tool/selection.py`)
- Qt ↔ Scope 변환: `SelectionController` (`df_tool/grid/selection.py`)
- 열 선택 후 우클릭 → **열 메뉴** (행 메뉴 아님) — Tk와 동일 UX

---

## 7. 테스트

기능 추가·버그 수정 후:

```bash
python scripts/run_all_qa.py
```

가능하면 `scripts/grid_smoke.py`에 headless 검증 추가 (GUI 조작 없이).

---

## 8. 문서 갱신 체크리스트

| 변경 | 갱신할 문서 |
|------|-------------|
| 새 버튼·단축키 | `help_content.py`, `DEVELOPER_GUIDE.md` |
| 새 파일 | `PROJECT_MAP.md` |
| PyQt 전환 | `MIGRATION_QT.md`, `CHANGELOG.md` |
| 사용자 동작 변경 | `CHANGELOG.md` |

---

## 9. 커밋 전 자가 점검

- [ ] `operations.py`에 순수 로직만 있는가?
- [ ] `_apply_df` / `_notify_change`로 undo 스택에 쌓이는가?
- [ ] `_require_data()`로 빈 상태를 막았는가?
- [ ] int 열명·필터·정렬 후에도 동작하는가?
- [ ] `run_all_qa` 통과했는가?
- [ ] PyQt 다이얼로그를 Tk 대신 쓸 수 있는데 Tk를 쓰지 않았는가?

---

## 10. 금지 사항

- `operations.py`에서 `tkinter` / `PyQt6` import
- `grid/` 모듈에서 `pandas` 직접 import (GridModel 경유)
- QHeaderView `paintEvent`에서 viewport에 중복 `QPainter` (크래시)
- 요청 없는 대규모 포맷·이름 변경
