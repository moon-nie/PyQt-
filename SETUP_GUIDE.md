# Gridloom — 설치 · 실행 가이드 (Windows / Mac)

초보자도 따라 할 수 있도록 **처음부터 끝까지** 적었습니다.  
Windows와 Mac **둘 다** 같은 Python 프로그램이라, 설치 방법만 OS별로 다릅니다.

---

## 0. 이 프로그램이 뭔가요?

- **Gridloom** = CSV, Excel(.xls/.xlsx), Parquet 등 **표 데이터**를 열어서
  - 엑셀처럼 보고·편집하고
  - Python 코드로 가공할 수 있는 **데스크톱 프로그램**입니다.
- 인터넷 없이 **내 PC에서만** 돌아갑니다.
- 실행 파일: 프로젝트 폴더의 **`gridloom.pyw`**

---

## 1. 필요한 것 (공통)

| 항목 | 설명 |
|------|------|
| **Python 3.10 이상** | 3.11, 3.12, 3.13 권장 |
| **프로젝트 폴더** | `Gridloom` 폴더 전체 (코드 + `requirements.txt`) |
| **패키지** | pandas, openpyxl, xlrd 등 (`requirements.txt`에 목록) |

> Mac도 Windows도 **Python + pip** 만 있으면 실행 가능합니다.

---

## 2. Windows — 처음 설치하기

### 2-1. Python 설치 확인

1. 키보드 **`Win + R`** → `cmd` 입력 → Enter  
2. 검은 창(명령 프롬프트)에 아래 입력 후 Enter:

```cmd
python --version
```

- `Python 3.10.x` 이상이 나오면 → **2-2로**
- `'python'은(는) 내부 또는 외부 명령...` 이라고 나오면 → Python 설치 필요

**Python 설치 (Windows)**

1. https://www.python.org/downloads/ 접속
2. **Download Python 3.x** 클릭
3. 설치 시 **맨 아래 `Add python.exe to PATH` 반드시 체크** ✅
4. Install Now
5. 설치 후 **cmd를 새로 열고** 다시 `python --version` 확인

> `python` 대신 `py`만 되는 PC도 있습니다. 그때는 아래 명령에서 `python` → `py` 로 바꿔 쓰세요.

---

### 2-2. 프로젝트 폴더로 이동

예: 바탕화면의 `Gridloom` 폴더라면

```cmd
cd Desktop\Gridloom
```

경로가 다르면 탐색기에서 `Gridloom` 폴더 주소창을 클릭 → 복사 → cmd에:

```cmd
cd 붙여넣은경로
```

---

### 2-3. 패키지 설치 (최초 1회, 업데이트 후에도 1회)

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

에러 없이 끝나면 OK.

**`.xls` (구형 Excel) 파일**을 열려면 위 명령이 꼭 필요합니다.  
(`python-calamine`, `xlrd`, `openpyxl` 등이 함께 설치됩니다.)

---

### 2-4. 실행 방법 (Windows)

**방법 A — 더블클릭 (일반 사용)**

- `Gridloom` 폴더에서 **`gridloom.pyw`** 더블클릭

**방법 B — cmd에서 실행 (에러 확인용, 추천)**

```cmd
cd Desktop\Gridloom
python gridloom.pyw
```

에러가 나면 **빨간 글씨 메시지**가 cmd에 남습니다. 그 내용을 복사해 두면 문제 해결에 도움이 됩니다.

**방법 C — pythonw (창 없이 실행, 더블클릭과 비슷)**

```cmd
pythonw gridloom.pyw
```

---

## 3. Mac — 처음 설치하기

### 3-1. Python 설치 확인

1. **`Cmd + Space`** → `터미널` 또는 `Terminal` 검색 → 실행
2. 입력:

```bash
python3 --version
```

- `Python 3.10` 이상 → **3-2로**
- 없거나 3.9 이하 → 아래 설치

**Python 설치 (Mac)**

