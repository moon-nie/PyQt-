# Gridloom — 기능 추가 가이드 (개발)

> **PyQt 기본 실행** (`gridloom.pyw`) 기준.  
> 코드 공부 순서: [LEARNING_GUIDE.md](LEARNING_GUIDE.md) · 규칙: [CODING_STANDARDS.md](CODING_STANDARDS.md) · 파일 지도: [PROJECT_MAP.md](PROJECT_MAP.md)

---

## 1. 프로젝트 구조 (PyQt)

```
Gridloom/
├── gridloom.pyw              ★ PyQt 실행
├── README.md                 문서 인덱스
│
└── df_tool/
    ├── qt_app.py             ★ 메인 창 (파일·undo·사이드바)
    ├── qt_viewer.py          ★ 표 Facade (메뉴·단축키·선택)
    ├── qt_viewer_ops.py      행/열 구조 변경 + PyQt 다이얼로그
    ├── qt_dialogs.py         공통 PyQt 팝업
    ├── qt_design_settings.py 디자인 설정 (PyQt)
    ├── qt_panels.py          정보·코드·작업 로그
    ├── qt_theme.py           stylesheet
    │
    ├── grid/                 QTableView 엔진
    │   ├── model.py          GridModel
    │   ├── view.py           GridView
    │   ├── header.py         헤더 드래그·우클릭
    │   ├── delegate.py       격자·활성 셀 paint
    │   └── selection.py      SelectionController
    │
    ├── operations.py         ★ pandas SSOT (UI import 금지)
    ├── window_state.py       창 위치·크기 (window.json)
    ├── crawl.py              정적 HTML CSS selector 크롤링
    ├── loader.py             파일 I/O
    ├── selection.py          SelectionScope
    ├── qt_data_dialogs.py    VLOOKUP·조인·병합·결측채우기·그룹
    ├── qt_analysis_panel.py  EDA 분석 탭 UI
    ├── qt_crawl_panel.py     크롤링 탭 UI
    ├── qt_analysis_worker.py 분석 백그라운드 QThread
    ├── analysis.py           EDA 통계·차트 (PyQt 없음)
    ├── chart_style.py        차트 스타일 load/save
    ├── eda_report.py         HTML 리포트 (PyQt 없음)
    ├── qt_chart_style_dialog.py
    └── analysis_deps.py      분석 패키지 누락 검사
```

### 역할 비유

| 파일 | 역할 |
|------|------|
| `qt_app.py` | 홀 매니저 — 파일 열기·저장·undo·패널·창 기하 |
| `qt_viewer.py` | 테이블 — 표시·선택·우클릭·단축키·검색/결과 추출 |
| `operations.py` | 주방 — pandas 변환만 (`extract_rows` 등) |
| `window_state.py` | 창 위치·크기 JSON 저장/복원 (PyQt 없음) |
| `crawl.py` | 정적 HTML 크롤링 (PyQt 없음) |
| `qt_crawl_panel.py` | 크롤링 탭 UI |
| `qt_dialogs.py` | PyQt 공통 팝업 (확인·저장·도움말·열 병합/분리 등 공통 폼) |
| `qt_data_dialogs.py` | VLOOKUP·조인·병합·결측채우기·그룹 팝업 |
| `grid/` | 표 엔진 — Qt 모델·뷰·헤더 |

---

## 2. 실행 흐름

```
gridloom.pyw
    └── qt_app.MainWindow
            ├── DataFrameViewer (qt_viewer.py)
            │       └── grid/ (GridModel, GridView, …)
            ├── InfoPanel / CodePanel / ActivityLogPanel
            ├── loader.load_file / save_file
            └── operations.* (데이터 변환)
```

---

## 2-1. 분석 탭 (EDA)

| 파일 | 역할 |
|------|------|
| `analysis.py` | 통계·차트 추천·상관·이상치 요약 (순수 pandas/numpy) |
| `qt_analysis_panel.py` | 개요·단·이·다변량·결측·이상치 UI |
| `qt_analysis_worker.py` | KNN·이상치 등 무거운 작업을 메인 스레드 밖에서 실행 |
| `analysis_deps.py` | matplotlib/sklearn/scipy 설치 여부 |
| `chart_style.py` | 차트 색·글자·격자 설정 (`~/.gridloom/chart_style.json`) |
| `eda_report.py` | `build_eda_html(df)` — HTML 리포트 문자열 |

- 가공 중 데이터 변경 시 `qt_app.py`는 `refresh_light()`만 호출하고, 분석 페이지일 때만 `refresh(charts=True)` 합니다.
- 차트 색 변경은 `ChartStyle` + `MplCanvas.style_axes` 경유. 리포트는 `eda_report.py`에 pandas만 사용.
- 새 분석 연산은 `operations.py`에 두고, UI는 `qt_analysis_panel.py`에서 `run_analysis_task`로 호출합니다.

---

## 3. 기능 유형별 추가 방법

### 유형 A — 데이터만 바꾸는 기능 (버튼·메뉴)

**예:** 중복 제거, 결측 행 제거, 정렬

1. `operations.py`에 함수 추가
2. `qt_app.py`에서 viewer 콜백 연결 (`on_drop_duplicates` 등)
3. `viewer.set_dataframe(result)` 또는 `_apply_dataframe`

```python
# operations.py
def my_filter(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    # ...
    return result

# qt_app.py — 기존 패턴 참고
def _on_my_filter(self):
    if not self._require_data():
        return
    new_df = my_filter(self.viewer.get_dataframe())
    self._apply_dataframe(new_df, "my_filter 적용")
```

### 유형 B — 표 UI (우클릭·단축키)

**예:** 새 컨텍스트 메뉴 항목, Ctrl+키

