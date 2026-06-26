# Gridloom

**Gridloom** — PyQt6 기반 **desktop tabular data workbench** (데스크톱 표 데이터 워크벤치)

CSV·Excel 등 표 데이터를 열어 보고, 편집하고, VLOOKUP·조인·그룹 집계로 가공하는 Python 데스크톱 앱입니다.

[![Repository](https://img.shields.io/badge/GitHub-PyQt--blue)](https://github.com/moon-nie/PyQt-)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **English:** A PyQt6 desktop tabular data workbench for CSV/Excel viewing, editing, and data wrangling (merge, VLOOKUP, group-by).

- **실행:** `python gridloom.pyw`
- **버전:** v0.8.21 (`df_tool/__init__.py`)
- **저장소:** https://github.com/moon-nie/PyQt-

---

## 빠른 시작

```bash
git clone https://github.com/moon-nie/PyQt-.git
cd PyQt-
pip install -r requirements.txt
python gridloom.pyw
```

`sample_data.csv`로 바로 테스트할 수 있습니다.

자세한 설치: [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 주요 기능

- CSV / Excel / Parquet 등 다양한 형식 열기·저장
- Excel 스타일 셀 선택·편집·복사·붙여넣기
- VLOOKUP, 조인(Merge), 세로 병합(Concat), 그룹 요약 — **미리보기 포함**
- **분석 탭 (EDA)** — 개요·단·이·다변량, Pair plot, EDA 요약·차트 포함 HTML 리포트
- **결측·이상치** — KNN/MICE 결측 대체, IQR·Z·Isolation Forest 이상치 제거
- **차트 꾸미기** — 색·글자·범례·색상맵 사용자 설정
- **결측치 채우기** (평균·중앙값·KNN·최빈값 등), **열 병합·열 분리**
- 검색 필터 ([검색] 버튼), 찾기/바꾸기, 중복·결측 행 제거
- Python 코드 패널, PyQt6 `QTableView` 기반 고성능 표 엔진

---

## 문서

| 문서 | 대상 |
|------|------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | 설치·실행 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | **기여 가이드 (사람)** |
| [AGENTS.md](AGENTS.md) | **AI 에이전트 운영 규칙** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 아키텍처 한눈에 보기 (초심자) |
| [LEARNING_GUIDE.md](LEARNING_GUIDE.md) | 코드 공부 순서 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 기능 추가 |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | 작성 규칙 |
| [PROJECT_MAP.md](PROJECT_MAP.md) | 파일 지도 |
| [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md) | 기술 부채·리팩토링 추적 |
| [MIGRATION_QT.md](MIGRATION_QT.md) | PyQt 전환 기록 (아카이브) |
| [CHANGELOG.md](CHANGELOG.md) | 변경 기록 |

---

## 프로젝트 구조

```
Gridloom/
├── gridloom.pyw              ← PyQt 실행
├── df_tool/
│   ├── qt_app.py             ← 메인 창
│   ├── qt_viewer.py          ← 표 Facade
│   ├── qt_analysis_panel.py  ← EDA 분석 탭
│   ├── analysis.py           ← EDA 통계·차트 추천
│   ├── chart_style.py        ← 차트 색·레이아웃 설정
│   ├── eda_report.py         ← HTML 리포트 생성
│   ├── qt_data_dialogs.py    ← VLOOKUP·조인·병합·그룹
│   ├── grid/                 ← QTableView 엔진
│   ├── operations.py         ← pandas SSOT
│   └── loader.py             ← 파일 I/O
├── scripts/                  ← QA
└── *.md
```

---

## QA

```bash
python scripts/run_all_qa.py
```

---

## License

MIT — [LICENSE](LICENSE)
