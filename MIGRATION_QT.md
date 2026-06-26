# PyQt 표 엔진 마이그레이션 기록 (아카이브)

> **현 상태:** v0.7.1 이후 Gridloom은 **PyQt6 단일 엔트리(`gridloom.pyw`)만 유지**합니다.
> 이 문서는 Tk → PyQt 전환 과정을 남긴 **역사 기록**입니다.  
> `gridloom_tk.pyw`, `viewer.py`, `app.py`, `dialogs.py`, `tk_bridge.py` 같은 Tk 레거시 파일은 현재 저장소에 없습니다.

---

## 1. 왜 바꿨는가

| 항목 | 과거 Tk Treeview 방식 | 현재 PyQt `df_tool/grid/` |
|------|----------------|----------------------|
| 렌더링 | Treeview + Frame 오버레이(격자·하이라이트) | QTableView viewport 가상화 |
| 스크롤 | 매번 Frame create/destroy | Qt 내장 가상화 |
| 편집 | Entry 오버레이 | `QAbstractTableModel.setData` |
| 대용량 | 오버레이 스로틀·풀링으로 완화 | Mantra급 체감 속도 목표 |

**원칙:** `operations.py`는 SSOT 유지, `SelectionScope`와 `qt_viewer.py` public API는 최대한 안정적으로 유지.

---

## 2. 실행 방법

```bash
pip install -r requirements.txt   # PyQt6>=6.6.0 추가됨

python gridloom.pyw               # PyQt6 (기본)
```

---

## 3. 새 파일

| 경로 | 역할 |
|------|------|
| `df_tool/grid/model.py` | `GridModel` — pandas ↔ `QAbstractTableModel`, row_map·col_map·정렬·열 윈도우 |
| `df_tool/grid/view.py` | `GridView` — `QTableView` 래퍼, 테마 |
| `df_tool/grid/delegate.py` | `GridCellDelegate` — 격자선·활성 셀 테두리 paint (Frame 0개) |
| `df_tool/grid/selection.py` | `SelectionController` — Qt 선택 ↔ `SelectionScope` |
| `df_tool/grid/state.py` | `ViewState` — 검색·정렬 상태 dataclass |
| `df_tool/grid/format.py` | 셀 표시 문자열 포맷 |
| `df_tool/selection.py` | `SelectionScope` — Tk/Qt 공용 (viewer에서 분리) |
| `df_tool/qt_viewer.py` | `DataFrameViewer` PyQt Facade |
| `df_tool/qt_app.py` | `MainWindow` PyQt — 파일 열기·저장·사이드바·작업 로그 |
| `df_tool/qt_panels.py` | 정보·코드·작업 로그 Qt 패널 |
| `df_tool/qt_dialogs.py` | PyQt 공통 다이얼로그, `QtHelpDialog` |
| `df_tool/qt_design_settings.py` | PyQt 디자인 설정 |
| `scripts/grid_smoke.py` | GridModel·Qt viewer headless smoke |

---

## 4. 수정된 파일

| 경로 | 변경 내용 |
|------|-----------|
| `gridloom.pyw` | `df_tool.app` → `df_tool.qt_app.MainWindow` |
| `df_tool/__init__.py` | 버전 `0.6.0` |
| `requirements.txt` | `PyQt6>=6.6.0` 추가 |
| `scripts/run_all_qa.py` | `grid_smoke.py` 포함 |

**변경 없음 (의도적):** `df_tool/operations.py`, `df_tool/loader.py` — 데이터 로직 SSOT.

---

## 5. 아키텍처

```
gridloom.pyw
    └── df_tool/qt_app.py (MainWindow)
            ├── df_tool/qt_viewer.py (DataFrameViewer)
            │       ├── df_tool/grid/model.py   (GridModel)
            │       ├── df_tool/grid/view.py    (GridView)
            │       ├── df_tool/grid/delegate.py
            │       └── df_tool/grid/selection.py
            ├── df_tool/qt_panels.py (Info / Code / ActivityLog)
            ├── df_tool/qt_dialogs.py, qt_design_settings.py
            ├── df_tool/loader.py, operations.py
            └── df_tool/qt_data_dialogs.py (VLOOKUP·조인·병합·그룹 등)
```