- **공식**: https://www.python.org/downloads/macos/ 에서 설치
- 또는 Homebrew 사용:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python
```

Mac에서는 명령어가 **`python3`**, **`pip3`** 인 경우가 많습니다.

---

### 3-2. 프로젝트 폴더로 이동

```bash
cd ~/Desktop/Gridloom
```

(폴더 위치에 맞게 경로 수정)

---

### 3-3. 패키지 설치 (최초 1회)

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

---

### 3-4. 실행 (Mac)

**터미널에서 (에러 확인용)**

```bash
cd ~/Desktop/Gridloom
python3 gridloom.pyw
```

**더블클릭**

- Finder에서 `gridloom.pyw` 더블클릭  
- 안 열리면: 파일 우��릭 → **연결 프로그램** → Python Launcher / python3

**Mac 첫 실행 시**

- “확인되지 않은 개발자” 경고 → **시스템 설정 → 개인정보 보호 및 보안** 에서 허용

---

## 4. Windows / Mac 공통 — 잘 되는지 테스트

1. 프로그램 실행
2. 상단 **[열기]** 클릭
3. 프로젝트 안의 **`sample_data.csv`** 선택
4. 표에 데이터가 보이면 **설치 성공** ✅

---

## 5. 자주 하는 질문 (FAQ)

### Q. `pip` / `pip3` 명령이 없대요

```cmd
python -m pip install -r requirements.txt
```

Mac:

```bash
python3 -m pip install -r requirements.txt
```

### Q. `.xls` 파일이 안 열려요

```cmd
python -m pip install python-calamine xlrd openpyxl
```

설치 후 **프로그램을 완전히 종료**했다가 다시 실행하세요.

### Q. 더블클릭하면 잠깐 깜빡이고 꺼져요

**cmd/터미널**에서 실행해 에러를 확인하세요:

```cmd
python gridloom.pyw
```

### Q. Mac에서 tkinter 관련 에러

Python 공식 설치본을 쓰거나:

```bash
brew install python-tk@3.12
```

(본인 Python 버전에 맞게)

### Q. 설정/테마는 어디 저장되나요?

| OS | 경로 |
|----|------|
| Windows | `C:\Users\사용자이름\.gridloom\` |
| Mac | `/Users/사용자이름/.gridloom/` |

`theme.json`, `window.json` 등이 있습니다.

### Q. Windows와 Mac에서 파일 호환?

- **데이터 파일** (csv, xlsx 등): 동일하게 열립니다.
- **프로그램 코드**: 같은 `Gridloom` 폴더를 쓰면 동일하게 동작합니다.
- **단축키**: Mac에서 Ctrl → **⌘ Command** 로 바꿔 생각하면 됩니다 (일부는 Ctrl 그대로).

---

## 6. 매일 쓸 때 요약

| OS | 한 줄 실행 |
|----|-----------|
| Windows | `cd Gridloom폴더` → `python gridloom.pyw` |
| Mac | `cd Gridloom폴더` → `python3 gridloom.pyw` |

코드 수정 후 / `requirements.txt` 변경 후:

```text
python -m pip install -r requirements.txt   (Windows)
python3 -m pip install -r requirements.txt (Mac)
```

---

## 7. 다음에 읽을 문서

| 문서 | 내용 |
|------|------|
| **PROJECT_MAP.md** | 파일마다 뭐가 있는지, 함수가 어디서 어디로 연결되는지 |
| **DEVELOPER_GUIDE.md** | 기능 추가 방법 (복사해서 확장) |
| 앱 내 **도움말 → 사용법** | 일반 사용자용 단축키·조작 |

---

## 8. 문제 해결 체크리스트

- [ ] Python 3.10+ 설치됨 (`python --version` / `python3 --version`)
- [ ] `Gridloom` 폴더에서 `pip install -r requirements.txt` 실행함
- [ ] `sample_data.csv`로 열기 테스트함
- [ ] `.xls` 문제 시 `python-calamine`, `xlrd` 재설치함
- [ ] 에러 시 cmd/터미널에서 `python gridloom.pyw` 로 메시지 확인함

여기까지 했는데도 안 되면, **에러 메시지 전체**와 **OS(Windows/Mac)** 를 알려주세요.
