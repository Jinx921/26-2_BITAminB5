# BITAmin B5 - 2026 빅콘테스트 (AI데이터 활용 부문)

## 1. 프로젝트 소개

**사회적 고립 대응 AI 에이전트 개발** </br>
SK 통신 유동인구와 신한카드 소비 데이터로 어르신의 낮 외출이 줄어든 동네를 찾고, **어떤 도움을 어떻게 줄지까지 계산해 제안한다.**
"사람을 시설로 연결할지 · 서비스를 동네로 보낼지"를 비교하고, AI 답변은 엔진이 계산한 숫자만 인용하도록 코드가 검증해 신뢰도를 붙인다.
관리자에게는 우선 확인 동네와 문서 초안을, 현장 인력에게는 확인 목록을, 시민에게는 위험 판정 없이 갈 곳과 함께 가기 요청을 제공한다.

- 대상 지역: 서울 강남구 · 강원 춘천시 (2025-07 ~ 2025-12)
- 판단 단위: 개인이 아니라 **동네(250m 격자)**. "누구"가 아니라 "어느 동네를 먼저 확인할지"를 짚는다.
- 사용자: 관리자(구청·주민센터 담당자) · 현장 인력(통·이장, 생활지원사) · 시민(주민·가족)
- 최종 결정은 항상 담당자가 한다.

## 2. 팀원 및 역할

| 이름 | 개발 담당 | 외부 데이터 수집·EDA |
| --- | --- | --- |
| 현준 | 분석 엔진 (`engine/`) | 주민등록 연령별 인구 및 1인가구, 건축물대장 |
| 혜진 | AI 에이전트 (`agent/`) | 사회적 기회 자원 (사회복지시설, 도서관, 체육·문화시설 등) |
| 채원 | 백엔드 (`backend/`) | 복지 데이터 (건강증진센터, 마을회관·경로당) |
| 사랑 | 프론트엔드 (`frontend/`) | SGIS 격자 인구와 가구 |

제공 데이터(SK 유동인구 · 신한카드) EDA는 네 명이 각자 진행했고, [`docs/team_eda_merged.md`](docs/team_eda_merged.md)에 하나로 합쳤다.

## 3. 주요 기능

| 사용자 | 할 수 있는 것 |
| --- | --- |
| 관리자 (구청·주민센터 담당자) | 어디부터 확인할지 (고립 유형 지도·신뢰도), 이동형 거점 배치, 시설 폐쇄 영향, 개입안 비교 차트, 현장 확인 목록, 사업 제안서·현황 보고·주민 안내문 초안 |
| 현장 인력 (통·이장, 생활지원사) | 확인 목록을 방문 순서대로 보고 동네별 확인 질문에 답해 저장 |
| 시민 (주민·가족) | 찾을 위치 주변의 갈 곳(시설·주소·거리·활동 시간대), 함께 갈 이웃 찾기·이동 도움 요청 |

시민 화면에는 위험 판정과 고립 유형을 보여주지 않는다. (관리자 전용)

## 4. 구조

![에이전트 구조](agent/docs/에이전트_구조.png)

| 층 | 폴더 | 하는 일 | 상세 |
| --- | --- | --- | --- |
| 데이터·EDA | `src/`, `notebooks/`, `preprocessed/`, `outputs/` | 원천 데이터 로딩, EDA, 250m 격자 전처리 | [`docs/`](docs/) |
| 분석 엔진 | `engine/` | 후보 찾기·유형 분류·배치 시뮬레이션·강건성 등 도구 8개. 같은 입력이면 같은 결과 | [`engine/README.md`](engine/README.md) |
| AI 에이전트 | `agent/` | 질문 해석 → 엔진 도구 호출 → 답변 검증 → 화면 조각(JSON) | [`agent/README.md`](agent/README.md) |
| 백엔드 | `backend/` | 질문·로그인·지도·지원 요청·현장 기록 API (FastAPI) | [`backend/README.md`](backend/README.md) |
| 프론트엔드 | `frontend/` | 관리자 웹, 시민 웹(모바일 우선), 현장 모바일 화면 | [`frontend/README.md`](frontend/README.md) |

## 5. 기술 스택

| 영역 | 사용 기술 |
| --- | --- |
| 데이터·분석 엔진 | Python 3.12, pandas, numpy, scipy(배치 최적화), pyproj, geopandas |
| AI 에이전트 | Claude Sonnet 5.5 (Anthropic API, tool use) |
| 백엔드 | FastAPI, SQLite, JWT, Argon2 |
| 프론트엔드 | Vite, React 19, TypeScript, TanStack Query, Tailwind CSS, react-leaflet(OpenStreetMap) |