---

## 6. DataFrameViewer API 호환

PyQt `DataFrameViewer`(`qt_viewer.py`)가 표 표시·선택·단축키의 Facade 역할을 합니다.

| 메서드 | 용도 |
|--------|------|
| `set_dataframe(df, reset_sort, copy, new_session)` | 표 갱신 |
| `get_selection()` | `SelectionScope` |
| `get_dataframe()` | 복사본 반환 |
| `prepare_for_new_dataset()` | 파일 전환 전 정리 |
| `insert_row_above/below_selection()` | 행 삽입 |
| `insert_column_left/right_selection()` | 열 삽입 |
| `delete_selected_rows()` | 행 삭제 |
| `set_restore_available(available, callback)` | 그룹 요약 복원 |
| `apply_theme()` | COLORS 반영 |

콜백: `on_change`, `on_info_refresh`, `on_action`, `on_action_error`, 데이터 메뉴 hooks.

---

## 7. Tk → Qt 차이 (사용자 체감)

- **속도:** 스크롤·대용량 표에서 PyQt가 훨씬 빠름
- **격자선:** Delegate paint (설정 `cell_grid` 색상)
- **다이얼로그:** 확인·행/열 추가·찾기/바꾸기·도움말·VLOOKUP·조인·병합·그룹 모두 **PyQt** (`qt_dialogs.py`, `qt_data_dialogs.py`)
- **디자인 설정:** PyQt `qt_design_settings.py` — `theme.json` 저장 후 Qt stylesheet 갱신
- **토스트:** PyQt는 실패·경고만 `QMessageBox`, 성공은 작업 로그만 (v0.5.3 정책 유지)

---

## 8. 테스트

```bash
cd c:\Users\siic\Desktop\0519
$env:PYTHONPATH = "."
python scripts/run_all_qa.py
```

- `grid_smoke.py` — int 열명(0,1,2) HTML xls 케이스 포함 GridModel 검증
- `qa_viewer_smoke.py` — 검색 필터·클립보드 복사/붙여넣기 검증
- `qa_mainwindow_smoke.py` — 로드·undo·비동기 결측 채우기 검증

---

## 9. 후속 작업

### 완료 (v0.6.1)
- 복사·붙여넣기 (Ctrl+C/V, Excel 탭 구분)
- 열/행 헤더 클릭 전체 선택
- PyQt 저장 다이얼로그 (`QtSaveAsDialog`)
- 셀 편집 → 표 즉시 반영 (`GridModel.replace_dataframe`)

### 완료 (v0.6.2)
- 열/행 추가·삭제 `restructure=True` 동기화
- 뷰어 액션 툴바, 우클릭 메뉴 대부분

### 완료 (v0.7.0)
- 열 헤더 우클릭·열 선택 후 셀 우클릭 (열 메뉴)
- 열 드래그 재정렬 + drop 라인 + 리사이즈/드래그 분리
- Ctrl+F 찾기/바꾸기 PyQt
- `QtHelpDialog` 도움말·가이드 문서
- PyQt 디자인 설정 (`qt_design_settings.py`)
- 개발 문서 전면 재작성 (`LEARNING_GUIDE`, `CODING_STANDARDS` 등)

### 현재 상태
- Tk 레거시 스택은 제거 완료.
- 남은 개선·리팩토링 항목은 [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)를 기준으로 관리.

---

## 10. 롤백

Tk 엔트리포인트는 현재 저장소에 없으므로 `gridloom_tk.pyw`로 롤백할 수 없습니다.
문제가 생기면 `CHANGELOG.md`에서 안정 버전을 확인하고, 해당 커밋/릴리스로 되돌리는 방식으로 대응합니다.
