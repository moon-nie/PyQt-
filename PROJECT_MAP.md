# Gridloom — 프로젝트 파일 지도

> **목적:** 파일이 많아도 어디를 고치면 되는지 바로 찾기  
> **PyQt** (`gridloom.pyw`) 기준 · v0.8.10

| 함께 볼 문서 | 대상 |
|--------------|------|
| [README.md](README.md) | 문서 인덱스 |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | 설치·실행 |
| [LEARNING_GUIDE.md](LEARNING_GUIDE.md) | 코드 공부 순서 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 기능 추가 |
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
│   ├── qa_loader_smoke.py
│   └── grid_smoke.py
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
    ├── operations.py         pandas 변환 SSOT
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
- `qa_loader_smoke.py`
- `grid_smoke.py`

