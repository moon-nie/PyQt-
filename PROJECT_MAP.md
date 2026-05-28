# Gridloom — 프로젝트 파일 지도

> **목적:** 파일이 많아도 「어디를 고치면 되는지」 바로 찾기  
> **PyQt** (`gridloom.pyw`) 기준 · v0.7.1

| 함께 볼 문서 | 대상 |
|--------------|------|
| [README.md](README.md) | 문서 인덱스 |
| [LEARNING_GUIDE.md](LEARNING_GUIDE.md) | 코드 공부 순서 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 기능 추가 |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | 작성 규칙 |

---

## 1. 전체 트리

```
Gridloom/
├── gridloom.pyw              ★ PyQt 엔트리
├── requirements.txt
├── README.md · CHANGELOG.md · *.md (문서)
├── sample_data.csv
│
├── scripts/
│   ├── run_all_qa.py         전체 QA
│   ├── grid_smoke.py         GridModel·헤더 smoke
│   ├── qa_operations_smoke.py
│   └── qa_loader_smoke.py
│
└── df_tool/
    ├── __init__.py           __version__
    ├── branding.py           APP_NAME, 설정 경로
    │
    ├── qt_app.py             ★ PyQt MainWindow
    ├── qt_viewer.py          ★ 표 Facade
    ├── qt_viewer_ops.py      구조 변경 + PyQt 다이얼로그
    ├── qt_dialogs.py         PyQt 공통 다이얼로그 (저장·확인·도움말)
    ├── qt_data_dialogs.py    VLOOKUP·조인·병합·그룹 요약
    ├── qt_design_settings.py PyQt 디자인 설정
    ├── qt_panels.py          Info / Code / ActivityLog
    ├── qt_theme.py           app stylesheet
    │
    ├── grid/                 QTableView 엔진 (model, view, header, …)
    ├── operations.py         ★ pandas SSOT
    ├── loader.py             load_file / save_file
    ├── selection.py          SelectionScope
    ├── theme.py              COLORS, theme.json
    ├── performance.py        넓은 표 모드 임계값
    └── help_content.py       사용법 텍스트
```

---

## 2. 실행 엔드포인트

```
[사용자] gridloom.pyw
            │
            ▼
    gridloom.pyw :: main()
            │
            ▼
    qt_app.MainWindow
            ├── QApplication + theme
            ├── _build_layout()
            ├── DataFrameViewer
            └── show()
```

| 파일 | 진입 | 비고 |
|------|------|------|
| `gridloom.pyw` | `main()` | 유일한 실행 엔트리 |
| `df_tool/qt_app.py` | `MainWindow` | PyQt 메인 |

---

## 3. 화면 ↔ 코드 (PyQt)

```
┌─ qt_app.MainWindow ──────────────────────────────────────────────┐
│  toolbar: [열기][저장][시트][도움말▾]                              │
│  nav: [메인] [작업 로그]                                          │
│  ┌─ qt_viewer.DataFrameViewer ────────┬─ qt_panels ────────────┐ │
│  │  검색·툴바 (VLOOKUP·조인·…)         │ InfoPanel              │ │
│  │  grid.GridView + GridModel          │ CodePanel              │ │
│  └─────────────────────────────────────┴────────────────────────┘ │
│  status bar                                                       │
└───────────────────────────────────────────────────────────────────┘
```

---

## 4. 데이터 흐름

```
load_file (loader.py)
    → MainWindow._apply_dataframe
    → viewer.set_dataframe
    → GridModel._sync_from_dataframe

사용자 편집/메뉴
    → operations.* (또는 viewer 내부)
    → viewer._apply_df(restructure=?)
    → on_change → MainWindow (undo stack)

save_file (loader.py) ← viewer.get_dataframe()
```

---

## 5. 파일별 상세

### 5-1. PyQt UI

| 파일 | 주요 클래스/함수 | 수정 시점 |
|------|------------------|-----------|
| `qt_app.py` | `MainWindow`, `open_file`, `_apply_dataframe`, `refresh_theme` | 파일·undo·전역 메뉴 |
| `qt_viewer.py` | `DataFrameViewer`, `_apply_df`, 우클릭·단축키 | 표 UX·검색·복붙 |
| `qt_viewer_ops.py` | `insert_*_with_dialog`, `delete_*_with_dialog` | 행/열 구조 + 입력창 |
| `qt_dialogs.py` | `qt_confirm`, `QtHelpDialog`, `QtSaveAsDialog` | 공통 팝업 |
| `qt_data_dialogs.py` | `qt_vlookup_dialog`, `qt_merge_dialog`, … | 데이터 처리 팝업 |
| `qt_design_settings.py` | `show_design_settings_dialog`, `THEME_GROUPS` | 색상 설정 UI |
| `qt_panels.py` | `InfoPanel`, `CodePanel`, `ActivityLogPanel` | 사이드바 |
| `qt_theme.py` | `app_stylesheet`, `card_frame_style` | 전역 스타일 |

