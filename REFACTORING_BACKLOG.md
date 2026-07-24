# Gridloom — 리팩토링 & 기술 부채 백로그

> **목적:** 시스템 복잡도와 기술 부채를 **장기 관점**에서 추적·해소합니다.
> **원칙:** 한 번에 다 갈아엎지 않습니다. **작고 안전한 단위(increment)로, 매번 QA를 통과시키며** 점진적으로 정리합니다 (애자일).
>
> 함께 보기: [ARCHITECTURE.md](ARCHITECTURE.md) · [CODING_STANDARDS.md](CODING_STANDARDS.md)

---

## 1. 작업 규칙 (클린 코드 + 점진적 리팩토링)

각 항목(increment)은 다음을 지킵니다.

1. **범위를 작게** — 한 항목은 한 가지 문제만 해결합니다.
2. **동작 보존** — 리팩토링은 기능을 바꾸지 않습니다 (behavior-preserving).
3. **QA 게이트** — `python scripts/run_all_qa.py` 통과 후에만 완료 처리합니다.
4. **SSOT** — 중복된 문자열·로직은 한 곳으로 모읍니다.
5. **문서 동기화** — 구조가 바뀌면 관련 문서를 같은 PR에서 갱신합니다.

> 위험도(Risk)·효과(Impact)·노력(Effort)은 각각 낮음/보통/높음으로 표기합니다.
> 우선순위는 **효과 높고 위험 낮은 것** 먼저입니다.

---

## 2. 상태 보드

진단(2026-06-15, 자동 분석) 기준 ROI 순. 위험 낮고 효과 큰 것부터.

| # | 항목 | 상태 | 위험 | 효과 | 노력 |
|---|------|------|------|------|------|
| 1 | 의존성/설치 안내 **메시지** SSOT 통합 | ✅ 완료 | 낮음 | 보통 | 낮음 |
| 2 | `help_content`·문서 vs 실제 동작 불일치 정리 | ✅ 완료 | 낮음 | 보통 | 낮음 |
| 10 | 자율 작업 핸드오프 문서(`AGENTS.md`·`CONTRIBUTING.md`) | ✅ 완료 | 낮음 | 높음 | 보통 |
| 11 | DataFrameViewer 검색·클립보드 QA(`qa_viewer_smoke`) | ✅ 완료 | 낮음 | 보통 | 보통 |
| 14 | Mac 그래프 한글 폰트 fallback 보강 | ✅ 완료 | 낮음 | 보통 | 낮음 |
| 15 | 분석 개요 결측 그래프 가독성·크기 조절 | ✅ 완료 | 낮음 | 보통 | 낮음 |
| 12 | 필터 결과 행 추출(퀵윈 기능) | ✅ 완료 | 낮음 | 높음 | 보통 |
| 13 | CodePanel·VLookup 다이얼로그 E2E QA 보강 | ✅ 완료 | 낮음 | 보통 | 보통 |
| 16 | `window.json` 창 기하 저장·복원 (문서 정합) | ✅ 완료 | 낮음 | 보통 | 낮음 |
| 3 | `github_upload` 미러 동기화 부채(버전·grid UX 3버전 drift) | ✅ 완료 | 낮음 | 높음 | 보통 |
| 4 | 의존성 **UI 게이트**(enable/disable+경고) 일원화 `qt_dependency.py` | ✅ 완료 | 낮음 | 보통 | 보통 |
| 5 | `AnalysisPanel` 차트 공통 헬퍼 추출(`begin_chart`/sample/draw) | ✅ 완료 | 보통 | 높음 | 보통 |
| 6 | `qt_data_dialogs` 참조파일 로드·preview 공통 mixin | ✅ 완료 | 보통 | 보통 | 보통 |
| 7 | `MainWindow` 비동기 패턴 통합(load/fill `AsyncPoller`) | ✅ 완료 | 보통 | 보통 | 높음 |
| 8 | `operations.py` 도메인 분할(re-export 호환) | ✅ 완료 | 보통 | 높음 | 높음 |
| 9 | MainWindow·다이얼로그 E2E QA 공백 보강 | ✅ 완료 | 낮음 | 높음 | 높음 |
| L1 | (latent) >10,000열 윈도우 이동 UI 부재 | 📝 기록 | — | 낮음 | — |
| 17 | Mac·크로스플랫폼 UI 폰트 SSOT (`ui_fonts.py`) | ✅ 완료 | 낮음 | 높음 | 낮음 |
| C1 | 크롤링: 앱 내 로그인 브라우저(Qt WebEngine) | ✅ 완료 | 보통 | 높음 | 보통 |
| C2 | 크롤링: 규칙(프리셋) 저장·불러오기 | ✅ 완료 | 낮음 | 보통 | 보통 |
| C3 | 크롤링: JS 렌더 페이지(동적 HTML) 지원 | ✅ 완료 | 보통 | 높음 | 보통 |

