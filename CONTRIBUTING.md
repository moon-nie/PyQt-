# CONTRIBUTING.md — Gridloom 기여 가이드

> **이 문서는 무엇인가요?**
> **Gridloom**(PyQt6 데스크톱 표/EDA 데이터 도구)에 처음 기여하는 분을 위한 안내입니다.
> 프로그래밍을 막 시작한 분도 따라올 수 있게 친절하게 적었습니다.
>
> - 코드 구조가 처음이라면 → [ARCHITECTURE.md](ARCHITECTURE.md)부터 (10분이면 큰 그림이 잡힙니다)
> - 코드 읽는 순서가 궁금하면 → [LEARNING_GUIDE.md](LEARNING_GUIDE.md)
> - AI 코딩 에이전트라면 → [AGENTS.md](AGENTS.md)의 운영 규칙을 보세요.

---

## 1. 5분 만에 시작하기

### 1-1. 설치

```powershell
git clone https://github.com/moon-nie/PyQt-.git
cd PyQt-
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> 분석 탭(EDA)까지 쓰려면 `requirements.txt`에 포함된 **matplotlib · numpy · scikit-learn · scipy**가 함께 설치되어야 합니다.
> OS별(Windows/Mac) 상세 설치는 [SETUP_GUIDE.md](SETUP_GUIDE.md)에 단계별로 정리되어 있습니다.

### 1-2. 실행

```powershell
python gridloom.pyw
```

상단 **[열기]** → 프로젝트 안의 `sample_data.csv`를 선택해 표가 보이면 성공입니다.
실행 엔트리포인트는 **`gridloom.pyw`** 하나뿐입니다.

### 1-3. QA(테스트) 실행

코드를 고치기 전·후로 항상 전체 QA가 통과하는지 확인합니다.

```powershell
$env:PYTHONPATH = "."
python scripts/run_all_qa.py
```

마지막 줄에 `run_all_qa: OK`가 보이면 통과입니다. (Windows PowerShell 기준. `$env:PYTHONPATH = "."`를 먼저 실행하세요.)

---

## 2. 기여 흐름 (Workflow)

```
1) 이슈/할 일 정하기
2) 브랜치 만들기  →  3) 작게 수정  →  4) QA 통과  →  5) 미러 동기화
                                                  ↓
                          6) 문서·버전 갱신  →  7) PR 올리기
