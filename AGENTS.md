# AGENTS.md — AI 코딩 에이전트 운영 규칙

> **이 문서는 무엇인가요?**
> 이 저장소(**Gridloom**, PyQt6 데스크톱 표/EDA 도구)에서 작업하는 **AI 코딩 에이전트**가
> 프로젝트 담당자 없이도 **안전하게** 변경·검증·인수인계할 수 있도록 만든 운영 체크리스트입니다.
>
> 사람 기여자는 [CONTRIBUTING.md](CONTRIBUTING.md)를 먼저 보세요.
> 구조·규칙의 자세한 배경은 아래 문서로 연결됩니다(여기서 중복 설명하지 않음):
>
> | 문서 | 용도 |
> |------|------|
> | [ARCHITECTURE.md](ARCHITECTURE.md) | 3층 구조·의존성 규칙의 근거 |
> | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 기능 유형별 추가 위치 |
> | [CODING_STANDARDS.md](CODING_STANDARDS.md) | 작성 규칙·금지 사항·체크리스트 |
> | [PROJECT_MAP.md](PROJECT_MAP.md) | 파일별 위치 찾기 |
> | [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md) | 다음 할 일(기술 부채) 목록 |
> | [CONTRIBUTING.md](CONTRIBUTING.md) | 사람 기여 가이드 |
> | [LEARNING_GUIDE.md](LEARNING_GUIDE.md) | 코드 읽는 순서 |

---

## 0. 작업 시작 전 — 30초 점검

1. 이 문서와 [CODING_STANDARDS.md](CODING_STANDARDS.md)를 읽었는가?
2. 바꾸려는 대상이 **어느 층**에 속하는지 정했는가? (UI / 로직 / 표 엔진)
3. 환경 변수를 세팅했는가? (아래 **§5 환경** 참조)
4. 작업 대상을 [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)에서 골랐는가? (자율 작업 시, **§4** 참조)

---

## 1. 절대 깨면 안 되는 불변식 (Invariants)

아래는 매 변경마다 **반드시** 지켜야 하는 핵심 규칙입니다. 자세한 근거는 [ARCHITECTURE.md](ARCHITECTURE.md) §3, [CODING_STANDARDS.md](CODING_STANDARDS.md) §10 참고.

### 1-1. 계층(import) 규칙

| 모듈 | import 허용 | 절대 금지 |
|------|-------------|-----------|
| `df_tool/operations.py`, `ops_impute.py`, `ops_outliers.py` (로직) | pandas, numpy, sklearn, `selection.py` | ❌ `PyQt6`, `tkinter`, `qt_*` |
| `df_tool/analysis.py`, `eda_report.py`, `analysis_deps.py` (로직) | pandas, numpy, matplotlib, sklearn, scipy | ❌ `PyQt6`, `qt_*` |
| `df_tool/grid/` (표 엔진) | PyQt6, `selection.py` | ❌ `pandas` 직접 import (DataFrame은 `GridModel` 경유) |
| `df_tool/qt_*` (UI) | 거의 전부 | — |

> 기억법: **`operations.py`에 `import PyQt6`가 보이면 그건 버그입니다.**
> 반대로, **`grid/` 안에 `import pandas`가 보여도 버그입니다.**

### 1-2. 데이터 변경은 항상 operations → `_apply_dataframe`

- pandas 변환은 **`operations.py`**(또는 그 re-export인 `ops_impute.py`·`ops_outliers.py`)에서만 합니다.
- 입력 `df`를 직접 수정하지 말고 **항상 `.copy()` 후 새 DataFrame을 반환**합니다.
- 화면 반영은 정해진 경로로만:
  - viewer 내부: `qt_viewer.py`의 `_apply_df(df, restructure=...)`
  - 메인 창(`qt_app.py`): `_apply_dataframe(df, label)` — **undo 스택 push**가 여기서 일어납니다.
- 빈 데이터에서 동작하지 않도록 `_require_data()` 가드를 둡니다.
- 자세한 흐름: [ARCHITECTURE.md](ARCHITECTURE.md) §4, [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) §3·§4.

### 1-3. 문구(메시지) SSOT는 `analysis_deps.py`

