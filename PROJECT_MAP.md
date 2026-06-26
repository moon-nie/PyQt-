# Gridloom — 프로젝트 파일 지도

> **목적:** 파일이 많아도 어디를 고치면 되는지 바로 찾기  
> **PyQt** (`gridloom.pyw`) 기준 · v0.8.21

| 함께 볼 문서 | 대상 |
|--------------|------|
| [README.md](README.md) | 문서 인덱스 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 기여 가이드 (사람) |
| [AGENTS.md](AGENTS.md) | AI 에이전트 운영 규칙 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 아키텍처 한눈에 보기 (초심자) |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | 설치·실행 |
| [LEARNING_GUIDE.md](LEARNING_GUIDE.md) | 코드 공부 순서 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 기능 추가 |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | 코드 작성 규칙 |
| [MIGRATION_QT.md](MIGRATION_QT.md) | PyQt 전환 아카이브 |
| [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md) | 기술 부채 추적 |
| [CHANGELOG.md](CHANGELOG.md) | 변경 기록 |

---

## 1. 전체 트리

```text
Gridloom/
├── gridloom.pyw              PyQt 엔트리
├── requirements.txt          런타임 의존성
├── README.md · CHANGELOG.md  문서
├── sample_data.csv
│
├── scripts/
│   ├── run_all_qa.py         전체 QA
│   ├── qa_operations_smoke.py
│   ├── qa_analysis_smoke.py
│   ├── qa_analysis_panel_smoke.py
│   ├── qa_mainwindow_smoke.py
│   ├── qa_loader_smoke.py
│   ├── qa_viewer_smoke.py    표 Facade 검색·클립보드
│   ├── grid_smoke.py
│   ├── github_publish.py     GitHub API 업로드(선택)
│   └── sync_mirror.py        github_upload 미러 동기화(본체 전용, 미러에는 복사 안 됨)
│
└── df_tool/
    ├── __init__.py           __version__
    ├── branding.py           APP_NAME, 설정 경로
    ├── theme.py              COLORS, theme.json
    ├── qt_theme.py           공통 stylesheet
    │
    ├── qt_app.py             메인 창, 파일·undo·네비게이션
    ├── qt_viewer.py          표 Facade
    ├── qt_viewer_ops.py      행/열 구조 변경 + 팝업 연결
    ├── qt_dialogs.py         공통 PyQt 다이얼로그
    ├── qt_data_dialogs.py    VLOOKUP·조인·병합·결측채우기·그룹
    ├── qt_panels.py          정보·코드·작업 로그 패널
    ├── qt_design_settings.py 앱 색상 설정
    │
    ├── qt_analysis_panel.py  EDA 분석 탭 UI
    ├── qt_analysis_worker.py 백그라운드 분석 작업(QThreadPool)
    ├── qt_chart_style_dialog.py  차트 꾸미기 다이얼로그
    ├── analysis.py           EDA 통계·차트 추천·PCA
    ├── analysis_deps.py      matplotlib/sklearn/scipy 의존성 검사
    ├── chart_style.py        차트 색·레이아웃 설정 저장
    ├── eda_report.py         차트 포함 HTML EDA 리포트
    │
    ├── operations.py         pandas 변환 SSOT (impute·outlier는 re-export)
    ├── ops_impute.py         KNN·MICE 결측 대체 (sklearn)
    ├── ops_outliers.py       이상치 탐지 IQR·Z·IsolationForest
    ├── qt_dependency.py      의존성 UI 게이트(활성/비활성·경고)
    ├── qt_async.py           백그라운드 Future 폴링 래퍼(AsyncPoller)
    ├── loader.py             load_file / save_file
    ├── performance.py        대용량·넓은 표 임계값
    ├── help_content.py       앱 도움말 텍스트
    ├── selection.py          SelectionScope
    └── grid/
        ├── model.py          GridModel
        ├── view.py           GridView
        ├── header.py         헤더 드래그·우클릭
        ├── delegate.py       셀 paint
        ├── selection.py      SelectionController
        └── state.py          선택·상태 모델
```

---

## 2. 실행 흐름

```text
gridloom.pyw
  └── qt_app.MainWindow
        ├── DataFrameViewer (qt_viewer.py)
        │     └── grid/ (model, view, header, delegate)
        ├── InfoPanel / CodePanel / ActivityLogPanel
        ├── AnalysisPanel (qt_analysis_panel.py)
        ├── loader.load_file / save_file
        └── operations.* (데이터 변환)
```

---

## 3. 기능별 수정 위치

| 기능 | 우선 확인 파일 |
|------|----------------|
| 파일 열기·저장 | `loader.py`, `qt_app.py` |
| 표 표시·편집 | `qt_viewer.py`, `grid/model.py`, `grid/view.py` |
| 행/열 선택 | `grid/selection.py`, `grid/header.py`, `selection.py` |
| VLOOKUP·조인·병합 | `qt_data_dialogs.py`, `operations.py` |
| 결측 채우기(KNN/MICE) | `operations.py`, `qt_data_dialogs.py`, `qt_analysis_panel.py` |
| EDA 통계·추천 | `analysis.py` |
| 분석 탭 UI | `qt_analysis_panel.py` |
| 이상치(IQR/Z/IF) | `operations.py`, `analysis.py`, `qt_analysis_panel.py` |
| 차트 꾸미기 | `chart_style.py`, `qt_chart_style_dialog.py`, `qt_analysis_panel.py` |
| HTML 리포트 | `eda_report.py`, `qt_analysis_panel.py` |
| 대용량 최적화 | `performance.py`, `qt_app.py`, `qt_viewer.py` |
| 도움말 | `help_content.py` |
| QA | `scripts/run_all_qa.py`, `scripts/qa_*_smoke.py` |

---

## 4. 설정 파일

| 파일 | 위치 | 설명 |
|------|------|------|
| `theme.json` | `~/.gridloom/` | 앱 색상 |
| `chart_style.json` | `~/.gridloom/` | 분석 차트 색·레이아웃 |
| `window.json` | `~/.gridloom/` | 창 상태 |

---

## 5. QA

```bash
python scripts/run_all_qa.py
```

포함 항목:

- `qa_operations_smoke.py`
- `qa_analysis_smoke.py`
- `qa_analysis_panel_smoke.py`
- `qa_mainwindow_smoke.py` — MainWindow 로드·undo + 결측 다이얼로그·비동기 경로
- `qa_loader_smoke.py`
- `qa_viewer_smoke.py` — DataFrameViewer 검색 필터·클립보드 복사/붙여넣기
- `grid_smoke.py`