### 5-2. grid/

| 파일 | 역할 |
|------|------|
| `model.py` | DataFrame ↔ Qt 인덱스, `setData`, `replace_dataframe` |
| `view.py` | QTableView 설정, 키보드 포커스 |
| `header.py` | 열 드래그 재정렬, 리사이즈 구역, 헤더 우클릭 |
| `delegate.py` | 격자선, 활성 셀 테두리 |
| `selection.py` | QItemSelection ↔ `SelectionScope` |
| `state.py` | 정렬·검색 상태 |
| `format.py` | 넓은 표 모드 축약 표시 |

### 5-3. 데이터·공통

| 파일 | 역할 |
|------|------|
| `operations.py` | 모든 pandas 변환 (UI import 없음) |
| `loader.py` | CSV/Excel/Parquet 등 I/O, 시트 |
| `selection.py` | `SelectionScope` dataclass |
| `theme.py` | `COLORS`, `load_theme_config`, `save_theme_config` |
| `performance.py` | `is_heavy_dataframe`, 열 윈도우 |
| `help_content.py` | `HELP_TEXT` (도움말 > 사용법) |

### 5-4. (삭제됨) Tk 레거시

v0.7.1에서 `app.py`, `viewer.py`, `dialogs.py`, `gridloom_tk.pyw` 등 Tk 스택 전부 제거.

---

## 6. operations.py 주요 함수

| 함수 | 용도 |
|------|------|
| `resolve_column_key`, `resolve_column_keys` | int/str 열명 |
| `insert_row`, `insert_column`, `delete_rows`, `delete_columns` | 구조 |
| `rename_column`, `duplicate_column` | 열 메타 |
| `reorder_columns` | 열 드래그 |
| `sort_dataframe`, `filter_rows` | 정렬·검색 |
| `find_replace` | Ctrl+F |
| `fill_column`, `fill_sequential` | 채우기 |
| `drop_duplicates`, `drop_na_rows` | 정리 |
| `merge_dataframes`, `concat_dataframes` | 조인·병합 |
| `vlookup`, `group_summary` | 고급 (Tk 다이얼로그 연동) |

---

## 7. qt_viewer ↔ qt_app 콜백

| 콜백 | qt_app 핸들러 (대표) |
|------|----------------------|
| `on_change` | undo, info 갱신 |
| `on_drop_duplicates` | `_drop_duplicates` |
| `on_vlookup` | `_vlookup` (Tk dialog) |
| `on_merge` | `_merge` |
| `on_add_column` | `insert_column_with_dialog` 경유 |

---

## 8. 설정·데이터 경로

| 항목 | 경로 |
|------|------|
| 테마 | `~/.gridloom/theme.json` |
| 구 테마 | `~/.dataframe_tool/theme.json` (자동 인식) |
| 버전 | `df_tool/__init__.py` → `__version__` |

---

## 9. QA

```bash
set PYTHONPATH=.
python scripts/run_all_qa.py
```

| 스크립트 | 검증 |
|----------|------|
| `grid_smoke.py` | GridModel, 헤더, 열 재정렬 |
| `qa_operations_smoke.py` | operations |
| `qa_loader_smoke.py` | loader |

---

## 10. 「이걸 고치려면?」 빠른 표

| 하고 싶은 일 | 파일 |
|--------------|------|
| 새 pandas 변환 | `operations.py` |
| 표 우클릭/단축키 | `qt_viewer.py` |
| 행/열 추가 다이얼로그 | `qt_viewer_ops.py`, `qt_dialogs.py` |
| 열 드래그/헤더 | `grid/header.py` |
| 셀 그리기 | `grid/delegate.py` |
| 파일 열기/저장 | `loader.py`, `qt_app.py` |
| 색상/테마 | `theme.py`, `qt_design_settings.py` |
| 도움말 텍스트 | `help_content.py` |
| 사용자 문서 | 루트 `*.md` |
| VLOOKUP UI | `qt_data_dialogs.py` |
| 조인·병합·그룹 | `qt_data_dialogs.py` |