- "scikit-learn이 필요합니다 / `pip install -r requirements.txt`" 류의 **설치·의존성 안내 문구**는
  **`df_tool/analysis_deps.py` 한 곳**에서만 생성합니다.
  - 표준 함수: `feature_requirement_message(module, *, feature=None, inline=False)`
  - 상수: `INSTALL_HINT`, 변환: `package_label("sklearn") → "scikit-learn"`
- UI 코드(`qt_analysis_panel.py`, `qt_data_dialogs.py` 등)에 같은 문구를 **하드코딩하지 마세요.**

### 1-4. 의존성 UI 게이트는 `qt_dependency.py`

- 선택적 패키지(sklearn·scipy 등) 유무에 따라 버튼/콤보를 활성·비활성하고 경고하는 로직은
  **`df_tool/qt_dependency.py`** 한 곳을 씁니다.
  - 위젯 활성/비활성+툴팁: `gate_widget(widget, available, module, feature=...)`
  - 콤보 항목 게이트: `gate_combo_item(combo, data_value, available, module, ...)`
  - 실행 전 가드: `require(parent, available, module, feature=...) -> bool`
- **계층 분리 유지**: 문구는 `analysis_deps`(PyQt 무관), 위젯 제어만 `qt_dependency`(PyQt 사용).

### 1-5. 비동기는 `qt_async.AsyncPoller`

- 파일 로드·KNN/MICE 결측 채우기 등 **무거운 백그라운드 작업**은
  `df_tool/qt_async.py`의 **`AsyncPoller`**(Future + QTimer 폴링)로 다룹니다.
  - `start(future, on_done)` / `cancel()` / `busy`
  - 콜백 안에서 stale 토큰 검사·로딩 표시·로그를 처리합니다.
  - 창 종료(`closeEvent`) 시 `cancel()`로 정리합니다.
- 분석 패널은 별도로 `QThreadPool`(`qt_analysis_worker.py`)을 유지합니다(현행 그대로 둘 것).

---

## 2. 표준 작업 루프 (매번 이 순서)

```
(1) 변경  →  (2) QA 통과  →  (3) 미러 동기화  →  (4) 버전/CHANGELOG  →  (5) 문서 갱신
```

### (1) 변경

- 해당 층·파일에 최소 diff로 수정합니다([CODING_STANDARDS.md](CODING_STANDARDS.md) §1).
- 기능 유형별 추가 위치는 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) §3을 따릅니다.

### (2) QA 통과 — **필수 게이트**

```powershell
$env:PYTHONPATH = "."
python scripts/run_all_qa.py
```

- `scripts/run_all_qa.py`는 아래 smoke 테스트를 순서대로 실행합니다(하나라도 실패하면 비정상 종료):
  `qa_operations_smoke.py` · `qa_analysis_smoke.py` · `qa_analysis_panel_smoke.py` ·
  `qa_mainwindow_smoke.py` · `qa_panels_dialogs_smoke.py` · `qa_loader_smoke.py` ·
  `qa_viewer_smoke.py` · `qa_crawl_smoke.py` · `grid_smoke.py`
- **QA를 통과하지 못한 변경은 "완료"가 아닙니다.**
- 새 로직을 추가했다면 가능한 한 관련 `scripts/qa_*_smoke.py`에 headless 검증을 보강합니다.

### (3) 미러 동기화 (`github_upload/`)

`github_upload/`는 GitHub 웹 업로드용 **수동 미러**입니다. 본체가 단일 출처(SSOT)이며, 코드/문서를 바꿨다면 미러를 맞춥니다.

```powershell
python scripts/sync_mirror.py --check    # 먼저 차이만 확인(드라이런, 파일 변경 없음)
python scripts/sync_mirror.py            # 실제 동기화
```

- 동기화 범위: 최상위 고정 파일(`gridloom.pyw`, `requirements.txt`, `sample_data.csv`, `LICENSE`, `.gitignore`),
  최상위 `*.md`, `df_tool/**/*.py`, `scripts/*.py`(단 `sync_mirror.py` 자신은 제외).
- **`github_upload/` 안의 파일을 직접 손으로 편집하지 마세요**(§3 금지 사항). 항상 본체를 고치고 이 스크립트로 반영합니다.

### (4) 버전 + CHANGELOG (필요 시)

- 사용자 동작·기능이 바뀌었으면 `df_tool/__init__.py`의 `__version__`(현재 `0.8.33`)과
  [CHANGELOG.md](CHANGELOG.md)를 갱신합니다.
