# BITAmin B5 — 2026 빅콘테스트

SK 통신 유동인구 + 신한카드 소비 데이터 기반 분석 프로젝트.

## 구조

```
data/raw/sk_flow_pop/         # SK 유동인구 CSV 18개 ('|' 구분, UTF-8 BOM)
data/raw/shinhan_card/        # 신한카드 txt 2개 (탭 구분, CP949)
data/_zip/                    # 원본 배포 zip 보관 (git 제외)
src/config.py                 # 경로 · 인코딩 · 구분자 상수
src/loaders.py                # 원천 데이터 로더 (202512 중복 자동 제거)
src/eda.py                    # EDA 표 35개 계산 로직
notebooks/run_eda.py          # 실행 → 터미널 출력 + outputs/ 갱신
notebooks/build_report.py     # 템플릿 + manifest → HTML 리포트
notebooks/report_template.html
docs/                         # 해석 가이드 · 결과 요약
outputs/                      # EDA 산출물 (표 CSV · HTML 리포트) — 커밋된다
preprocessed/                 # 전처리 결과 parquet — 커밋된다
```

`preprocessed/` 내용:

| 파일 | 크기 | 내용 |
| --- | --- | --- |
| `card_clean.parquet` | 983,413행 × 13열 | 카드 데이터1 정제 (법인 제외, `age`·`ticket`·`is_social` 파생) |
| `flow_cell.parquet` | 48,546행 × 50열 | 격자 단위 집계 (`peer` 그룹, `dev_*` 이탈 지표, `trend`) |

`data/` 와 `submissions/` 는 git에 올라가지 않는다 (원천 데이터 ~350MB).

`interim` / `processed` / `external` 경로는 `config.py` 에 상수로만 정의돼 있고 실제로 쓰는 시점에 생긴다
(`loaders.cache()` 는 저장할 때 알아서 만든다). 빈 폴더를 미리 두지 않는다.

## 문서

