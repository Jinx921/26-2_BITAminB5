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
질문 API를 실제 Anthropic과 함께 사용하려면 `agent/.env`에 API 키를 설정한다.

```bash
python -m pytest backend/tests -q
python -m pytest agent/tests -q
```

설정은 `BACKEND_APP_NAME`과 `BACKEND_LOG_LEVEL` 환경 변수로 지정할 수 있다.
기본 로그 레벨은 `INFO`이며 요청 로그는 JSON 형식으로 출력된다.
SQLite 파일은 기본 `backend/data/app.db`에 생성되며 `BACKEND_DB_PATH`로 경로를 바꿀 수 있다.
DB와 `backend/data/`는 Git에서 제외된다.

### 제공 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/health` | API 상태 확인 |
| POST | `/api/v1/questions` | 관리자·시민 질문 처리. 시민 위치는 선택 사항이며 응답은 화면 표시 내용만 반환 |
| POST | `/api/v1/support-requests` | 함께 가기·이동 도움 요청 생성. `pending`으로 저장 |
| GET | `/api/v1/support-requests` | 지원 요청 목록 조회. 선택적 `status` 필터 지원 |
| GET | `/api/v1/support-requests/{request_id}` | 지원 요청 상세 조회 |
| POST | `/api/v1/field-checks` | 현장 확인 기록 생성 |
| GET | `/api/v1/field-checks?cell_id=...` | 격자 ID 기준 현장 확인 기록 조회 |

질문 API 요청 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{"mode":"citizen","question":"주변 교류 시설을 알려줘","location":{"lat":37.88,"lon":127.73}}'
```

### 지원 요청 및 현장 확인 기록

함께 가기·이동 도움 요청은 `POST /api/v1/support-requests`로 등록한다.
새 요청은 항상 `pending` 상태이며 자동 매칭·승인하지 않는다. 관리자가 별도로 검토하고 승인해야 한다.
지원 요청 목록·상세 조회 API는 **현재 임시 관리자용**으로, 아직 인증·권한 검사가 없다.
연락처 등 개인정보가 포함될 수 있으므로 신뢰된 로컬 환경에서만 사용한다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/support-requests \
  -H 'Content-Type: application/json' \
  -d '{"facility_id":"facility-123","requester_name":"홍길동","contact":"010-1234-5678","requested_at":"2026-10-10T10:00:00+09:00","request_type":"companion","note":"도착 전에 연락 바랍니다"}'

curl 'http://127.0.0.1:8000/api/v1/support-requests?status=pending'
curl http://127.0.0.1:8000/api/v1/support-requests/1
```

현장 확인은 `POST /api/v1/field-checks`로 저장하고, 격자 ID로 조회한다.
이 기록은 저장·조회 전용이며 현재 에이전트 답변이나 엔진 분석 결과에 반영되지 않는다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/field-checks \
  -H 'Content-Type: application/json' \
  -d '{"cell_id":"4026_7935","checklist":{"accessible":true,"bench":false},"checked_at":"2026-10-10T11:30:00+09:00","note":"입구에 계단이 있음"}'

curl 'http://127.0.0.1:8000/api/v1/field-checks?cell_id=4026_7935'
```

### 현재 범위와 유의사항

- 로그인·권한 관리는 아직 없다. 지원 요청 목록·상세 조회는 현재 임시 관리자용 API다.
- 지원 요청은 `pending`으로 저장되며 자동 매칭·승인과 알림 기능은 구현하지 않았다.
- 프론트엔드 연결과 배포는 아직 구현하지 않았다.
- 현장 확인 기록은 저장·조회 전용이며 에이전트 답변이나 엔진 분석 결과에 자동 반영되지 않는다.
- 실제 사용자 데이터와 API 키 등 비밀값은 Git에 추가하거나 커밋하지 않는다. DB 파일과 `backend/data/`도 추적하지 않는다.

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