```

1. **무엇을 할지 정합니다.** 직접 정할 항목이 없다면 [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)에서
   **위험 낮고 효과 높은** 항목을 하나 고르세요.
2. **브랜치를 만듭니다** (예: `feature/uppercase-column`, `fix/empty-data-guard`).
3. **작은 단위로** 수정합니다. 요청과 무관한 대규모 포맷 변경은 피합니다([CODING_STANDARDS.md](CODING_STANDARDS.md) §1).
4. **QA를 통과**시킵니다(§1-3).
5. 코드/문서를 바꿨다면 **미러를 동기화**합니다(§6).
6. 바뀐 내용에 맞춰 **문서·버전을 갱신**합니다(§5·§7).
7. **PR을 올립니다** — 아래 체크리스트를 확인하세요.

---

## 3. 어디에 코드를 추가하나요? (기능 유형별)

Gridloom은 **3층 구조**(UI / 로직 / 라이브러리)이고, "**화살표는 위에서 아래로만**" 흐릅니다.
즉 **로직 층(`operations.py`·`analysis.py`)은 화면(PyQt)을 절대 모릅니다.** (그림 설명: [ARCHITECTURE.md](ARCHITECTURE.md) §2~§4)

기능 유형별로 어느 파일을 고칠지는 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) §3에 코드 예시와 함께 정리되어 있습니다. 요약하면:

| 만들려는 것 | 주로 고치는 곳 | 자세히 |
|-------------|----------------|--------|
| 데이터만 바꾸는 버튼·메뉴(완전동일 행 제거 등) | `operations.py` → `qt_app.py` | DEVELOPER_GUIDE §3 유형 A |
| 표 우클릭/단축키 동작 | `qt_viewer.py` → `operations.py` | 유형 B |
| 행/열 구조 변경 + 입력창 | `operations.py` → `qt_viewer_ops.py` → `qt_viewer.py` | 유형 C |
| 새 PyQt 팝업 | `qt_dialogs.py` 또는 전용 `qt_*.py` | 유형 D |
| 메인 창·파일·설정 | `qt_app.py` | 유형 E |
| 표 엔진 저수준(헤더·셀 그리기) | `df_tool/grid/` | 유형 F |
| EDA 분석·통계 | `analysis.py`(로직) + `qt_analysis_panel.py`(UI) | DEVELOPER_GUIDE §2-1 |

**꼭 기억할 점:**

- 데이터 변환은 **`operations.py`**에서만(입력을 직접 바꾸지 말고 `.copy()` 후 반환).
- 화면 반영은 `qt_app.py`의 **`_apply_dataframe`**(undo가 여기서 쌓입니다) 또는 viewer의 `_apply_df`.
- 의존성 안내 문구는 **`analysis_deps.py`** 한 곳에서만 만들고, 버튼 활성/비활성은 **`qt_dependency.py`**를 씁니다.
- 무거운 백그라운드 작업은 **`qt_async.AsyncPoller`**를 씁니다.

파일이 어디 있는지 헷갈리면 [PROJECT_MAP.md](PROJECT_MAP.md)에서 찾으세요.

---

## 4. 테스트 작성 가이드 (headless smoke)

Gridloom의 테스트는 **GUI를 직접 클릭하지 않고**(headless) 동작을 검증하는 `scripts/qa_*_smoke.py` 패턴을 씁니다.

### 4-1. 패턴

- 각 smoke 스크립트는 `main() -> int`를 갖고, 성공 시 `print("...: OK")` 후 `0`을 반환합니다.
- 검증은 평범한 `assert`로 합니다. 실패하면 `assert`가 예외를 던져 비정상 종료됩니다.
- 새 테스트 스크립트를 추가하면 [`scripts/run_all_qa.py`](scripts/run_all_qa.py)의 `scripts` 목록에 이름을 등록해야 함께 돌아갑니다.

### 4-2. 어떤 파일에 추가하나요?

| 검증 대상 | 추가할 스크립트 |
|-----------|-----------------|
| `operations.py` 데이터 변환 | `scripts/qa_operations_smoke.py` |
| EDA 통계·분석 로직(`analysis.py`) | `scripts/qa_analysis_smoke.py` |
| 분석 패널 UI | `scripts/qa_analysis_panel_smoke.py` |
| 메인 창 로드·undo·다이얼로그 | `scripts/qa_mainwindow_smoke.py` |
| CodePanel·VLookup 다이얼로그 | `scripts/qa_panels_dialogs_smoke.py` |
| 크롤링 로직(`crawl.py`) | `scripts/qa_crawl_smoke.py` |
| 파일 입출력(`loader.py`) | `scripts/qa_loader_smoke.py` |
| 표 Facade(검색 필터·클립보드) | `scripts/qa_viewer_smoke.py` |
| 표 엔진(GridModel·헤더·열 재정렬) | `scripts/grid_smoke.py` |

### 4-3. 예시 (operations 테스트의 형태)

`scripts/qa_operations_smoke.py`는 다음처럼 순수 함수를 직접 호출해 결과를 단언합니다.

```python
import pandas as pd
from df_tool.operations import sort_dataframe

def main() -> int:
    df = pd.DataFrame({0: [3, 1, 2]})
    sorted_df = sort_dataframe(df, "0")   # int 열명도 처리되는지 확인
    assert sorted_df[0].tolist() == [1, 2, 3]
    print("qa_operations_smoke: OK")
    return 0
