# Gridloom — 코드 공부 가이드

> **처음 이 프로젝트를 여는 사람**을 위한 학습 로드맵입니다.  
> 기능을 직접 추가하려면 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md), 규칙은 [CODING_STANDARDS.md](CODING_STANDARDS.md)를 이어서 읽으세요.

---

## 0. 준비 지식

| 분야 | 최소 수준 | 이 프로젝트에서 쓰는 곳 |
|------|-----------|-------------------------|
| Python | 함수, 클래스, import | 전체 |
| pandas | `DataFrame`, 열 선택, `iloc` | `operations.py`, `loader.py` |
| GUI (PyQt6) | 위젯, 시그널/슬롯 개념 | `qt_app.py`, `grid/` |
| Git / 터미널 | `python`, `pip install` | 실행·QA |

PyQt6를 처음 본다면 [Qt for Python 공식 문서](https://doc.qt.io/qtforpython-6/)의 **QWidget**, **QTableView**, **QAbstractTableModel** 항목만 먼저 훑어도 충분합니다.

---

## 1. 큰 그림 (5분)

Gridloom은 **3층 구조**입니다.

```
사용자 클릭/단축키
    ↓
UI (qt_app, qt_viewer, grid)     ← 화면·입력·선택
    ↓
operations.py                    ← pandas로 실제 데이터 변경
    ↓
다시 UI에 반영 (_apply_df)
```

- **UI는 얇게**, **데이터 로직은 `operations.py`에만** — 이 한 문장이 프로젝트의 핵심입니다.
- 기본 실행은 **PyQt6** (`gridloom.pyw`). Tk 버전(`gridloom_tk.pyw`)은 레거시입니다.

---

## 2. 추천 읽기 순서

아래 순서대로 파일을 열어 **한 함수씩** 따라가 보세요.

### 1단계 — 실행과 진입점 (30분)

| 순서 | 파일 | 볼 것 |
|------|------|-------|
| 1 | `gridloom.pyw` | `main()` → `MainWindow` 생성 |
| 2 | `df_tool/qt_app.py` | `__init__`, `_build_layout`, `_apply_dataframe` |
| 3 | `df_tool/branding.py` | 앱 이름, 설정 경로 |

**연습:** 앱을 실행하고 `Ctrl+O`로 CSV를 연 뒤, `open_file` 함수를 찾아 호출 흐름을 메모해 보세요.

### 2단계 — 데이터 로딩 (30분)

| 순서 | 파일 | 볼 것 |
|------|------|-------|
| 4 | `df_tool/loader.py` | `load_file`, `save_file`, 엑셀 시트 처리 |
| 5 | `df_tool/operations.py` (앞부분) | `resolve_column_key`, `insert_row` |

**연습:** `sample_data.csv`를 열었을 때 `MainWindow._apply_dataframe`까지 거치는 경로를 그려 보세요.

### 3단계 — 표 엔진 (1~2시간)

| 순서 | 파일 | 볼 것 |
|------|------|-------|
| 6 | `df_tool/selection.py` | `SelectionScope` — 셀/행/열 선택 표현 |
| 7 | `df_tool/grid/model.py` | `GridModel` — pandas ↔ Qt 모델 |
| 8 | `df_tool/grid/view.py` | `GridView` — QTableView 래퍼 |
| 9 | `df_tool/grid/delegate.py` | 격자선·활성 셀 그리기 |
| 10 | `df_tool/grid/header.py` | 헤더 클릭, 드래그, 우클릭 |
| 11 | `df_tool/grid/selection.py` | Qt 선택 ↔ `SelectionScope` |

**연습:** 셀을 더블클릭해 편집할 때 `setData` → `_commit_cell_edit` → `on_change` 순서를 추적하세요.

### 4단계 — Facade와 다이얼로그 (1시간)

| 순서 | 파일 | 볼 것 |
|------|------|-------|
| 12 | `df_tool/qt_viewer.py` | `DataFrameViewer` — 메뉴, 단축키, `_apply_df` |
| 13 | `df_tool/qt_viewer_ops.py` | 행/열 추가·삭제 + PyQt 다이얼로그 |
| 14 | `df_tool/qt_data_dialogs.py` | VLOOKUP·조인·병합·그룹 PyQt 다이얼로그 |

**연습:** 열 헤더 우클릭 → 「열 삭제」를 눌렀을 때 호출되는 함수 이름을 적어 보세요.

### 5단계 — 부가 패널·테마 (선택)

| 파일 | 역할 |
|------|------|
| `df_tool/qt_panels.py` | 정보·코드·작업 로그 패널 |
| `df_tool/qt_theme.py` | 전역 stylesheet |
| `df_tool/theme.py` | `COLORS`, `theme.json` 로드 |
| `df_tool/qt_design_settings.py` | 디자인 설정 UI |

---

## 3. 핵심 개념 정리

### 3-1. `SelectionScope`

선택 상태를 **UI와 무관한** 공통 타입으로 표현합니다.

- `cells`, `rows`, `columns`, `active_cell`
- Tk viewer와 PyQt viewer가 같은 타입을 씁니다.

### 3-2. `GridModel`

`QAbstractTableModel` 구현체입니다.

- 내부에 `pandas.DataFrame` 보관
- `row_map` / `col_map` — 필터·정렬·열 윈도우 후 **화면 인덱스 ↔ 원본 인덱스** 매핑
- `replace_dataframe(df)` — 값만 바뀔 때
- `_sync_from_dataframe(df)` — 행·열 구조가 바뀔 때 (restructure)

### 3-3. `DataFrameViewer` (Facade)

Tk 시절 `viewer.py`와 **같은 public API**를 PyQt로 제공합니다.

- `set_dataframe`, `get_dataframe`, `get_selection`
- 우클릭 메뉴, 단축키, 검색 필터는 여기서 연결
- 실제 pandas 호출은 `operations.py` 또는 `qt_viewer_ops.py`

### 3-4. `_apply_df` / undo

`qt_viewer.py`의 `_apply_df(df, restructure=False)`:

| `restructure` | 의미 | GridModel 갱신 |
|---------------|------|----------------|
| `False` | 셀 값·필터 결과만 변경 | `replace_dataframe` |
| `True` | 행/열 추가·삭제·순서 변경 | 전체 `_sync_model` |

변경 후 `on_change` → `MainWindow._apply_dataframe` → undo 스택에 push.

### 3-5. PyQt vs Tk 다이얼로그

| 방식 | 언제 |
|------|------|
| `qt_dialogs.py` | **신규·단순** 팝업 (확인, 입력, 도움말) |
| `qt_data_dialogs.py` | VLOOKUP, 조인, 병합, 그룹 요약 |

---

## 4. 사용자 동작 → 코드 추적 (실습)

### 예시 A: Ctrl+C 복사

```
키 이벤트 (qt_viewer.py)
  → _on_copy()
  → SelectionScope 확인
  → 클립보드에 TSV 형식 기록
```

### 예시 B: 열 드래그로 순서 변경

```
GridHorizontalHeader (grid/header.py)
  → mouseMove / drop
  → qt_viewer._reorder_columns(from, to)
  → operations.reorder_columns(df, ...)
  → _apply_df(..., restructure=True)
```

### 예시 C: 중복 제거 버튼

```
qt_viewer 툴바 버튼
  → on_drop_duplicates (qt_app에 연결)
  → operations.drop_duplicates
  → viewer.set_dataframe / _apply_dataframe
```

---

## 5. 테스트로 확인하기

```bash
cd c:\Users\siic\Desktop\0519
set PYTHONPATH=.
python scripts/grid_smoke.py
python scripts/run_all_qa.py
```

- `grid_smoke.py` — GUI 없이 GridModel·헤더·열 재정렬 검증
- `run_all_qa.py` — operations, loader, viewer 회귀 전체

코드를 읽은 뒤 **테스트 파일**을 보면 「기대 동작」을 빠르게 확인할 수 있습니다.

---

## 6. 자주 헷갈리는 것

| 질문 | 답 |
|------|-----|
| `viewer.py` vs `qt_viewer.py`? | 기본은 `qt_viewer.py`. `viewer.py`는 Tk 레거시 |
| `app.py` vs `qt_app.py`? | 기본은 `qt_app.py` |
| 열 이름이 `0`, `1`인데? | `resolve_column_key`가 int/str 모두 처리 |
| 표가 안 바뀌어요 | `restructure=True` 필요한지 확인 |
| 다이얼로그 후 크래시 | 메뉴에서 바로 열 때 `QTimer.singleShot(0, ...)` 패턴 |

---

## 7. 다음 단계

1. [PROJECT_MAP.md](PROJECT_MAP.md) — 파일 전체 지도
2. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — 작은 기능 하나 추가해 보기
3. [CODING_STANDARDS.md](CODING_STANDARDS.md) — PR 전 체크리스트
4. [MIGRATION_QT.md](MIGRATION_QT.md) — Tk에서 무엇이 바뀌었는지

---

## 8. 학습용 미니 과제 (선택)

| 난이도 | 과제 |
|--------|------|
| ★ | `operations.py`에 `count_non_null(df, col)` 추가 후 info 패널에 표시 |
| ★★ | 표 우클릭 메뉴에 「선택 열 대문자 변환」 추가 |
| ★★★ | `qt_dialogs.py`로 간단한 「열 통계」 팝업 (min/max/mean) |

과제를 할 때는 **operations → qt_viewer_ops(필요 시) → qt_viewer 메뉴/단축키 → QA** 순서를 지키세요.