1. `qt_viewer.py`에서 메뉴/shortcut 추가
2. `operations.py` 호출
3. `_apply_df(df, restructure=?)` 호출

```python
# qt_viewer.py — 열 메뉴 예시
action = menu.addAction("내 기능")
action.triggered.connect(lambda: self._my_column_action(col))

def _my_column_action(self, column):
    df = self.get_dataframe()
    new_df = my_operation(df, column)
    self._apply_df(new_df, restructure=False)
    self._notify_change("내 기능")
```

### 유형 C — 행/열 구조 변경 + 입력 다이얼로그

**예:** 열 추가, 행 추가, 이름 변경

1. `operations.py` — 순수 로직
2. `qt_viewer_ops.py` — `qt_*_dialog` + operations 호출
3. `qt_viewer.py` — 메뉴에서 `*_with_dialog` 호출

```python
# qt_viewer_ops.py 패턴
def my_thing_with_dialog(df, *, parent=None) -> pd.DataFrame | None:
    result = qt_my_dialog(parent)
    if not result:
        return None
    return my_thing(df, result)
```

### 유형 D — 새 PyQt 다이얼로그

1. `qt_dialogs.py`에 함수 또는 `QDialog` 클래스 추가
2. `COLORS` / `card_frame_style`로 기존 스타일 맞춤
3. `exec()` → 결과 반환 (`None` = 취소)

복잡한 다중 표 UI는 `qt_design_settings.py`처럼 **별도 `qt_*.py`** 파일도 가능.

### 유형 E — 메인 창 기능 (파일·설정)

**예:** 새 메뉴, 전역 단축키

- `qt_app.py`의 `_build_layout`, `_bind_shortcuts` 수정
- 데이터 변경 시 `_apply_dataframe`, `_log_action` 사용

### 유형 F — 표 엔진 저수준 (드물게)

**예:** 헤더 드래그, 셀 paint, 선택 동작

- `df_tool/grid/` 수정
- Facade(`qt_viewer.py`)에서 grid 이벤트 연결
- **grid/ 에 pandas import 금지** — DataFrame은 GridModel 경유

---

## 4. `_apply_df` vs `_apply_dataframe`

| 위치 | 함수 | 용도 |
|------|------|------|
| `qt_viewer.py` | `_apply_df` | viewer 내부 — GridModel 동기화 + `on_change` |
| `qt_app.py` | `_apply_dataframe` | undo push + viewer 갱신 + info 패널 |

viewer 밖(qt_app)에서 데이터를 바꿀 때는 **`_apply_dataframe`** 을 씁니다.

---

## 5. 다이얼로그 선택 가이드

| 상황 | 사용 |
|------|------|
| 예/아니오 | `qt_confirm(parent, title, message)` |
| 텍스트 입력 | `qt_*_dialog` 패턴 (`qt_add_column_dialog` 참고) |
| Markdown 문서 | `QtHelpDialog(parent, text, title=...)` |
| VLOOKUP·조인·병합·그룹 | `qt_data_dialogs.py` |
| 디자인 설정 | `show_design_settings_dialog` (`qt_design_settings.py`) |

메뉴 핸들러에서 다이얼로그를 열 때 크래시가 나면:

```python
QTimer.singleShot(0, lambda: self._open_my_dialog())
```

---

## 6. 테마·디자인

- 색상 키: `theme.COLORS` (예: `text`, `accent`, `cell_grid`)
- 저장: `~/.gridloom/theme.json`
- 변경 후: `MainWindow.refresh_theme()` → viewer·패널 `apply_theme()`

---

## 7. 문서·도움말 갱신

| 변경 | 수정 |
|------|------|
| 사용자 단축키·동작 | `help_content.py` |
| 개발 절차 | 이 파일 (`DEVELOPER_GUIDE.md`) |
| 새 파일 | `PROJECT_MAP.md` |
| 버전 릴리스 | `CHANGELOG.md`, `df_tool/__init__.py` |

앱 **도움말 ▾** 메뉴는 `qt_app.show_guide_doc("파일.md", "제목")`으로 연결됩니다.

---

## 8. QA 체크리스트

```powershell
$env:PYTHONPATH = "."
python scripts/run_all_qa.py
```

- [ ] 빈 데이터(`_require_data`)에서 안전하게 return?
- [ ] int 열명 (`0`, `1`) CSV에서 동작?
- [ ] undo (Ctrl+Z)에 쌓이는가?
- [ ] 필터/정렬 중에도 올바른 행/열 대상?
- [ ] PyQt 다이얼로그로 할 수 있는데 Tk를 새로 추가하지 않았는가?
- [ ] 변경 영역에 맞는 smoke(`qa_operations_smoke.py`, `qa_analysis_panel_smoke.py`, `qa_viewer_smoke.py`, `grid_smoke.py` 등)를 보강했는가?

---

## 9. (삭제됨) Tk 레거시

v0.7.1부터 PyQt만 유지합니다. `gridloom.pyw`가 유일한 실행 엔트리입니다.

---

## 10. 빠른 참조 — 자주 쓰는 API

### DataFrameViewer (`qt_viewer.py`)

| 메서드 | 설명 |
|--------|------|
| `set_dataframe(df, ...)` | 표 전체 갱신 |
| `get_dataframe()` | 복사본 |
| `get_selection()` | `SelectionScope` |
| `apply_theme()` | COLORS 반영 |

### operations (`operations.py`)

| 함수 | 설명 |
|------|------|
| `resolve_column_key(df, col)` | int/str 열명 해석 |
| `insert_row`, `insert_column` | 구조 변경 |
| `reorder_columns` | 열 순서 |
| `find_replace` | 찾기/바꾸기 |

자세한 목록은 `PROJECT_MAP.md` § operations 참고.