```

> **팁:** 로직 층 함수는 PyQt가 필요 없어 이렇게 GUI 없이 빠르게 테스트됩니다. 가능하면 새 기능의 핵심을 `operations.py`/`analysis.py`에 두고 여기서 검증하세요.

자주 점검하는 항목(빈 데이터, `0`·`1` 같은 int 열명, 필터·정렬 후 동작, undo)은 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) §8 QA 체크리스트를 참고하세요.

---

## 5. 문서 갱신 의무

코드만 바꾸고 문서를 두면 다음 사람이 헤맵니다. 변경 종류에 따라 아래 문서를 **같은 PR에서** 갱신하세요([CODING_STANDARDS.md](CODING_STANDARDS.md) §8).

| 변경 | 갱신할 문서 |
|------|-------------|
| 새 버튼·단축키·사용자 동작 | `df_tool/help_content.py`, [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| 새 파일 추가 | [PROJECT_MAP.md](PROJECT_MAP.md) |
| 리팩토링·구조 변경 | [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md) |
| 사용자 동작 변경·릴리스 | [CHANGELOG.md](CHANGELOG.md) |
| 버전 릴리스 | [CHANGELOG.md](CHANGELOG.md) + `df_tool/__init__.py`(`__version__`) |

---

## 6. 미러 동기화 규칙 (`github_upload/`)

이 저장소에는 GitHub 웹 업로드용 **수동 미러** 폴더 `github_upload/`가 있습니다.
본체가 단일 출처(SSOT)이며, 미러가 어긋나면 배포 사고로 이어집니다.

- ✅ **본체 코드/문서를 고쳤으면** 아래로 미러를 맞춥니다.
- ❌ **`github_upload/` 안의 파일을 직접 손으로 편집하지 마세요.**

```powershell
python scripts/sync_mirror.py --check   # 먼저 차이만 확인(파일을 바꾸지 않는 드라이런)
python scripts/sync_mirror.py           # 실제 동기화
```

`--check`가 차이를 보고하면, `--check` 없이 다시 실행해 동기화한 뒤 그 변경도 함께 커밋합니다.

---

## 7. PR 전 체크리스트

PR을 올리기 전, 아래를 확인하세요. (자세한 항목은 [CODING_STANDARDS.md](CODING_STANDARDS.md) §9 "커밋 전 자가 점검"을 그대로 따릅니다.)

- [ ] `operations.py`(로직)에 PyQt/Tk import나 UI 문자열이 없는가? (계층 규칙)
- [ ] 데이터 변경이 `operations` → `_apply_dataframe`/`_apply_df` 경로를 거치는가? (undo 보존)
- [ ] 빈 데이터(`_require_data`)·int 열명·필터/정렬 후에도 동작하는가?
- [ ] `$env:PYTHONPATH = "."; python scripts/run_all_qa.py`가 **통과**했는가?
- [ ] 새 로직에 대한 headless 테스트를 `scripts/qa_*_smoke.py`에 보강했는가?
- [ ] 코드/문서를 바꿨다면 `python scripts/sync_mirror.py`로 미러를 맞췄는가?
- [ ] 필요한 문서(§5)와 버전·[CHANGELOG.md](CHANGELOG.md)를 갱신했는가?
- [ ] 요청과 무관한 대규모 포맷·이름 변경을 넣지 않았는가? (최소 diff)

---

## 8. 막히면

| 상황 | 볼 문서 |
|------|---------|
| 전체 구조가 안 그려짐 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 어떤 파일부터 읽지? | [LEARNING_GUIDE.md](LEARNING_GUIDE.md) |
| 이 기능 어디에 넣지? | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [PROJECT_MAP.md](PROJECT_MAP.md) |
| 규칙·금지 사항 | [CODING_STANDARDS.md](CODING_STANDARDS.md) |
| 다음에 뭘 개선하지? | [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md) |
| 설치가 안 됨 | [SETUP_GUIDE.md](SETUP_GUIDE.md) §5 FAQ |

환영합니다. 작은 PR부터 편하게 시작하세요!