| 문서 | 내용 |
| --- | --- |
| `docs/team_eda_merged.md` | **팀 5인 EDA 통합본** — 제공/외부 데이터, 충돌 정리 |
| `docs/data_interpretation.md` | 분석 전 합의할 해석 규칙 — **먼저 읽을 것** |
| `docs/EDA_summary.md` | 원천 데이터 관측 결과 |
| `docs/external_data.md` | 외부 데이터 수집·판정·전처리·EDA |
| `docs/data_integration.md` | 데이터 간 연결 전략과 그 한계 |
| `outputs/eda_report.html` | 표 35개 + 차트 24개. `open outputs/eda_report.html` |
| [같은 페이지 온라인 링크](https://claude.ai/artifact/QtLETb7adVcx7M9HWCgSNj) | Claude Artifact. 기본 비공개이므로 공유 설정 필요 |

표 원본은 `outputs/tables/*.csv` (UTF-8 BOM, 엑셀에서 바로 열림).

```bash
python3 notebooks/build_grid_access.py  # 250m 격자 × 자원 접근성
python3 notebooks/eda_external.py       # 외부 데이터 EDA
python3 notebooks/run_eda.py            # 표 35개 + manifest 재생성
python3 notebooks/build_report.py       # manifest → HTML 리포트
```

## 세팅

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

주피터에서는 커널 **Python (BITAmin B5)** 를 고른다 (`python -m ipykernel install --user --name bitamin-b5`).

현재 환경: Python 3.12.5 / pandas 3.0.5 / numpy 2.5.3 / geopandas 1.1.4 / lightgbm 4.7.0

## 백엔드 서버

FastAPI 서버는 루트 `.venv`를 사용하며 의존성은 별도 파일로 관리한다. 저장소 루트에서 실행한다.

```bash
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

서버 실행 후 `http://127.0.0.1:8000/docs`에서 Swagger 문서를 확인할 수 있다.
실제 Anthropic 호출에는 `agent/.env`의 API 키가 필요하다. 테스트는 mock으로 실행하며 API 키를 요구하지 않는다.
프론트엔드는 같은 로컬 환경에서 기본 허용 주소(`http://localhost:5173`, `http://localhost:3000`)를 사용할 수 있다.
프론트 개발 주소가 정해지면 `BACKEND_ALLOWED_ORIGINS`에 쉼표로 구분해 지정한다.
예: `export BACKEND_ALLOWED_ORIGINS="http://localhost:5173,https://<FRONTEND_HOST>"`.
운영 환경에서는 명시적인 주소가 필수이며 `*` 와일드카드는 거부된다. CORS credentials는 허용하지 않는다.
API 계약은 [`docs/api-contract.md`](docs/api-contract.md)에 정리되어 있다.

```bash
python -m pytest backend/tests -q
python -m pytest agent/tests -q
```

설정은 `BACKEND_APP_NAME`과 `BACKEND_LOG_LEVEL` 환경 변수로 지정할 수 있다.
기본 로그 레벨은 `INFO`이며 요청 로그는 JSON 형식으로 출력된다.
SQLite 파일은 기본 `backend/data/app.db`에 생성되며 `BACKEND_DB_PATH`로 경로를 바꿀 수 있다.
DB와 `backend/data/`는 Git에서 제외된다.
production에서는 `BACKEND_ENVIRONMENT=production` 및 `BACKEND_JWT_SECRET` 설정이 필수이며,
키가 없으면 서버가 시작되지 않는다. development에서는 임시 키를 프로세스 시작 시 생성한다.

### 질문 API 사용량 제한

질문 API는 로그인한 사용자 ID만으로 SQLite에 최근 요청 시각을 기록해 사용자별 rolling-window 제한을 적용한다.
질문 원문, 위치, 토큰 또는 응답은 제한 기록이나 로그에 저장하지 않는다.
development 기본값은 시민 60초당 10회, 관리자 60초당 30회이며, 동시 질문은 2개까지 처리하고 초과 요청은 대기시키지 않고 `503`으로 거절한다.
제한 초과는 공통 오류 응답의 `429`와 `Retry-After` 헤더로 반환한다.

운영 등 development 이외의 환경은 role별 요청 수와 시간 창을 모두 명시해야 하며 누락되면 시작을 거부한다.
동시 실행 상한은 `BACKEND_QUESTION_MAX_CONCURRENCY`로 지정한다.

```bash
export BACKEND_QUESTION_RATE_LIMIT_CITIZEN=10
export BACKEND_QUESTION_RATE_LIMIT_ADMIN=30
export BACKEND_QUESTION_RATE_WINDOW_SECONDS=60
export BACKEND_QUESTION_MAX_CONCURRENCY=4
```

### 제공 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/health` | API 상태 확인 |
| POST | `/api/v1/auth/register` | 시민 계정 공개 가입 |
| POST | `/api/v1/auth/login` | 이메일·비밀번호 로그인 및 JWT 발급 |
| POST | `/api/v1/questions` | 질문 처리 (admin/citizen) |
| GET | `/api/v1/maps/facilities?region=...` | 시민·관리자용 시설 지도 |
| GET | `/api/v1/admin/maps/types?region=...` | 관리자용 유형 지도 및 최신 현장기록 반영 |
| GET | `/api/v1/admin/maps/candidates?region=...` | 관리자용 후보 지도 |
| GET | `/api/v1/admin/maps/placements?region=...&radius_m=...&sites=...` | 관리자용 거점 배치 지도 |
| POST | `/api/v1/support-requests` | 시민 지원 요청 생성 |
| GET | `/api/v1/support-requests?status=...` | 관리자용 목록 조회 및 상태 필터 |
| GET | `/api/v1/support-requests/{request_id}` | 관리자용 상세 조회 |
| PATCH | `/api/v1/support-requests/{request_id}/status` | 관리자용 상태 변경 |
| POST/GET | `/api/v1/field-checks` | 현장 담당자·관리자 기록 생성 및 조회 |
| GET | `/api/v1/admin/demand-signals` | 관리자용 익명 지원 수요 집계 |
| GET | `/api/v1/admin/field-feedback-summary` | 관리자용 현장 확인 건수·항목별 응답 요약 |

인증이 필요한 요청에는 `Authorization: Bearer <ACCESS_TOKEN>` 헤더를 전달한다.
질문 요청의 `mode` 값은 호환성을 위해 받지만 권한으로 결정하며, admin은 admin, citizen은 citizen 모드로 처리한다.
현장 담당자는 질문 API를 사용할 수 없다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/questions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -d '{"mode":"citizen","question":"주변 교류 시설을 알려줘","location":{"lat":37.88,"lon":127.73}}'
```

### 지원 요청 및 현장 확인 기록

함께 가기·이동 도움 요청은 `POST /api/v1/support-requests`로 등록한다.
새 요청은 항상 `pending` 상태이며 자동 매칭·승인하지 않는다. 관리자만 상태를 `pending`, `approved`,
`rejected`, `completed` 중 하나로 변경할 수 있다. 연락처는 요청에 `contact_consent: true`를 명시한 경우에만 저장한다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/support-requests \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -d '{"facility_id":"<FACILITY_ID>","requester_name":"<REQUESTER_NAME>","contact":"<CONTACT>","contact_consent":true,"requested_at":"<ISO_8601_DATETIME>","request_type":"companion","note":"<NOTE>"}'

curl -H 'Authorization: Bearer <ADMIN_ACCESS_TOKEN>' \
  'http://127.0.0.1:8000/api/v1/support-requests?status=pending'
curl -X PATCH 'http://127.0.0.1:8000/api/v1/support-requests/<REQUEST_ID>/status' \
  -H 'Authorization: Bearer <ADMIN_ACCESS_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"status":"approved"}'
```

현장 확인은 `POST /api/v1/field-checks`로 저장하고, 격자 ID로 조회한다.
관리자 유형 지도 API는 셀별 최신 `checked_at` 기록을 반영한다. `has_residents=no`이면 제외
(기본 지도에서 숨김), 그렇지 않고 `support_needed=not_needed`이면 관찰형(우선순위 4)으로
낮춘다. 두 규칙이 모두 맞으면 제외가 우선한다. `unknown`/`unsure` 등 적용 조건에 해당하지
않는 최신 기록은 이전 기록으로 되돌아가지 않고 엔진 판정을 유지한다. 원본 엔진 유형·우선순위는
`engine_type`, `engine_priority`로 보존하며 GeoJSON 원본 파일은 변경하지 않는다. 이 반영은
관리자 지도에 한정되고 에이전트 답변의 수치는 변경하지 않는다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/field-checks \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <FIELD_WORKER_ACCESS_TOKEN>' \
  -d '{"cell_id":"<CELL_ID>","checklist":{"accessible":true,"bench":false},"checked_at":"<ISO_8601_DATETIME>","note":"<NOTE>"}'

curl -H 'Authorization: Bearer <FIELD_WORKER_ACCESS_TOKEN>' \
  'http://127.0.0.1:8000/api/v1/field-checks?cell_id=<CELL_ID>'
```

### 지도 API

시민 시설 지도는 다음 API를 사용한다. 지역은 `강남`, `춘천`만 허용한다.
시민 응답은 시설 GeoJSON만 제공하며 유형·후보·배치·위험도·현장기록 필드는 포함하지 않는다.
`fac_id`는 시설 연결용 내부 키이므로 프론트엔드는 화면에 글자로 표시하지 않는다.

```bash
curl -H 'Authorization: ******' \
  'http://127.0.0.1:8000/api/v1/maps/facilities?region=춘천'
curl -H 'Authorization: ******' \
  'http://127.0.0.1:8000/api/v1/admin/maps/types?region=춘천&show_excluded=false'
curl -H 'Authorization: ******' \
  'http://127.0.0.1:8000/api/v1/admin/maps/candidates?region=춘천'
curl -H 'Authorization: ******' \
  'http://127.0.0.1:8000/api/v1/admin/maps/placements?region=춘천&radius_m=1000&sites=3'
```

### 익명 운영 신호 (관리자 전용)

`GET /api/v1/admin/demand-signals`는 지원 요청을 `facility_id`, `request_type`, `status`별로 집계한다.
기존 시설 자료와 신뢰할 수 있는 매핑 근거가 없어 임의의 동네·셀 이름은 붙이지 않고 시설 ID만 제공한다.
기본 최소 집계 수는 3이며, 3건 미만인 그룹은 응답에서 제외한다. 응답에는 그룹 키와 건수만 포함하고
이름·연락처·이메일·메모나 원본 요청은 반환하지 않는다.

`GET /api/v1/admin/field-feedback-summary`는 셀별 확인 건수와 체크리스트 응답 수만 제공한다.
체크리스트의 원래 항목명은 신뢰할 수 없는 입력일 수 있어 반환하지 않고, 각 셀 응답 내 임시 항목 인덱스와 건수로만 제공한다.
두 API 모두 향후 엔진 보정값으로 전달 가능한 익명 운영 신호이며 현재 agent·engine 판단에는 반영되지 않는다.
엔진 보정 연동은 현준·혜진과 데이터 계약을 확정한 뒤 진행한다.

```bash
curl -H 'Authorization: Bearer <ADMIN_ACCESS_TOKEN>' \
  'http://127.0.0.1:8000/api/v1/admin/demand-signals'

curl -H 'Authorization: Bearer <ADMIN_ACCESS_TOKEN>' \
  'http://127.0.0.1:8000/api/v1/admin/field-feedback-summary'
```

### 계정 생성 및 권한

공개 회원가입은 citizen 계정만 만들 수 있다. 가입 후 로그인해 응답의 토큰을 사용한다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"<EMAIL>","password":"<PASSWORD_AT_LEAST_12_CHARACTERS>"}'

curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<EMAIL>","password":"<PASSWORD>"}'
```

admin·field_worker 계정은 공개 가입할 수 없다. 로컬 development에서만 아래 명령을 실행하면
이메일과 비밀번호를 대화형으로 입력받아 계정을 만든다. 비밀번호는 화면에 표시되지 않는다.
실제 계정 정보는 파일에 기록하거나 커밋하지 않는다.

```bash
python -m backend.seed_user --role admin
python -m backend.seed_user --role field_worker
```

| API | citizen | field_worker | admin |
| --- | --- | --- | --- |
| 질문 | citizen 모드 | 거부 | admin 모드 |
| 지원 요청 생성 | 허용 | 거부 | 거부 |
| 지원 요청 조회·상태 변경 | 거부 | 거부 | 허용 |
| 현장 확인 생성·조회 | 거부 | 허용 | 허용 |
| 시설 지도 조회 | 허용 | 거부 | 허용 |
| 유형·후보·배치 지도 조회 | 거부 | 거부 | 허용 |
| 시설 지도 조회 | 허용 | 거부 | 허용 |
| 유형·후보·배치 지도 조회 | 거부 | 거부 | 허용 |

### 현재 범위와 유의사항

- 비밀번호는 Argon2 해시로 저장한다. JWT secret은 환경 변수로만 제공하고 토큰·비밀번호·Authorization 헤더는 로그에 남기지 않는다.
- 지원 요청은 `pending`으로 저장되며 자동 매칭·승인과 알림 기능은 구현하지 않았다.
- 프론트엔드 연결과 배포는 아직 구현하지 않았다.
- 현장 확인 기록은 에이전트 답변·엔진 원본 결과에는 자동 반영하지 않고, 관리자 유형 지도 응답에서만 최신 기록을 덮어써 표시한다.
- 실제 사용자 데이터, 비밀번호, JWT secret, Anthropic API 키 및 `.env` 파일은 Git에 추가하거나 커밋하지 않는다.
  DB 파일과 `backend/data/`도 추적하지 않는다.

## 데이터 읽기

노트북 첫 셀에서 `src` 를 경로에 추가한다.

```python
import sys; sys.path.insert(0, "../src")

from loaders import load_sk, load_shinhan

age = load_sk("flow_age_pop", months=["202507"])   # 중복 제거된 상태로 반환
mct = load_shinhan("mct")   # 데이터1 — 시간대(TIME_GB) 있음, 법인 포함
cln = load_shinhan("cln")   # 데이터2 — 고객 거주지(CLN_SGG_CD) 있음, 법인 제외
```

인코딩/구분자는 `src/config.py` 에만 둔다. 직접 `pd.read_csv` 하지 말 것.
(`src/loaders.py` 의 이름은 표준 라이브러리 `io` 와 충돌하지 않도록 고른 것 — `src/io.py` 로 두면 `import pandas` 가 깨진다.)

## 데이터 메모

- 기간은 2025-07 ~ 2025-12, 대상은 서울 강남구와 강원 춘천시 두 곳뿐이다.
- 공간 키가 다름: SK 원본은 **50m 격자**(`BLOCK_CD`, `X_COORD`/`Y_COORD`), 신한카드는 **시군구**(2개).
  직접 결합은 불가능하므로 각 데이터가 답할 수 있는 범위에서 따로 분석한다.
- **격자 분석의 팀 표준은 250m** (`preprocessed/flow_cell.parquet`, `cell_id = floor(X/250)_floor(Y/250)`).
  50m는 춘천에서 칸당 1명 미만이라 쓸 수 없다. 거리 계산의 기준점은 격자 중심이다.
- SK 좌표계는 **UTM-K(EPSG:5179)** — 테이블 정의서에 명시돼 있다.
- SK 값은 일별 시계열이 아니라 **월별 "일평균"** 이다. 격자당 관측 시점이 6개뿐이다.
- **신한카드 데이터2는 2026-09 재배포본**(`데이터2_수정.txt`)을 쓴다. 최초 배포본은
  `TA_YMD` · `MCT_SGG_CD` · `MCT_RY_CD` 가 누락된 5컬럼이었고, 재배포로 8컬럼이 복구됐다.
  행 수와 결제액 합계는 동일하다.
- 두 카드 파일의 역할이 다르다. **데이터1**은 시간대(`TIME_GB`)가 있고 법인카드를 포함한다.
  **데이터2**는 고객 거주지(`CLN_SGG_CD`)가 있고 법인카드가 빠져 있다 — 우리 부문용 파일이다.
- **`flow_time_pop_202512` 와 `flow_wkdy_pop_202512` 에는 중복 행이 있다.** 전체 행이 정확히
  2번씩 들어 있다 (185,090→92,545 / 242,534→121,267). `load_sk()` 가 자동 제거하지만
  원천 CSV를 직접 읽을 때는 직접 걷어내야 한다.

해석상 주의사항은 `docs/data_interpretation.md` 에 정리돼 있다. 분석 전에 먼저 읽을 것.