범례: ✅ 완료 · 🔄 진행 중 · ⏳ 대기 · 📝 기록(관찰)

---

## 3. 완료된 작업

### #1 — 의존성/설치 안내 메시지 SSOT 통합 ✅

**문제:** `"pip install -r requirements.txt"`와 "scikit-learn이 필요합니다" 류 문구가
`analysis_deps.py`, `qt_analysis_panel.py`, `qt_data_dialogs.py` 등 **4개 파일에 흩어져** 있었습니다.
문구를 바꾸려면 여러 곳을 고쳐야 했고, 실제로 표현이 조금씩 달랐습니다(DRY 위반).

**해결:**
- `analysis_deps.py`에 단일 출처 추가:
  - `INSTALL_HINT` 상수
  - `package_label(module)` — `sklearn` → `scikit-learn` 변환
  - `feature_requirement_message(module, *, feature=None, inline=False)` — 표준 안내 문구 생성
- `qt_analysis_panel.py`·`qt_data_dialogs.py`의 하드코딩 문구를 모두 이 헬퍼 호출로 교체.

**효과:** 안내 문구를 바꿀 때 **한 곳만** 고치면 됩니다. 표현이 일관됩니다.
**QA:** `run_all_qa.py` 전체 통과.

---

## 4. 백로그 (예정)

> 아래는 자동 진단에서 도출된 구체 항목입니다. 파일·줄 위치는 작업 시 재확인합니다.

### #2 — 문서 vs 실제 동작 불일치 ✅
- ✅ `DEVELOPER_GUIDE.md` 역할 표의 `qt_dialogs.py` 중복 행 통합.
- ✅ `ARCHITECTURE.md` 신설 + `README`·`PROJECT_MAP` 인덱스 동기화.
- ✅ `help_content.py` "40열 초과 시 보이는 열만" 구버전 설명 → 네이티브 전체 스크롤로 정정.
- ✅ `grid/model.py` `MAX_DATA_COLUMNS=40` 의미 주석화(윈도우 페이지 크기, 10,000열 초과 전용).
- ✅ 미러 help/CHANGELOG 동기화는 #3 `sync_mirror.py`로 해결.

### #3 — `github_upload` 미러 동기화 부채 ✅
- (문제) 미러 버전 `0.8.11` vs 본체 `0.8.14`. grid UX·`analysis_deps`·help가 3버전 어긋남.
- ✅ `scripts/github_publish.py`의 `SKIP_DIRS`에 `github_upload` 추가 — API 배포 시 중복 트리 업로드 차단.
- ✅ `scripts/sync_mirror.py` 신설 — 본체를 SSOT로 미러를 자동 동기화(`--check` 드라이런 지원).
- ✅ 미러 1회 전체 동기화 완료(19개 파일 갱신, drift 0). 결정: **미러 유지 + 스크립트 동기화**.
- 운영 규칙: 본체 변경 후 `python scripts/sync_mirror.py` 실행(문서 체크리스트에 반영).

### #4 — 의존성 UI 게이트 일원화 ✅
- ✅ `df_tool/qt_dependency.py` 신설(UI 계층): `gate_widget`·`gate_combo_item`·`require`.
- ✅ `qt_analysis_panel._sync_dependency_controls`를 게이트 호출로 슬림화(버튼 3 + 콤보 2).
- ✅ KNN/MICE/Isolation Forest apply 가드를 `require(...)` 한 줄로 통일.
- 계층 유지: 문구는 `analysis_deps`(PyQt 무관), 위젯 제어는 `qt_dependency`만 PyQt 사용.
- (FillNa 다이얼로그는 콤보가 data 기반이 아니고 이미 중앙 메시지를 써서 현행 유지.)

### #5 — `AnalysisPanel` 차트 헬퍼 추출 ✅
- ✅ `MplCanvas.begin_chart()`(clear+add_subplot+style) — 7곳의 3줄 블록을 한 줄로.
- ✅ `MplCanvas.finish_chart()`(tight_layout+draw) — 5곳의 마무리 쌍을 한 줄로.
- ✅ `AnalysisPanel._sample_label_text()` — 단·이변량 표본 안내 문구 중복 제거.
- 격자형 Pair plot·단독 `draw()`는 의도적으로 그대로 둠(동작 보존).
- QA 전체 통과(차트 렌더링 동작 변화 없음).

