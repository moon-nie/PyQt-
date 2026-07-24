# Gridloom — 아키텍처 한눈에 보기 (초심자용)

> **이 문서는 무엇인가요?**
> 코드를 처음 보는 사람이 **10분 안에 전체 구조를 이해**하도록 만든 지도입니다.
> 프로그래밍을 막 시작한 분도 따라올 수 있게 비유와 그림 위주로 설명합니다.
>
> | 다음에 읽을 문서 | 용도 |
> |------------------|------|
> | [LEARNING_GUIDE.md](LEARNING_GUIDE.md) | 파일을 **어떤 순서로** 읽을지 |
> | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 기능을 **어떻게 추가**할지 |
> | [CODING_STANDARDS.md](CODING_STANDARDS.md) | 코드 **작성 규칙·금지 사항** |
> | [PROJECT_MAP.md](PROJECT_MAP.md) | 파일별 **위치 찾기** |
> | [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md) | 정리 중인 **기술 부채 목록** |

---

## 1. Gridloom이 하는 일 (한 문장)

**엑셀/CSV를 열어 표로 보여주고, 클릭과 단축키로 데이터를 가공하며, 통계·차트로 분석(EDA)하는 데스크톱 앱**입니다.

- 화면(GUI)은 **PyQt6**로 그립니다.
- 데이터 계산은 **pandas**가 합니다.
- 차트·통계는 **matplotlib / scikit-learn / scipy**가 (있을 때만) 거듭니다.

---

## 2. 큰 그림 — 3층 구조

Gridloom의 모든 코드는 아래 3개 층 중 하나에 속합니다. **이 3층만 기억하면 절반은 이해한 것**입니다.

```
┌─────────────────────────────────────────────┐
│  ① UI 층 (화면·입력·선택)                     │
│     qt_app · qt_viewer · grid/ · qt_*_dialog  │
│     "버튼을 그리고 클릭을 받는다"               │
└───────────────────────┬─────────────────────┘
                        │ 호출 (데이터 바꿔줘)
                        ▼
┌─────────────────────────────────────────────┐
│  ② 로직 층 (순수 계산, 화면 모름)              │
│     operations · analysis · loader · eda_report│
│     "pandas로 실제 데이터를 바꾼다"             │
└───────────────────────┬─────────────────────┘
                        │ 사용
                        ▼
┌─────────────────────────────────────────────┐
│  ③ 라이브러리 (pandas · numpy · matplotlib …) │
└─────────────────────────────────────────────┘
```

### 가장 중요한 규칙 하나

> **화살표는 위에서 아래로만 흐릅니다.**
> UI는 로직을 부를 수 있지만, **로직 층은 절대 UI(PyQt)를 모릅니다.**

왜 이렇게 할까요?

- 로직(`operations.py`)에 화면 코드가 없으면, **GUI 없이 테스트**할 수 있습니다 (`scripts/`의 QA가 이렇게 동작).
- 화면 디자인을 바꿔도 데이터 계산이 깨지지 않습니다.
- 버그가 났을 때 "화면 문제인지 / 계산 문제인지" 빠르게 나뉩니다.

---

## 3. 누가 누구를 import 해도 되나? (의존성 규칙)

클린 아키텍처의 핵심은 "**아무나 아무거나 가져다 쓰지 않는다**"입니다.

| 모듈 | import 해도 되는 것 | 절대 import 금지 |
|------|--------------------|------------------|
| `operations.py` (로직) | pandas, numpy, `selection.py` | ❌ PyQt6, tkinter, qt_* |
| `analysis.py` / `eda_report.py` (로직) | pandas, numpy, matplotlib | ❌ PyQt6, qt_* |
| `grid/` (표 엔진) | PyQt6, `selection.py` | ❌ pandas 직접 (DataFrame은 `GridModel` 경유) |
| `qt_viewer.py` (Facade) | grid/, operations, qt_dialogs | — |
| `qt_app.py` (메인 창) | 거의 전부 | — |

> 기억법: **`operations.py`에 `import PyQt6`가 보이면 그건 버그입니다.**

이 규칙은 [CODING_STANDARDS.md](CODING_STANDARDS.md) §10 "금지 사항"에도 적혀 있고, QA가 일부를 자동으로 검사합니다.

---

## 4. 클릭 한 번이 코드에서 흐르는 전체 경로

가장 흔한 예시 — **"중복 행 제거" 버튼**을 눌렀을 때:

```
1) 사용자가 버튼 클릭
        │
2) qt_app.py 의 핸들러(_on_drop_duplicates 류)가 받음
        │   - 먼저 _require_data() 로 "표가 비어있지 않은가?" 확인
        │
3) operations.py 의 drop_duplicates(df) 호출   ← 순수 계산
        │   - df.copy() 후 중복 제거한 새 DataFrame 반환 (원본 안 건드림)
        │
4) qt_app._apply_dataframe(new_df, "완전동일 행 제거")
        │   - undo 스택에 직전 상태 push (Ctrl+Z 가능)
        │   - viewer.set_dataframe(new_df) 로 화면 갱신
        │   - info 패널·작업 로그 갱신
        │
5) 화면의 표가 새 데이터로 다시 그려짐
```

**핵심 포인트 3가지:**

1. **계산은 항상 ②층(`operations.py`)에서** — UI 핸들러는 "부르고 받기"만 합니다.
2. **`_apply_dataframe`를 거쳐야 undo가 쌓입니다** — 데이터를 바꿀 땐 이 함수를 통합니다.
3. **원본 DataFrame은 직접 수정하지 않습니다** — 항상 `.copy()` 후 새 것을 반환.

> 더 많은 추적 예시(Ctrl+C 복사, 열 드래그 등)는 [LEARNING_GUIDE.md](LEARNING_GUIDE.md) §4 참고.

---

## 5. 분석 탭(EDA)은 한 단계 더 있습니다

통계·차트·KNN 같은 무거운 작업은 **화면이 멈추지 않도록 백그라운드**에서 돕니다.

```
분석 버튼 클릭 (qt_analysis_panel.py)
   │
   ├─ 가벼운 작업 → 바로 계산해서 표시
   │
   └─ 무거운 작업(KNN·이상치·PCA)
          │
          ▼
      qt_analysis_worker.py  (QThreadPool에서 별도 실행)
          │   - 시작 시점의 데이터 복사본으로 계산
          │   - 도중에 데이터가 바뀌면(_data_token 불일치) 결과를 버림
          ▼
      끝나면 메인 스레드에서 차트/표에 반영
```

- 선택 패키지(scikit-learn·scipy)가 없으면 관련 버튼은 **자동으로 비활성**되고 설치 안내를 띄웁니다.
- 그 안내 문구는 **`analysis_deps.py` 한 곳**에서만 만듭니다 (`feature_requirement_message`). 문구를 바꿀 땐 여기만 고치세요.

---

## 6. 초심자용 용어 사전

| 용어 | 쉬운 설명 |
|------|-----------|
| **DataFrame** | pandas의 "표" 객체. Gridloom이 다루는 데이터 그 자체 |
| **operations** | 화면을 모르는 순수 계산 함수 모음. 데이터 변경의 "주방" |
| **Facade(파사드)** | 복잡한 내부를 가리고 간단한 입구만 보여주는 것. `qt_viewer.py`가 표 엔진의 입구 |
| **GridModel** | pandas 표 ↔ Qt 화면을 연결하는 번역기 (`QAbstractTableModel`) |
| **SelectionScope** | "지금 어떤 셀/행/열이 선택됐나"를 화면과 무관하게 표현한 데이터 |
| **undo 스택** | Ctrl+Z를 위해 직전 상태들을 쌓아둔 목록 |
| **restructure** | 행/열 개수가 바뀌는 변경(`True`) vs 값만 바뀌는 변경(`False`) |
| **EDA** | 탐색적 데이터 분석. 통계·분포·상관·이상치를 살펴보는 것 |
| **선택적 의존성** | 없어도 앱은 돌아가지만, 있으면 추가 기능이 켜지는 패키지 (scikit-learn 등) |
| **SSOT** | Single Source of Truth. "같은 정보는 한 곳에만" 원칙 |

---

## 7. 30초 요약

1. 코드는 **UI 층 / 로직 층 / 라이브러리** 3층이다.
2. **화살표는 아래로만** — 로직은 화면(PyQt)을 모른다.
3. 데이터 변경은 **`operations.py`에서 계산 → `_apply_dataframe`로 반영**.
4. 무거운 분석은 **백그라운드 워커**가 처리한다.
5. **같은 문구·로직은 한 곳에만** 둔다 (SSOT).

이 5개만 알면, 나머지는 [LEARNING_GUIDE.md](LEARNING_GUIDE.md)를 따라 파일을 하나씩 열어보며 채우면 됩니다.
