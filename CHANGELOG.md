# Gridloom — 변경 기록

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