### #6 — `qt_data_dialogs` 공통화 ✅
- ✅ `_prompt_load_reference(parent, title)` — 파일 선택→load_file→실패 경고를 한곳에.
- ✅ `_set_ref_file_label(label, loaded)` — "이름 (n행 × m열)" 라벨 공통화.
- ✅ VLookup/Merge `_load_reference`·Concat `_add_file`가 공통 헬퍼 사용.
- preview 채우기는 이미 `_preview_columns`/`_fill_table` 공유 중이라 추가 변경 없음.

### #7 — `MainWindow` 비동기 통합 ✅
- ✅ `df_tool/qt_async.py`의 `AsyncPoller`(future+QTimer 폴링) 신설.
- ✅ 파일 로드: `_load_future`+`_poll_file_load` → `AsyncPoller` + `_on_file_loaded` 콜백.
- ✅ 결측 채우기: `_fill_future`/`_fill_context`+`_poll_fill_missing` → `AsyncPoller` + 클로저 콜백(토큰 검사 보존).
- ✅ `closeEvent`도 poller `cancel()`로 정리.
- ✅ `qa_mainwindow_smoke`에 비동기 load·KNN fill을 이벤트 루프로 검증(회귀 안전망).
- (분석 패널은 `QThreadPool` 별도 유지 — 위험 대비 효익 낮아 현행.)

### #8 — `operations.py` 도메인 분할 ✅
- ✅ KNN/MICE 결측 대체 → `df_tool/ops_impute.py`.
- ✅ 이상치 탐지(IQR/Z/IsolationForest) → `df_tool/ops_outliers.py`.
- ✅ `operations.py`가 파일 끝에서 re-export → 기존 `from df_tool.operations import ...` 전부 유지.
- ✅ 순환 import 방지: leaf 모듈은 공용 헬퍼를 **함수 내부에서 지연 import**(leaf-first import도 안전).
- (CRUD·vlookup·group_summary는 핵심으로 보고 operations.py에 잔류 — 추가 분할은 필요 시.)

### #9 — 통합 QA 공백 보강 ✅
- ✅ `scripts/qa_mainwindow_smoke.py` 신설 — `run_all_qa`에 등록.
  - MainWindow: 로드 → `_apply_dataframe`(토큰·undo 스택 증가) → `undo`(복원) → 페이지 전환 → 배지 동기화.
  - `QtFillNaDialog`: mean 미리보기/적용 버튼 활성, KNN 적용 버튼이 scikit-learn 설치 여부와 일치.