## 6. 실행 방법

저장소 루트에서 실행한다. 각 단계의 자세한 설정은 위 표의 README를 확인한다.

```bash
# 1) Python 환경 (데이터·엔진·에이전트·백엔드)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r backend/requirements.txt   # backend는 agent·engine 의존성을 포함한다.

# 2) 백엔드 (http://127.0.0.1:8000, 문서 /docs)
#    실제 질문 답변에는 agent/.env의 ANTHROPIC_API_KEY가 필요하다.
uvicorn backend.app.main:app --reload

# 3) 프론트엔드 (http://localhost:5173, Node 20.19 이상)
cd frontend && npm install && npm run dev
```

```bash
# 테스트 (API 키 없이 동작)
python -m pytest agent/tests engine/tests backend/tests -q
cd frontend && npm run typecheck && npm run lint && npm run build
```

### 분석 코드

주피터에서는 커널 **Python (BITAmin B5)** 을 고른다. (`python -m ipykernel install --user --name bitamin-b5`) </br>
노트북 첫 셀에서 `src` 를 경로에 추가한다.

```python
import sys; sys.path.insert(0, "../src")

from loaders import load_sk, load_shinhan

age = load_sk("flow_age_pop", months=["202507"])   # 중복 제거된 상태로 반환
mct = load_shinhan("mct")   # 데이터1 — 시간대(TIME_GB) 있음, 법인 포함
cln = load_shinhan("cln")   # 데이터2 — 고객 거주지(CLN_SGG_CD) 있음, 법인 제외
```

인코딩/구분자는 `src/config.py` 에만 둔다. 직접 `pd.read_csv` 하지 말 것. </br>
(`src/loaders.py` 의 이름은 표준 라이브러리 `io` 와 충돌하지 않도록 고른 것 - `src/io.py` 로 두면 `import pandas` 가 깨진다.)

## 7. 데이터

| 구분 | 데이터 | 단위 |
| --- | --- | --- |
| 제공 | SK 통신 유동인구 (연령·시간대·요일별) | 50m 격자 → 팀 표준 **250m 격자**, 월별 일평균 |
| 제공 | 신한카드 소비 (데이터1: 시간대 / 데이터2: 고객 거주지) | 시군구 |
| 외부 | SGIS 격자 인구·가구, 주민등록 인구·1인가구, 건축물대장 | 격자, 행정동 |
| 외부 | 복지시설(경로당·마을회관·보건기관), 사회적 기회 자원(도서관·공공체육·문화시설) | 시설 좌표 |

- 원천 데이터(`data/`, 약 350MB)와 `submissions/`는 git에 올라가지 않는다. 전처리 결과(`preprocessed/`)와 EDA 산출물(`outputs/`)은 커밋된다.
- 데이터 해석 규칙(중복 행, 카드 데이터2 재배포본, 좌표계, 격자 단위 등)은 [`docs/data_interpretation.md`](docs/data_interpretation.md)를 먼저 읽는다.

## 8. 문서 안내

| 문서 | 내용 |
| --- | --- |
| [`agent/docs/에이전트_설계.md`](agent/docs/에이전트_설계.md) | 에이전트 설계 - 두 모드 (관리자: 담당자·현장 인력 / 시민), 고립 유형, 차별점, 구조 |
| [`engine/JSON_규격.md`](engine/JSON_규격.md) | 분석 엔진 도구 응답 형식 |
| [`engine/지도_규격.md`](engine/지도_규격.md) · [`engine/현장기록_규격.md`](engine/현장기록_규격.md) | 지도 레이어 · 현장 확인 기록 형식과 판정 반영 규칙 |
| [`docs/api-contract.md`](docs/api-contract.md) | 백엔드 API 요청과 응답 형식 |
| [`docs/demo-checklist.md`](docs/demo-checklist.md) | 시연 체크리스트 |
| [`docs/team_eda_merged.md`](docs/team_eda_merged.md) | 팀 EDA 통합본 - 제공/외부 데이터, 충돌 정리 |
| [`docs/data_interpretation.md`](docs/data_interpretation.md) | 분석 전 합의할 해석 규칙 |
| [`docs/EDA_summary.md`](docs/EDA_summary.md) | 원천 데이터 관측 결과 |
| [`docs/EDA_srh.md`](docs/EDA_srh.md) | 사회적 고립 신호 EDA (거주셀과 후보셀) |
| [`docs/external_data.md`](docs/external_data.md) | 외부 데이터 수집·판정·전처리·EDA |
| [`docs/data_integration.md`](docs/data_integration.md) | 데이터 간 연결 전략과 그 한계 |
