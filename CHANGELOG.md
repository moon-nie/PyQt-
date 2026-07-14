# Gridloom — 변경 기록

## v0.8.29 (2026-07-14)

### Mac·크로스플랫폼 UI 폰트 (한글 깨짐 방지)
- UI 전역 스타일·코드/로그 모노스페이스·EDA HTML 리포트 폰트를 OS별로 선택
- SSOT: `df_tool/ui_fonts.py` (PyQt 무관) · Qt는 `qt_theme.monospace_qfont`
- Mac: Apple SD Gothic Neo / Menlo · Windows: Segoe UI+맑은 고딕 / Consolas
- 차트(Matplotlib) 한글은 기존 `analysis.configure_matplotlib_font` 유지

---

## v0.8.28 (2026-07-14)

### 크롤링 파라미터 소스 · Cookie/attr 안내 · Shift 열 선택
- 일괄 파라미터: **열린 표의 열** / **파일에서 불러오기** / 직접 입력
- Cookie·attr(text/href/src) **도움말 버튼** 추가 (브라우저 로그인 Cookie 복사 방법 안내)
- 표 **Shift+열 헤더**로 열 범위 다중 선택 (행과 동일 패턴)

---

## v0.8.27 (2026-07-14)

### 크롤링 일괄(URL 패턴) + Cookie
- **일괄 (URL 패턴)** 탭: `...?code={code}` 템플릿 + 종목코드 목록 + 다중 열 매핑(`열|selector|attr`)
- 요청 간격·최대 건수 조절, 행마다 `error` 열로 실패 기록
- 선택적 **Cookie** 헤더(브라우저 세션 붙여넣기) — 로그인 필요 페이지용 경량 지원
- `crawl_batch` / `parse_param_list` / `parse_fields_text` / `render_url_template` SSOT
- 예: [네이버 증권 종목](https://finance.naver.com/item/main.naver?code=005930)처럼 code만 바꿔 여러 종목 수집

---

## v0.8.26 (2026-07-14)

### 크롤링 구조 스캔
- URL만 넣고 **[구조 스캔]** 하면 반복 목록(형제 블록) 후보를 점수순으로 제안
- 후보 클릭 시 CSS selector·추천 속성(text/href) 자동 채움 후 미리보기 실행
- 로직: `crawl.scan_structure` / `scan_url_structure` (PyQt 없음)
- `qa_crawl_smoke`에 구조 스캔 회귀 검증 추가

---

## v0.8.25 (2026-07-13)

### 크롤링 탭 MVP
- 네비에 **크롤링** 탭 추가 (가공 · 분석 · 크롤링 · 작업 로그)
- URL + CSS selector(DevTools Copy selector) + 추출 속성(text/href/src)으로 정적 HTML 수집
- **미리보기** 후 **표로 가져오기** → 가공 탭 DataFrame으로 로드·편집·저장 가능
- 로직 SSOT: `df_tool/crawl.py` (PyQt 없음) · UI: `qt_crawl_panel.py` · 네트워크는 AsyncPoller
- `qa_crawl_smoke.py` 추가 (로컬 HTML, 네트워크 없음)

---

## v0.8.24 (2026-07-13)

### 창 위치·크기 기억
- 종료 시 `~/.gridloom/window.json`에 위치·크기·최대화 여부를 저장하고, 다음 실행 때 복원
- 읽기/쓰기는 `window_state.py` 단일 출처(SSOT), UI는 `qt_app`만 적용
- 문서에만 있던 `window.json` 안내와 실제 동작을 맞춤

---

## v0.8.23 (2026-07-13)

### 필터 결과 행 추출
- 검색으로 좁힌(표에 보이는) 행만 데이터로 남기는 **[결과 추출]** 버튼 추가
- pandas 변환은 `operations.extract_rows` 단일 출처(SSOT), UI는 확인 후 `_apply_df` — Ctrl+Z로 되돌리기 가능
- `qa_operations_smoke`·`qa_viewer_smoke`에 추출 경로 회귀 검증 추가
- 도움말(검색 섹션)에 결과 추출 안내 반영

### 개발/QA
- `qa_panels_dialogs_smoke.py` 추가 — CodePanel 실행·VLookup 미리보기/적용 headless 검증 (`run_all_qa` 8종)

---

## v0.8.22 (2026-07-13)

### 표 왼쪽 위 코너 클릭으로 전체 선택
- 행 번호·열 헤더가 만나는 왼쪽 최상단(코너)을 클릭하면 Ctrl+A와 동일하게 전체 셀이 선택됨
- 도움말에 이미 안내돼 있었으나 코너 버튼이 비활성화되어 있던 UX 공백을 맞춤
- `qa_viewer_smoke.py`에 코너 클릭 → 전체 선택 회귀 검증 추가

---

## v0.8.21 (2026-06-26)

### 분석 개요 그래프 좌측 정렬 보정
- 개요 탭 결측 비율 그래프의 왼쪽 축 라벨 영역을 더 줄여 막대 영역이 오른쪽으로 밀려 보이던 현상 추가 완화
- 긴 열 이름 말줄임 길이를 더 짧게 조정하고 y축 tick padding을 축소
- `qa_analysis_panel_smoke.py`에 subplot 좌측 시작 위치 회귀 검증 추가

---

## v0.8.20 (2026-06-26)

### 분석 개요 그래프 크기 조절 후속 개선
- 개요 탭 결측 비율 그래프가 splitter에서 너무 크게 고정되어 줄어들지 않던 문제 수정
- 그래프 위젯 최소 높이를 낮춰 사용자가 표/그래프 비율을 더 자유롭게 조절 가능
- 긴 축 라벨 말줄임 폭과 좌측 여백을 줄여 그래프가 오른쪽으로 치우쳐 보이던 현상 완화
- `qa_analysis_panel_smoke.py`를 그래프 최소 높이가 낮게 유지되는지 검증하도록 보강

---

## v0.8.19 (2026-06-26)

### 분석 개요 결측 그래프 가독성 개선
- 분석 탭 개요의 표/열별 결측 비율 그래프를 세로 splitter로 분리해 사용자가 높이를 직접 조절 가능
- 결측 상위 항목이 많을 때 그래프 최소 높이를 항목 수에 맞춰 자동 보정
- 긴 열 이름은 차트 축에서 말줄임 처리해 막대 영역을 덮지 않도록 개선
- `qa_analysis_panel_smoke.py`에 다수 결측 열 환경에서 개요 그래프 영역이 확보되는지 회귀 검증 추가

---

## v0.8.18 (2026-06-26)

### Mac 그래프 한글 폰트 보강
- Matplotlib 차트 폰트 설정이 실제 설치 폰트를 확인한 뒤 적용되도록 개선
- macOS 기본 한글 폰트(`AppleGothic`, `Apple SD Gothic Neo`)와 Noto/Nanum 계열 후보를 우선 탐색
- 한글 폰트가 없을 때는 안정적으로 `DejaVu Sans`로 fallback하고, 음수 기호 깨짐 방지는 유지
- `qa_analysis_smoke.py`에 폰트 설정 회귀 검증 추가
- `SETUP_GUIDE.md`에 Mac 그래프 한글 네모(□) 표시 FAQ와 Noto CJK 설치/확인 방법 추가

---

## v0.8.17 (2026-06-15)

### 자율 작업 기반 + QA 안전망 확장
- [AGENTS.md](AGENTS.md) 신설 — AI 코딩 에이전트용 운영 규칙(불변식·표준 루프·금지 사항·환경). 담당자 없이도 같은 절차로 작업 가능
- [CONTRIBUTING.md](CONTRIBUTING.md) 신설 — 사람 기여자용 5분 시작·기여 흐름·headless 테스트·미러 동기화·PR 체크리스트
- `scripts/qa_viewer_smoke.py` 신설 — DataFrameViewer 검색 필터·클립보드 복사/붙여넣기 headless 검증, `run_all_qa` 7종으로 확대
- README·PROJECT_MAP·REFACTORING_BACKLOG 문서 인덱스·백로그(#10·#11 완료, #12·#13 예정) 동기화
- QA 7종 전체 통과(동작 변경 없음)

---

## v0.8.16 (2026-06-15)

### 점진적 리팩토링 2차 (동작 보존)
- QA 안전망 신설: `scripts/qa_mainwindow_smoke.py` — MainWindow 로드/적용/undo·결측 다이얼로그 미리보기·비동기 로드/KNN 적용을 headless 검증
- 의존성 UI 게이트 일원화: `df_tool/qt_dependency.py`(`gate_widget`·`gate_combo_item`·`require`)로 활성/비활성+경고 통합
- `qt_data_dialogs`: 참조 파일 로드/라벨 표시를 `_prompt_load_reference`·`_set_ref_file_label`로 공통화(VLOOKUP·조인·병합)
- `operations.py` 도메인 분할: KNN/MICE → `ops_impute.py`, 이상치(IQR/Z/IF) → `ops_outliers.py` (operations에서 re-export해 import 경로 100% 호환, 순환 import 안전)
- MainWindow 비동기 통합: `df_tool/qt_async.py`의 `AsyncPoller`로 파일 로드·결측 채우기 폴링 로직 일원화(stale 토큰 검사 보존)
- 기술 부채 보드(`REFACTORING_BACKLOG.md`) #4·#6·#7·#8·#9 완료 반영
- QA 6종 전체 통과(동작 변경 없음)

---

## v0.8.15 (2026-06-15)

### 유지보수성·문서 정리 (기술 부채 1차)
- 자동 진단으로 복잡도·중복·문서 불일치·결합도·테스트 공백·미러 부채 6축 점검
- 초심자용 [ARCHITECTURE.md](ARCHITECTURE.md)(3층 구조·의존성 규칙·요청 흐름·용어사전) 신설
- 기술 부채 추적용 [REFACTORING_BACKLOG.md](REFACTORING_BACKLOG.md)(애자일 점진 리팩토링 보드) 신설
- 의존성/설치 안내 문구를 `analysis_deps.feature_requirement_message`로 단일화(4개 파일 하드코딩 제거)
- `help_content.py`의 "40열 초과 시 보이는 열만" 구버전 설명을 네이티브 전체 가로 스크롤로 정정
- `grid/model.py` `MAX_DATA_COLUMNS` 의미 주석화(10,000열 초과 전용 윈도우 페이지 크기)
- `scripts/github_publish.py`가 `github_upload` 미러를 제외하도록 보강(중복 트리 업로드 방지)
- `scripts/sync_mirror.py` 신설 — 본체를 SSOT로 `github_upload` 미러를 자동 동기화(`--check` 드라이런)하고, 어긋났던 미러를 본체 기준으로 일괄 동기화
- 차트 보일러플레이트 정리: `MplCanvas.begin_chart()`/`finish_chart()` + `_sample_label_text()`로 `qt_analysis_panel`의 반복 코드 통합(동작 보존)
- README·PROJECT_MAP 문서 인덱스에 신규 문서 연결, DEVELOPER_GUIDE 중복 행 정리, 코드 작성 규칙에 미러 동기화 단계 추가
- QA 전체 통과(동작 변경 없음)

---

## v0.8.14 (2026-06-15)

### 의존성 UX 후속 보강
- scikit-learn/scipy 누락이 기본 차트 전체를 막지 않도록 차트 최소 의존성과 고급 분석 의존성 분리
- KNN 미리보기는 scikit-learn 없이도 결측 개수 안내가 가능하므로 계속 활성화
- 단변량 차트 옵션 재구성 후에도 scipy 누락 시 KDE 비활성 상태 유지
- Isolation Forest 직접 실행 경로에 scikit-learn 선제 안내 추가
- 결측 채우기 방식 목록도 scikit-learn 유무에 따라 KNN/MICE 포함 여부를 결정

---

## v0.8.13 (2026-06-15)

### 분석 의존성 UX
- scikit-learn이 없으면 PCA, KNN/MICE, Isolation Forest 관련 버튼·옵션을 비활성화
- scipy가 없으면 단변량 KDE 차트 옵션을 비활성화
- 결측 채우기 다이얼로그에서도 KNN/MICE 선택지를 비활성화하고 설치 안내 툴팁 표시
- 분석 패널 smoke QA에 의존성 상태와 버튼 활성 상태 일치 검증 추가

---

## v0.8.12 (2026-06-15)

### 넓은 표 스크롤 UX 정리
- 추가 열 구간 스크롤바를 제거해 가로 스크롤바가 2개 보이던 문제 해결
- 일반적인 넓은 표는 기본 표 가로 스크롤바 하나로 모든 열을 확인
- 55열 데이터가 전체 55열로 노출되는 회귀 테스트 추가

---

## v0.8.11 (2026-06-15)

### 넓은 표 탐색
- 41열 이상 표에서 뒤쪽 열 접근성을 개선하기 위한 열 구간 탐색을 시도
- v0.8.12에서 디자인 피드백을 반영해 기본 가로 스크롤 하나로 정리

---

## v0.8.10 (2026-05-19)

### CS 예방 하드닝
- 부분 로드 상태에서 원본 경로에 저장하려 할 때 데이터 유실 경고 확인창 추가
- 가공/병합/코드 실행/되돌리기로 데이터가 바뀌면 분석 탭 백그라운드 결과를 무효화
- 무효화된 분석 백그라운드 결과는 작업 로그에 경고로 남기도록 개선
- HTML EDA 리포트에 분포 차트 표본 기준(최대 5,000행)을 명시
- QA에 대용량 열 기준, 리포트 표본 고지, MICE 최소 행 오류 회귀 체크 추가

---

## v0.8.9 (2026-05-19)

### 상태 표시·신뢰성
- 상단 파일 줄에 **부분 로드 / 대용량 / 넓은 표 / 분석 수동** 상태 배지 추가
- 부분 로드 상태는 상태바에도 표시해 저장 전 현재 데이터 범위를 인지할 수 있게 개선
- Excel 시트 전환 시 부분 로드 배지를 해제해 잘못된 상태 표시 방지

---

## v0.8.8 (2026-05-19)

### 운영/CS 예방 UX
- 가공 탭 KNN/MICE 결측 채우기를 백그라운드 처리로 전환
- 작업 중 데이터가 바뀌면 가공 탭 결측 채우기 결과를 폐기
- 대용량 분석 배너에 [지금 그리기] 버튼 추가
- 이상치 제거 적용 전 실제 제거 행 수 확인창 추가

---

## v0.8.7 (2026-05-19)

### PM 리스크 하드닝
- 백그라운드 KNN/MICE/이상치 작업은 DataFrame 복사본으로 실행해 편집 중 동시 접근을 차단
- 작업 실패 콜백도 데이터 변경 토큰을 검사해 오래된 오류 팝업을 무시
- 단·이변량 차트에서 선택 열이 사라진 경우 크래시 대신 안내
- 루트 레거시 분석 `.py` 중복 파일과 `github_upload` 중복 문서 제거

---

## v0.8.6 (2026-05-19)

### 리포트·의존성 UX
- **HTML 리포트 차트 포함** — 결측 비율, 대표 수치 분포, 상관 행렬을 base64 이미지로 내장
- **KDE 안내** — scipy가 없거나 KDE 계산이 실패하면 차트 위에 이유 표시
- **QA 보강** — HTML 리포트 이미지 포함 회귀 검사

---

## v0.8.5 (2026-05-19)

### 안정성·CS 예방
- **KNN/MICE** — 행 2개 미만 시 sklearn 오류 대신 한글 안내 메시지
- **이상치 탭** — 탭 전환 시 자동 미리보기 제거 (멈춤·중복 작업 방지) → [미리보기] 버튼만
- **백그라운드 작업** — 데이터 변경 후 이전 작업 결과 무시 (토큰 검증)
- **HTML 리포트** — 빈 데이터 차단
- **분석 적용** — 중복 `refresh()` 제거

---

## v0.8.4 (2026-05-19)

### 분석 워크플로우 강화
- **HTML EDA 리포트** — 열 개요·결측·상관을 HTML로 저장 (`eda_report.py`, [HTML 리포트] 버튼)
- **PCA** — 다변량 탭 2D 산점도 + 설명 분산 비율
- **MICE 결측 대체** — 분석 탭·가공 결측 다이얼로그 (`fill_na_mice`)
- **대용량 차트** — 8k행/40열 이상 시 자동 전체 차트 생략, [분석 새로고침]으로 강제 갱신
- **진행 표시** — KNN·MICE·이상치 백그라운드 작업 시 헤더 상태 표시

### 문서
- `help_content.py`, `README.md`, `PROJECT_MAP.md`, `DEVELOPER_GUIDE.md` v0.8.3 기능 반영

---

## v0.8.3 (2026-05-19)

### 분석 차트 꾸미기
- **차트 꾸미기** 버튼 — 분석 탭 헤더에서 색·글자·격자·범례·색상맵 조정
- `chart_style.py` — 설정을 `~/.gridloom/chart_style.json`에 저장
- 단변량·이변량 탭 **제목** 입력란 — 차트별 제목 직접 지정
- 색상 10종, 제목/축 글자 크기, 막대·산점도 투명도, 범례 위치, 컬러맵(RdBu_r 등)

---

## v0.8.2 (2026-05-19)

### 트러블슈팅
- **분석 refresh 분리** — 가공 탭 작업 시 `refresh_light()`만 호출 (파일 열기·undo 시 무거운 차트 생략)
- **lazy 차트** — 분석 탭 전환·서브탭 변경 시에만 해당 차트 갱신
- **대용량 EDA** — 8k행/40열 이상 시 차트 지연 안내 (`should_defer_analysis_charts`)
- **의존성 배너** — matplotlib·numpy·scikit-learn·scipy 누락 시 분석 탭 상단 안내 (`analysis_deps.py`)
- **백그라운드 작업** — KNN 적용·이상치 미리보기·이상치 제거를 QThread로 실행 (`qt_analysis_worker.py`)

### 추가 기능
- **EDA 요약 실행** — 개요·단변량·이변량·다변량 대표 차트 원클릭 순회
- **가공 탭 KNN 결측** — `QtFillNaDialog`에서 KNN (k) 선택·미리보기
- **Isolation Forest 이상치** — UI·적용·오염도 파라미터
- **Pair plot** — 다변량 탭, 숫자 열 최대 4개 산점도 행렬

### 의존성
- `scipy>=1.10.0` 추가 (KDE·p-value)

### 테스트
- `qa_analysis_smoke.py` — Isolation Forest, 대용량 지연, 의존성 검사
- `qa_analysis_panel_smoke.py` — 이상치 탭 전환·백그라운드 미리보기 (크래시 회귀 방지)

### 버그 수정
- **이상치 탭 클릭 시 앱 종료** — `self._df or pd.DataFrame()` 불리언 오류 수정
- **백그라운드 작업 크래시** — `QThread`+`moveToThread` → `QThreadPool`+`QRunnable`로 교체 (matplotlib/Qt 메인 스레드 위반 방지)

---

## v0.8.1 (2026-05-19)

### 분석 탭 강화
- **단변량** — 수치: 분산·표준편차·사분위수·범위·IQR 통계표 / 히스토그램·KDE·박스플롯
- **단변량** — 범주: 빈도표·최빈값 / 막대·파이 차트
- **이변량** — 수치×수치·범주×수치·범주×범주별 전용 차트·통계 (상관, 그룹 요약, 교차표)
- **다변량** — 숫자 열 상관 행렬 히트맵 탭 추가

---

## v0.8.0 (2026-05-19)

### 분석 탭 (EDA MVP)
- **네비 3페이지** — 가공(기존 메인) · **분석** · 작업 로그
- **`analysis.py`** — 개요 통계, 차트 추천, 결측·이상치 요약, 플롯 샘플링
- **`qt_analysis_panel.py`** — 개요 / 단변량 / 이변량 / 결측·대체 / 이상치 서브탭
- **matplotlib** 차트 (히스토그램, 박스, 산점도, 교차표 히트맵, 결측 막대)
- **KNN 결측 대체** — `fill_na_knn` (scikit-learn), 미리보기 후 [적용]
- **이상치** — IQR / Z-score, `drop_outlier_rows`, 미리보기 후 행 제거 [적용]

### 의존성
- `matplotlib`, `scikit-learn`, `numpy` (`requirements.txt`)

### 테스트
- `qa_analysis_smoke.py` — EDA 개요, KNN, 이상치, 차트 추천

---

## v0.7.2 (2026-05-19)

### 데이터 가공
- **결측치 채우기** — `fill_na`, `qt_fill_na_dialog` (평균·중앙값·최빈값·ffill/bfill·직접입력)
- **열 가로 병합** — `merge_columns`, Ctrl+다중 열 선택 → 우클릭, 구분자·원본 삭제 옵션
- **열 분리** — `split_column`, 구분자 기준 값 나누기 (`\t` 탭 지원)
- **조인·세로 병합 미리보기** — `QtMergeDialog`, `QtConcatDialog` (VLOOKUP과 동일 레이아웃)

### VLOOKUP
- 동일 키 열 이름 시 값 유실 버그 수정 (`map` 기반 `vlookup`)

### 검색·필터
- **[검색] 버튼** — 입력 즉시 필터 제거, 버튼/Enter로 적용
- **필터 중 Delete** — 열 전체 선택 시 검색에 걸린 행만 내용 지우기
- **필터 중 편집** — 조건에서 벗어난 행도 [검색] 다시 누르기 전까지 목록 유지

### 표·헤더
- **조인 후 새 열 리사이즈** — `replace_dataframe` 구조 판정 수정, `refresh_column_headers`
- **열 헤더 클릭** — 드래그/리사이즈와 클릭 분리, Ctrl+클릭 다중 열 선택 안정화
- **다중 열 선택** — `SelectionController.select_columns`, `columns` 모드

### 정보 패널
- 컬럼명·결측·고유값 **읽기 전용** (타입 열 더블클릭만 타입 변경)
- 결측치 숫자 클릭 → 결측치 채우기 다이얼로그

### UI
- 표 상단 **결측 채우기** 버튼
- `help_content.py` 사용법 갱신

### 테스트
- `qa_operations_smoke.py` — `fill_na`, `merge_columns`, `split_column`, VLOOKUP 동일키 열

---

## v0.7.1 (2026-05-19)

### PyQt 데이터 다이얼로그
- **`qt_data_dialogs.py`** — VLOOKUP(미리보기 포함), 조인(Merge), 세로 병합(Concat), 그룹 요약
- `qt_app.py` — Tk `run_tk_dialog` 의존 제거, 전부 PyQt 네이티브

### 레거시 제거 (Tk 스택)
- 삭제: `gridloom_tk.pyw`, `app.py`, `viewer.py`, `dialogs.py`, `design_settings.py`
- 삭제: `info_panel.py`, `code_panel.py`, `toast.py`, `activity_log.py`, `window_settings.py`, `tk_bridge.py`
- 삭제: `scripts/viewer_interaction_smoke.py`
- `qt_dialogs.py` — `run_tk_dialog` 제거

---

## v0.7.0 (2026-05-19)

### PyQt 표 — Tk 패리티 완성
- **열 헤더 우클릭** — 정렬, 열 선택, 이름 변경, 복제, 채우기, 순차번호, 삭제 등 (`grid/header.py`)
- **열 선택 후 셀 우클릭** — 열 메뉴 유지 (행 메뉴와 분기)
- **열 드래그 재정렬** — 커스텀 드래그, 파란 drop 라인, `reorder_columns` 연동
- **열 드래그 크래시 수정** — `paintEvent` viewport 이중 `QPainter` 제거 (Windows)
- **열 리사이즈 vs 드래그 분리** — 경계 10px는 Qt 리사이즈, 중앙만 드래그
- **붙여넣기** — 스크롤·열 선택 상태 유지

### PyQt 다이얼로그 전환
- `qt_dialogs.py` — 확인, 행/열 추가, 이름 변경, 복제, 순차 채우기, **찾기/바꾸기**, 열 선택
- **Ctrl+F** — PyQt `qt_find_replace_dialog`
- **도움말** — `QtHelpDialog` (Markdown 표시); 닫을 때 Tk `attributes` 크래시 수정
- 메뉴 → 다이얼로그 — `QTimer.singleShot(0, …)` 지연 패턴

### PyQt 디자인 설정
- **`qt_design_settings.py`** — 탭별 색상 편집, 미리보기, 기본값 복원, `theme.json` 저장
- `MainWindow.show_design_settings()` — Tk `DesignSettingsWindow` 대신 PyQt 사용
- `refresh_theme()` — 툴바·네비·패널 stylesheet 갱신

### 문서 전면 재작성
- `README.md` — 문서 인덱스
- `LEARNING_GUIDE.md` — 초보자 코드 공부 가이드 (신규)
- `DEVELOPER_GUIDE.md` — PyQt 기준 기능 추가 가이드 (재작성)
- `CODING_STANDARDS.md` — 코드 작성 규칙 (신규)
- `PROJECT_MAP.md` — PyQt 아키텍처 지도 (재작성)
- `MIGRATION_QT.md` — 완료/남은 항목 갱신

### 테스트
- `scripts/grid_smoke.py` — 헤더, 열 재정렬, 열 선택 컨텍스트
- `scripts/run_all_qa.py` — 전체 통과

### 아직 Tk (`run_tk_dialog`)
- VLOOKUP, 조인(Merge), 병합(Concat), 그룹 요약 다이얼로그

---

## v0.6.2 (2026-05-19)

### 버그 수정 · 기능 패리티 (Tk → PyQt)
- **열/행 추가·삭제가 표에 안 보이던 문제** — 구조 변경 시 `GridModel` 전체 동기화 (`restructure=True`)
- 열 추가 시 **이름 입력 다이얼로그** (Tk와 동일)
- 행 추가 시 **개수 입력 다이얼로그**

### Tk viewer 기능 이식
- 뷰어 **액션 툴바**: +참조, VLOOKUP, 조인, 병합, 그룹, 결측/중복 제거, +열
- **열 헤더 우클릭**: 정렬, 열 선택, 이름 변경, 복제, 열 추가, 채우기, 순차번호, 열 삭제, 복사/붙여넣기
- **행 헤더 우클릭**: 행 추가, 행 삭제
- **셀 우클릭**: 편집, 행 선택, 행 추가/삭제, 복사/붙여넣기
- 단축키: Ctrl+A, Ctrl+Space, Shift+Space, 방향키 이동
- `sort_by`, `clear`, `replace_dataframe` API
- 원본 복원 버튼 (그룹 요약 후)

---

## v0.6.1 (2026-05-19)

### 버그 수정
- **셀 편집 표시 안 됨** — `set_cell_value` 후 `GridModel`이 갱신되지 않던 문제 (`replace_dataframe` 동기화)
- **저장 다이얼로그 안 뜸** — Tk+PyQt 혼합 시 창이 뒤에 가려지던 문제 → **PyQt 네이티브 `QtSaveAsDialog`**
- 기타 Tk 다이얼로그 — `run_tk_dialog`로 PyQt 이벤트 루프와 함께 표시

### 기능 보완 (PyQt)
- **Ctrl+C / Ctrl+V** — Excel 형식 복사·붙여넣기
- **열 헤더 클릭** — 열 전체 선택 / **더블클릭** — 정렬
- **행 헤더 클릭** — 행 전체 선택
- 표 단축키: Ctrl+Shift+방향키(행·열 삽입), Ctrl+Shift+N(열 추가)
- 우클릭 메뉴 **열 삭제**
- 선택값 패널 — 포커스 나갈 때만 반영 (Tk와 동일)
- 코드 패널 **Ctrl+Enter** 실행

---

## v0.6.0 (2026-05-19)

### PyQt6 표 엔진 (기본 실행)
- **`df_tool/grid/`** — `GridModel` / `GridView` / `GridCellDelegate` / `SelectionController` 신규
- **`df_tool/qt_viewer.py`** — Tk `DataFrameViewer`와 동일 public API의 PyQt Facade
- **`df_tool/qt_app.py`** — PyQt `MainWindow` (파일 I/O·undo·사이드바·작업 로그)
- **`gridloom.pyw`** — PyQt6 엔트리로 전환
- **`gridloom_tk.pyw`** — Tkinter 레거시 엔트리 유지
- **`df_tool/selection.py`** — `SelectionScope` Tk/Qt 공용 분리
- **`df_tool/tk_bridge.py`** — 복잡 다이얼로그(저장·VLOOKUP 등) 기존 Tk 재사용
- **`requirements.txt`** — `PyQt6>=6.6.0` 추가
- **`MIGRATION_QT.md`** — 파일별 변경·아키텍처·롤백 방법
- **`scripts/grid_smoke.py`** — headless GridModel smoke

### 성능
- Treeview + Frame 오버레이 제거 → QTableView viewport 가상화
- 격자선·활성 셀 테두리를 delegate paint로 처리 (DOM 위젯 0개)

---

## v0.5.3 (2026-05-19)

### 성능
- 스크롤·드래그 시 격자/하이라이트 **디바운스** (Frame 매번 destroy → 풀 재사용)
- 스크롤 중 `update_idletasks`·헤더/태그 갱신 생략 → **가벼운 visual 오버레이**만
- 드래그 선택 중 하이라이트만 20ms 스로틀, 라벨은 mouseup 시 갱신
- 셀 편집 중 Treeview 실시간 갱신 제거 (커밋 시 반영)
- info 패널 갱신 350ms 디바운스 (연속 편집 시 부하 감소)
- 스크롤 렌더 지연 12ms → 8ms

### 버그 수정 · 안정화
- HTML 위장 `.xls`(고도몰 등) — 정수 열명(`0`,`1`…) 파일에서 셀 클릭·하이라이트·편집 불가 수정
- 열 `0` falsy 처리 버그 수정 (`if column:` → `if column is not None:`)
- 로드 시 비문자열 열명을 문자열로 자동 정규화 (`loader._normalize_dataframe_columns`)
- `operations` 전반에 `resolve_column_key` 적용 (정렬·열 이동·찾기/바꾸기·VLOOKUP 등)
- 표 **셀 경계선** 추가 (`cell_grid` 색상, 디자인 설정에서 조절)
- 넓은 표 모드: 다중 셀 하이라이트 상한 적용 (활성 셀만 표시)
- QA smoke 테스트 추가 (`qa_operations_smoke`, `qa_loader_smoke`, `run_all_qa`)

### UX
- Delete/Backspace: 행·열 구조 삭제 X, **내용만** 지우기 (구조 삭제는 우클릭)
- 성공 토스트 제거 → 작업 로그만 기록, 실패·경고만 토스트
- 방향키 이동 시 화면 밖 셀 자동 스크롤 추적
- 삭제 확인창 Enter로 확인

---

## v0.5.0 (2026-05-19)

### 리브랜딩 · UI
- 프로그램명 **Gridloom**(그리드룸)으로 변경 · 실행 파일 `gridloom.pyw`
- 설정 폴더 `~/.gridloom/` (이전 `~/.dataframe_tool/` 설정 자동 인식)
- **!** 도움말 툴팁이 화면 밖으로 나가지 않도록 자동 줄바꿈·위치 조정

---

## v0.4.5 (2026-05-19)

### 수정내용 추가

#### 화면 · 작업 로그
- **[메인] / [작업 로그]** 페이지 전환 — [보기] 메뉴에서도 이동
- 파일을 연 세션 동안 작업 기록 (시간·완료/실패/알림·상세)
- 새 파일 열기 시 로그 초기화 · [로그 지우기] 버튼

#### 알림
- 작업 완료·실패 시 우하단 토스트 알림

---

## v0.4.4 (2026-05-19)

### 수정내용 추가

#### 선택 · 편집
- **열 전체 / 행 전체** 선택 후 Delete·Backspace로 내용 일괄 지우기

#### 디자인 설정
- **[도움말 > 디자인 설정]** — 배경·글자·표·코드 패널 색상 세부 조절
- 미리보기 · 탭별 설정 · 기본값 복원 · 설정 파일 저장 (`~/.dataframe_tool/theme.json`)

---

## v0.4.3 (2026-05-19)

### 수정내용 추가

#### 데이터 정보
- **타입** 열 클릭 → 드롭다운에서 문자·정수·실수·논리·날짜로 변경
- 변경 후 표·실행 취소(Ctrl+Z) 반영

---

## v0.4.2 (2026-05-19)

### 수정내용 추가

#### 버그 수정
- 가로 스크롤 시 선택 셀 하이라이트·편집창이 고정되어 따라다니던 문제 수정

#### 그룹 요약
- 그룹 요약 적용 후 **[원본 복원]** 버튼으로 요약 전 데이터로 되돌리기

#### UI
- 주요 버튼·옵션 옆 **!** 아이콘 — 마우스를 올리면 사용 설명 표시

---

## v0.4.1 (2026-05-19)

### 수정내용 추가

#### 열 순서
- **열 헤더 드래그**로 열 순서 변경 (파란 세로선으로 삽입 위치 표시)
- 변경 후 실행 취소(Ctrl+Z) 가능

---

## v0.4.0 (2026-05-19)

### 수정내용 추가

#### 셀 편집
- 셀 **더블클릭** 또는 **같은 셀 빠른 두 번 클릭**으로 인라인 편집 (보라색 테두리 + 커서)
- 타이핑 시 표 셀·상단 미리보기 **실시간 반영**
- **Enter** → 저장 후 **아래 행** 같은 열로 이동·편집 계속
- **Shift+Enter** → 위 행으로 이동
- **Tab / Shift+Tab** → 옆 열로 이동
- **F2 / F12** → 선택 셀 편집
- **Esc** → 편집 취소
- 저장 후 **스크롤 위치 유지** (아래쪽 데이터 수정해도 맨 위로 튀지 않음)

#### 검색 · 위치 표시
- 검색창 비우고 **대상 열**만 지정 후 검색 → 해당 열 **공백(결측)** 행만 표시
- **제외** 체크 시 → 값이 **있는** 행만 표시
- 필터 결과에서도 **원본 행·열 번호** 표시
  - 표 `행#` 열: 원본 기준 1부터 번호
  - 선택 정보: `47행 3열 · 열이름 · 필터 12행` 형식
  - 하단 상태: `1–20 / 50행 · 전체 1,000행 · 'A' 공백` 형식

#### VLOOKUP
- **별도 창**에서 참조 파일 불러오기 (사전에 참조 파일 등록 불필요)
- 키 열·가져올 열·결과 열 이름 설정
- **미리보기** (상위 50행, 매칭/미매칭 건수)
- 설정 변경 시 미리보기 자동 갱신

---

## v0.3.0 (2026-05-19)

### 수정내용 추가

#### 검색
- 검색어 입력 후 **[검색]** 버튼 또는 Enter로만 적용 (입력 중 자동 필터 제거)
- **[전체 보기]** → 검색 UI 초기화 + 전체 데이터 표시 (편집 내용은 유지)
- **완전일치** / **제외** / **대상 열** 옵션
- 빈 검색 + 대상 열 → 결측치 필터

#### 선택 · 편집
- 셀 클릭 시 **선택 값 미리보기** 패널 (직접 수정 가능)
- **Delete / Backspace** → 선택 셀 내용 지우기
- **Ctrl+C** → 값만 복사 (열 이름 제외)
- Canvas 하이라이트로 선택 셀 표시 (정렬·스크롤과 분리)

#### 실행 취소
- 데이터 변경 시 **Ctrl+Z** 실행 취소 (최대 20단계)
- Python 코드 패널 **되돌리기** 버튼 (실행 직전 상태 복원)

#### UI
- **다크 모드** 테마
- 헤더 내 **커스텀 메뉴** (Menubutton)
- 표 : 코드 패널 = **7 : 3** 비율
- 콤보박스·메뉴 스타일 통일

---

## v0.2.0 (2026-05-19)

### 수정내용 추가

#### 성능
- **가상 스크롤** (화면에 보이는 행만 렌더, 약 20행 단위)
- 연속 스크롤 (페이지 버튼 제거, 마우스 휠·스크롤바)
- 검색 **디바운스** (입력 후 일정 시간 뒤 적용 — 이후 v0.3에서 버튼 방식으로 변경)
- undo 시 `df.copy()` 최적화

#### 표시
- 행 번호 열, 정렬 표시 (▲/▼)
- 정보 패널 컬럼 너비 조정

---

## v0.1.0 (초기)

### 기본 기능
- CSV / Excel 등 파일 열기·저장 (다양한 인코딩·형식)
- 데이터 표 보기 (Treeview)
- 열/행 추가·삭제, 찾기 및 바꾸기
- VLOOKUP, Merge, Concat, 그룹 요약 (참조 파일 방식)
- Python 코드 패널 (`df` 변수로 실행)
- 시트 선택 (Excel 다중 시트)