- 이후 리팩토링(#4·#6·#8·#7)의 회귀 안전망으로 사용.
- ✅ 검색/필터·클립보드는 #11 `qa_viewer_smoke.py`로 보강 완료.
- ✅ CodePanel·VLookup E2E는 #13 `qa_panels_dialogs_smoke.py`로 보강 완료.

### #10 — 자율 작업 핸드오프 문서 ✅
- ✅ [AGENTS.md](AGENTS.md) — AI 에이전트용 불변식·표준 루프·금지 사항·환경.
- ✅ [CONTRIBUTING.md](CONTRIBUTING.md) — 사람 기여자용 5분 시작·기여 흐름·테스트·미러·PR 체크리스트.
- ✅ `README`·`PROJECT_MAP` 문서 인덱스에 연결.

### #11 — DataFrameViewer QA 보강 ✅
- ✅ `scripts/qa_viewer_smoke.py` — set/get 라운드트립, 검색 필터, 클립보드 복사/붙여넣기(headless).
- ✅ `run_all_qa.py`에 등록. (이후 #13에서 8종으로 확대)

### 순차 작업 계획 (2026-07-13)

| 순서 | ID | 작업 | SSOT | 완료 조건 |
|------|----|------|------|-----------|
| W1 | #12 | 필터 결과 행 추출 | `operations.extract_rows` → viewer `_apply_df` → undo | ✅ QA + help + CHANGELOG + `sync_mirror` |
| W2 | #13 | CodePanel·VLookup E2E QA | 기존 패널/다이얼로그 경로 headless 호출 | ✅ `run_all_qa` 등록 + `sync_mirror` |
| W3 | #16 | `window.json` 창 기하 persist | 읽기/쓰기 한 모듈 + `qt_app`만 적용 | ✅ 문서 정합 + QA 스모크 + `sync_mirror` |

규칙: 한 번에 한 행만 완료. 매 행마다 **변경 → QA → sync_mirror → 버전/문서**.

### #12 — 필터 결과 행 추출(퀵윈 기능) ✅
- ✅ `operations.extract_rows(df, indices)` — copy 후 `loc` 순서 보존.
- ✅ viewer `[결과 추출]` — 필터 활성 시에만 enable, 확인 후 `_apply_df`(undo 가능).
- ✅ help·CHANGELOG·operations/viewer smoke QA.

### #13 — CodePanel·VLookup E2E QA 보강 ✅
- ✅ `scripts/qa_panels_dialogs_smoke.py` — CodePanel.execute 성공/오류, VLookup preview/apply(참조 DF 주입).
- ✅ `run_all_qa.py`에 등록 (당시 QA 8종; 이후 crawl 등으로 확대).

### #16 — `window.json` 창 기하 저장·복원 ✅
- ✅ `df_tool/window_state.py` — load/save SSOT (`~/.gridloom/window.json`).
- ✅ `qt_app` 시작 시 복원 · `closeEvent`에서 저장.
- ✅ help·PROJECT_MAP·qa_mainwindow_smoke 라운드트립.

### #14 — Mac 그래프 한글 폰트 fallback 보강 ✅
- ✅ `analysis.configure_matplotlib_font()`가 없는 폰트명을 무조건 지정하지 않고, `font_manager`로 실제 설치 폰트를 확인.
- ✅ macOS 기본 후보(`AppleGothic`, `Apple SD Gothic Neo`)와 Noto/Nanum 계열을 우선 탐색.
- ✅ `qa_analysis_smoke.py`에 rcParams 설정 검증 추가.
- ✅ `SETUP_GUIDE.md`에 Mac 그래프 한글 네모(□) FAQ 추가.

### #15 — 분석 개요 결측 그래프 가독성·크기 조절 ✅
- ✅ 개요 탭의 표/결측 비율 그래프를 세로 splitter로 분리해 사용자가 높이를 조절 가능.
- ✅ 그래프 figure 크기는 항목 수를 참고하되, 위젯 최소 높이는 낮게 유지해 사용자가 줄일 수 있게 조정.
- ✅ 긴 열 이름은 축 라벨에서 말줄임 처리해 그래프 영역 침범 완화.
- ✅ 좌측 여백·라벨 길이·tick padding을 줄여 그래프가 오른쪽으로 치우쳐 보이는 현상 완화.
- ✅ `qa_analysis_panel_smoke.py`에 다수 결측 열 회귀 검증 추가.

### #17 — Mac·크로스플랫폼 UI 폰트 SSOT ✅
- ✅ `df_tool/ui_fonts.py` — UI/모노스페이스/HTML 스택 (PyQt 무관).
- ✅ `qt_theme.app_stylesheet` · `monospace_qfont` · 코드/로그·디자인 설정·EDA HTML 적용.
- ✅ `SETUP_GUIDE.md` UI 한글 FAQ · CHANGELOG v0.8.29.

### L1 — (latent) >10,000열 윈도우 이동 UI 부재 📝
- 열 윈도우 이동 스크롤바 제거 후, 10,000열 초과 표는 첫 40열만 보일 수 있음(매우 드문 케이스).
- 즉시 수정 대신 관찰. 실제 요구 시 키보드/메뉴 기반 오프셋 이동으로 대응.

### C1·C3 — 로그인 브라우저 · JS 렌더 ✅
- ✅ `qt_webengine_crawl.py` — LoginBrowserDialog + RenderedHtmlFetcher (공유 프로필).
- ✅ 크롤 패널: [로그인 브라우저] · [브라우저 렌더 미리보기] · [브라우저로 일괄].
- ✅ `PyQt6-WebEngine` + `analysis_deps.webengine_available` / `qt_dependency` 게이트.
- ✅ 세션 경로 `~/.gridloom/webengine/`.

### C2 — 크롤링 규칙(프리셋) 저장·불러오기 ✅
- ✅ `df_tool/crawl_presets.py` — `~/.gridloom/crawl_presets.json` SSOT (PyQt 없음).
- ✅ 크롤 패널: 프리셋 콤보 · 불러오기 · 현재 저장 · 삭제.
- ✅ 브라우저 일괄 취소: `cancel_pending`이 큐·WebEngine fetch·poller를 함께 중단.

## 5. 진행 방식

매 작업 세션마다:
1. 이 보드에서 **위험 낮고 효과 높은** 다음 항목 1개를 고른다.
2. 작은 단위로 수정 → `run_all_qa.py` 통과 확인.
3. 이 문서의 상태/완료 섹션을 갱신한다.
4. 필요 시 버전·`CHANGELOG.md`를 올린다.