- 순수 리팩토링(동작 보존)은 버전을 올리지 않아도 됩니다.

### (5) 문서 갱신

[CODING_STANDARDS.md](CODING_STANDARDS.md) §8 표를 기준으로:

| 변경 | 갱신할 문서 |
|------|-------------|
| 새 버튼·단축키·사용자 동작 | `help_content.py`, [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| 새 파일 | [PROJECT_MAP.md](PROJECT_MAP.md) |
| 구조·리팩토링 | [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)의 상태/완료 섹션 |
| 사용자 동작·릴리스 | [CHANGELOG.md](CHANGELOG.md) |

> 문서를 고쳤다면 (3) 미러 동기화를 다시 실행해 `*.md`도 미러에 반영합니다.

---

## 3. 금지 사항 (Do NOT)

- ❌ 요청 없는 **대규모 포맷·이름 변경**, 무관한 리팩토링(최소 diff 원칙 위반).
- ❌ `operations.py`(및 `ops_*`)·`analysis.py` 등 **로직 층에 `PyQt6`/`tkinter` import** 또는 **UI 문자열** 삽입.
- ❌ `grid/` 모듈에서 **`pandas` 직접 import**(DataFrame은 `GridModel` 경유).
- ❌ **`github_upload/` 직접 수동 편집** — 반드시 본체 변경 후 `scripts/sync_mirror.py`로 동기화.
- ❌ **의존성 안내 문구를 UI에 하드코딩** — `analysis_deps.feature_requirement_message` 사용.
- ❌ 데이터 변경을 `operations` 밖(예: UI 핸들러 안)에서 직접 pandas로 처리.
- ❌ QA 미통과 상태로 작업 종료.
- ❌ QHeaderView `paintEvent`에서 viewport에 중복 `QPainter` 생성(크래시).

---

## 4. "다음 할 일" 고르는 규칙 (자율 작업)

담당자 지시가 없을 때는 [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)의 **상태 보드**에서
**위험(Risk) 낮고 효과(Impact) 높은** 미완료 항목 **하나**를 고릅니다.

1. 보드(§2)에서 `⏳ 대기` / `🔄 진행 중` 중 ROI가 가장 좋은 1건 선택.
2. **작은 단위**로만 변경(동작 보존, behavior-preserving).
3. **§2의 표준 작업 루프**를 그대로 수행(특히 QA 게이트).
4. 백로그 문서의 상태/완료 섹션을 갱신.

> 한 번에 여러 항목을 갈아엎지 않습니다. "작고 안전한 increment"가 이 저장소의 원칙입니다.

---

## 5. 환경 (Windows PowerShell)

이 저장소의 표준 실행 환경은 **Windows PowerShell**입니다. 명령 실행 전에 항상 `PYTHONPATH`를 설정하세요.

```powershell
# 프로젝트 루트에서
$env:PYTHONPATH = "."

python gridloom.pyw                  # 앱 실행 (PyQt6)
python scripts/run_all_qa.py         # 전체 QA
python scripts/sync_mirror.py --check # 미러 차이 확인
```

- 엔트리포인트는 **`gridloom.pyw`** 하나입니다(Tk 레거시는 제거됨, [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) §9).
- `run_all_qa.py`는 내부적으로도 `PYTHONPATH`를 보강하지만, 개별 스크립트를 직접 실행할 때를 대비해 위 설정을 습관화합니다.
- 설치·실행 상세는 [SETUP_GUIDE.md](SETUP_GUIDE.md) 참고.

---

## 6. 한 화면 요약

1. **층을 지켜라** — 로직(operations/analysis)은 PyQt 모름, grid는 pandas 직접 import 금지.
2. **데이터는 operations → `_apply_dataframe`** (copy 후 반환, undo 보존).
3. **문구=`analysis_deps`, UI 게이트=`qt_dependency`, 비동기=`qt_async.AsyncPoller`**.
4. **루프**: 변경 → `run_all_qa.py` 통과 → `sync_mirror.py` → 버전/CHANGELOG → 문서.
5. **다음 일**은 [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)에서 위험↓·효과↑ 항목 1개.
6. **미러는 손으로 만지지 말 것**, 최소 diff 유지.
