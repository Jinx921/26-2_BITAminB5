# 에이전트 (담당: 혜진)

- 설계: [`docs/에이전트_설계.md`](docs/에이전트_설계.md) (v2.2)
- 분석 엔진: [`../engine/README.md`](../engine/README.md) (v0.2) · 응답 규격: [`../engine/JSON_규격.md`](../engine/JSON_규격.md)

이 문서는 팀원이 **에이전트가 어떻게 구현되었는지** 따라갈 수 있도록 쓴다.
앞부분(1~6절)은 현재 구조를 설명하고, 뒷부분(7절)은 단계별로 무엇을 왜 만들었고 출력이 어떻게 나왔는지를 기록한다.
단계가 끝날 때마다 7절에 한 절씩 추가하고, 1~6절을 현재 상태로 고친다.

---

## 목차

1. [에이전트가 하는 일](#1-에이전트가-하는-일)
2. [시작 설정](#2-시작-설정)
3. [동작 흐름](#3-동작-흐름)
4. [설계 원칙](#4-설계-원칙)
5. [모듈 구성](#5-모듈-구성)
6. [진행 현황](#6-진행-현황)
7. [단계별 개발 기록](#7-단계별-개발-기록)

---

## 1. 에이전트가 하는 일

에이전트는 **질문을 받아 엔진 계산 순서를 정하고, 결과를 검증해서, 사용자에게 맞는 화면 조각으로 바꾸는 중간 층**이다.
숫자는 직접 만들지 않는다. 계산은 전부 분석 엔진이 하고, 에이전트는 엔진 `evidence`의 숫자만 인용한다.

| 층                      | 담당 | 하는 일                                                                        |
| ----------------------- | ---- | ------------------------------------------------------------------------------ |
| 분석 엔진 (`engine/`)   | 현준 | 후보 찾기·유형 분류·배치·강건성 등 계산. 같은 입력이면 같은 결과               |
| **에이전트 (`agent/`)** | 혜진 | 질문 해석, 도구 선택, 결과 요약, 검증·신뢰도, 화면 조각 구성, 모드별 도구 차단 |
| 백엔드                  | 채원 | 엔진 전체 결과 저장·서빙, 현장 기록, 이웃 연결 요청                            |
| 프론트                  | 사랑 | 화면 조각을 지도·차트·카드로 그리기                                            |

에이전트가 맡는 역할은 다섯 가지다.

| #   | 역할                                               |
| --- | -------------------------------------------------- |
| ①   | 질문을 엔진 도구 호출 순서로 바꾼다                |
| ②   | 엔진 결과를 Sonnet이 읽을 크기로 줄인다            |
| ③   | 답변의 숫자와 한계 문장을 검증하고 신뢰도를 붙인다 |
| ④   | 사용자에 맞는 화면 조각 JSON을 만든다              |
| ⑤   | 모드별로 쓸 수 있는 도구를 제한한다                |

에이전트는 고립 위험을 판정하지 않는다(판정은 엔진 규칙이 한다). 최종 결정도 하지 않는다(결정은 담당자가 한다).

---

## 2. 시작 설정

저장소 루트에서 실행한다.

```bash
# 1) 가상환경과 패키지
source .venv/bin/activate
pip install -r engine/requirements.txt -r agent/requirements.txt

# 2) API 키: agent/.env 파일을 만들고 한 줄 작성 (git 무시 대상)
#    ANTHROPIC_API_KEY=sk-ant-...

# 3) 테스트 (API 키 없이 동작)
python -m pytest agent/tests -v

# 4) 엔진 도구 하나 호출해 보기
python -m agent.engine_client classify --region 춘천                  # 예시 응답
python -m agent.engine_client classify --region 춘천 --engine live    # 실제 엔진 계산
```

> 키는 반드시 `agent/.env`에 넣는다. 루트 `.gitignore`에 `!.env.example` 예외가 있어서 `.env.example`에 키를 넣으면 커밋된다.

---

## 3. 동작 흐름

목표 시나리오는 관리자 모드 질문 **"춘천에서 어디부터 확인해야 해?"** 이다.

```
질문 ─▶ ① Sonnet: 도구 선택 ─▶ ② 엔진 호출 ─▶ ③ 결과 보관 + 요약해서 Sonnet에 전달
                     ▲                                    │
                     └──────── 다음 도구 필요하면 반복 ◀───────┘
     ─▶ ④ Sonnet: 답변 제출 (요약 문장 + 인용 목록)
     ─▶ ⑤ 코드 검증 (숫자 대조 · caveats · 신뢰도 등급) ─ 실패 시 1회 수정
     ─▶ ⑥ 화면 조각 JSON (요약 + 지도 참조 + 신뢰도 + caveats)
```

| 흐름        | 구현               |
| ----------- | ------------------ |
| ② 엔진 호출 | `engine_client.py` |
| ③ 결과 보관 | `store.py`         |

---

## 4. 설계 원칙

| 원칙                                                                                 | 이유                                                          |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| LLM은 Claude Sonnet 5.5 (`claude-sonnet-5-5`)                                        | 설계 4절 결정                                                 |
| API 키는 `agent/.env`에만 둔다. 코드에 넣지 않는다                                   | 키 유출 방지                                                  |
| 엔진 코드는 수정하지 않는다. `engine/core.py`의 공개 도구(`core.TOOLS`)만 호출한다   | 엔진은 현준 담당. 겉모양(도구 이름·인자·필드)만 약속이다      |
| 예외: 칸별 안정도 계산만 엔진 내부 함수 `_universe`를 쓴다                           | 설계 차별점 ④. 엔진 공개 도구에 칸별 결과가 없다              |
| 엔진 전체 결과는 Sonnet에 넣지 않는다. evidence와 핵심 값만 요약해 넘긴다            | `robustness` 하나가 약 10만 자다                              |
| 우리 데이터에 관한 숫자는 엔진 결과(evidence, params)와 사용자 입력에서만 가져온다   | LLM이 숫자를 지어내지 못하게 한다 (설계 차별점 ②)             |
| 비율 등 계산이 필요하면 엔진 값을 쓰고, 직접 계산한 값은 검증 단계에서 다시 계산한다 | 같은 이유                                                     |
| 엔진 숫자를 프롬프트나 코드에 하드코딩하지 않는다                                    | 엔진 기준값이 바뀌면 에이전트가 틀린 말을 하게 된다           |
| 시민 모드에는 `find_candidates`, `classify`를 주지 않는다                            | 위험 판정이 시민에게 구조적으로 나올 수 없게 한다 (낙인 방지) |

---

## 5. 모듈 구성

```
agent/
├── README.md            이 문서
├── requirements.txt     에이전트 전용 패키지 (anthropic, python-dotenv, pytest)
├── .env                 ANTHROPIC_API_KEY (git 무시, 직접 생성)
├── __init__.py          agent 패키지 표시 (빈 파일)
├── engine_client.py     엔진 호출: LiveEngine / FixtureEngine
├── store.py             엔진 전체 결과 보관소 (ref 발급, 저장)
├── tests/
│   ├── conftest.py      저장소 루트를 import 경로에 추가
│   └── test_engine_client.py
├── docs/                설계 문서·구조도
└── out/                 실행 결과 (git 무시)
```

모듈 사이의 데이터 흐름은 다음과 같다.

```
engine_client.call(tool, args) ──▶ 엔진 응답 dict (8개 키)
        │
        └──▶ store.put(...) ──▶ ref ("r1") ── 전체 결과 보관
```

엔진 응답의 공통 형식은 [`engine/JSON_규격.md`](../engine/JSON_규격.md)를 따른다.

| 키                   | 내용                                      | 에이전트에서의 쓰임                             |
| -------------------- | ----------------------------------------- | ----------------------------------------------- |
| `tool`, `region`     | 도구 이름, 지역                           | 보관 목록 표시                                  |
| `result`             | 도구별 본문                               | 보관소에 원본 그대로 보관                       |
| `evidence`           | 인용 가능한 숫자 목록 (`metric`, `value`) | 답변에 인용할 수 있는 유일한 숫자 출처          |
| `caveats`            | 답변에 붙일 한계 문장                     | 답변에 원문 그대로 첨부                         |
| `figures`, `geojson` | 그림·지도 파일 경로                       | 실제 엔진 호출에서는 비어 있음 (`render=False`) |
| `params`             | 계산에 쓴 기준값                          | 인용 가능한 숫자 출처                           |

---

## 6. 진행 현황

| 단계 | 내용      | 주요 파일                                |
| ---- | --------- | ---------------------------------------- |
| 0    | 환경 구성 | `requirements.txt`, `.env`, `.gitignore` |
| 1    | 엔진 연결 | `engine_client.py`, `store.py`           |

---

## 7. 단계별 개발 기록

각 단계는 같은 틀로 기록한다.

| 항목      | 내용                                 |
| --------- | ------------------------------------ |
| 목표      | 이 단계에서 만들려는 것              |
| 구현      | 만든 파일, 구현 방식, 그렇게 한 이유 |
| 실행 결과 | 실제 출력 (그대로 붙임)              |
| 결과 검토 | 출력이 맞는지 어떻게 확인했는지      |
| 테스트    | 테스트 목록과 확인 내용              |

---

### 0단계 · 환경 구성

#### 목표

에이전트 코드를 둘 패키지를 만들고, Claude API를 쓸 준비를 한다.

#### 구현

| 파일                     | 내용                                   | 이유                                                                                                                     |
| ------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `agent/__init__.py`      | 빈 파일                                | `agent`를 패키지로 만든다. 엔진은 `import config`를 그대로 쓰므로, 에이전트 모듈은 `agent.xxx`로 불러 이름 충돌을 막는다 |
| `agent/requirements.txt` | `anthropic`, `python-dotenv`, `pytest` | Claude API 호출, `.env`에서 키 읽기, 테스트                                                                              |
| `agent/.env`             | `ANTHROPIC_API_KEY`                    | 키 보관. 루트 `.gitignore`의 `.env` 규칙으로 git이 무시한다. 파일 권한은 600(본인만 읽기)이다                            |
| `.gitignore`             | `agent/out/` 한 줄 추가                | 실행할 때마다 쌓이는 결과 저장 폴더                                                                                      |

`.env.example` 견본 파일은 만들지 않는다. 키 이름은 이 문서 2절에 적어 둔다.

#### 실행 결과

```
anthropic 1.12.1
python-dotenv ok
pytest 9.1.1

무시됨: .env
무시됨: agent/.env
무시됨: agent/out/x.json
engine core ok          ← 패키지 설치 후에도 엔진 import 정상
```

#### 결과 검토

- 키 파일과 결과 폴더가 git 무시 대상임을 `git check-ignore`로 확인했다.
- 키 값은 출력하지 않고, 키가 있는지만 `grep -c`로 확인했다.
- `engine/` 폴더에 변경이 없다.

---

### 1단계 · 엔진 연결

#### 목표

엔진 도구를 에이전트에서 호출하고, 결과를 보관하는 통로를 만든다.
API 키나 엔진 데이터가 없어도 테스트할 수 있게 예시 응답으로도 같은 방식으로 호출되게 한다.

#### 구현

**`engine_client.py`**: 두 엔진이 같은 메서드 `call(tool, args)`를 갖고, 같은 형식의 dict를 돌려준다.

| 구성               | 구현 방식                                                                                                          | 이유                                                                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `LiveEngine`       | `core.TOOLS[tool](**args)`로 엔진 공개 도구 8개를 호출                                                             | 엔진 코드를 고치지 않고 공개 도구만 쓴다                                                                                                       |
|                    | 그림을 그리는 도구(`find_candidates`, `classify`, `simulate_placement`, `facility_change`)는 `render=False`로 호출 | `engine/out/`은 git이 추적하는 폴더다. 그대로 부르면 PNG·geojson을 덮어써 엔진 폴더가 바뀐다. 지도는 프론트가 결과 행의 `lat`·`lon`으로 그린다 |
|                    | 호출을 잠금(lock)으로 한 번에 하나씩 실행                                                                          | `simulate_placement`가 모듈 전역 상태(`_mclp.last_status`)를 쓴다                                                                              |
|                    | 잘못된 인자·지역은 `EngineError`로 바꿔 던짐                                                                       | 엔진마다 다른 예외(`ValueError`, `TypeError` 등)를 하나로 모아, 호출하는 쪽이 한 가지로 처리하게 한다                                          |
| `FixtureEngine`    | `engine/out/json/*.json` 예시 응답을 돌려줌                                                                        | API 키·엔진 데이터 없이 테스트한다                                                                                                             |
|                    | 파일 이름이 아니라 **JSON 안의 `tool`·`region`·`params`가 호출 인자와 맞는 파일**을 고름                           | 파일 이름(`k3_radius_m1000` 등)을 해석하려면 엔진 기본값을 코드에 적어야 한다. 하드코딩 금지 원칙에 어긋난다                                   |
|                    | 조건에 맞는 파일이 여럿이면 파일 이름 순 첫 번째                                                                   | 테스트용이므로 결정적이기만 하면 된다                                                                                                          |
|                    | 돌려줄 때 깊은 복사                                                                                                | 받은 쪽이 결과를 고쳐도 다음 호출에 영향이 없다                                                                                                |
| `_normalize_paths` | 그림·지도 경로의 `\`를 `/`로 변환                                                                                  | 예시 JSON이 Windows에서 만들어져 `out\\types_춘천.png` 형태다                                                                                  |
| `__main__`         | 터미널 실행 진입점                                                                                                 | 도구 하나를 불러 evidence·caveats·params를 바로 확인한다                                                                                       |

**`store.py`**: `ResultStore`는 엔진 전체 결과를 보관한다.

| 메서드                      | 하는 일                                                           |
| --------------------------- | ----------------------------------------------------------------- |
| `put(tool, args, data)`     | 결과를 보관하고 ref(`r1`, `r2`, …)를 돌려준다                     |
| `get(ref)`, `by_tool(tool)` | ref나 도구 이름으로 결과를 찾는다                                 |
| `save()`                    | `agent/out/runs/<시각>/`에 결과별 JSON과 목록 `index.json`을 쓴다 |

엔진 원본은 보관소에 두고, 다른 곳에서는 ref로 원본을 가리킨다.

#### 실행 결과

**① 시나리오 도구 세 개를 두 방식으로 호출**

```
[fixture] r1 find_candidates   33,939자  evidence  4개  caveats 5개  0.0s
[fixture] r2 classify          20,671자  evidence 14개  caveats 6개  0.0s
[fixture] r3 robustness        99,738자  evidence 27개  caveats 7개  0.0s
[live   ] r4 find_candidates   33,893자  evidence  4개  caveats 5개  0.1s
[live   ] r5 classify          20,635자  evidence 14개  caveats 6개  0.0s
[live   ] r6 robustness        99,738자  evidence 27개  caveats 7개  2.2s
```

**② 터미널 실행** (`python -m agent.engine_client classify --region 춘천 --engine live`)

```
[live] classify 춘천: 20,635자
result 키: ['type_counts', 'gap_tags', 'n_universe_cells', 'by_emd_withdrawn', 'table', 'type_actions', 'layers']
evidence:
  n_연계형 = 98
  n_긴급방문형 = 55
  n_예방인프라형 = 101
  n_관찰형 = 1361
  관찰형_gap_교류 = 176  /  관찰형_gap_둘다 = 20  /  관찰형_gap_보건 = 81
  긴급방문형_gap_교류 = 38  /  긴급방문형_gap_둘다 = 5  /  긴급방문형_gap_보건 = 12
  예방인프라형_gap_교류 = 55  /  예방인프라형_gap_둘다 = 14  /  예방인프라형_gap_보건 = 32
  n_universe_cells = 1615
caveats: 6개 (공통 3 + 거주 칸 정의 + SGIS 1km + 두 층 구분)
params: {'far_social_m': 500, 'far_health_m': 3000, 'persist_min': 4, 'residential_filter': True}
```

(evidence는 지면상 한 줄에 세 개씩 묶었다. 실제 출력은 한 줄에 하나다.)

#### 결과 검토

**① 두 방식 비교**

- 실제 엔진과 예시 응답의 evidence·caveats가 세 도구 모두 같다.
- 글자 수 차이는 실제 엔진이 `render=False`라 `figures`가 `[]`, `geojson`이 `null`이기 때문이다.
- 실행 시간은 `robustness`가 2.2초로 가장 길다. 질문 하나에 실시간으로 호출해도 된다.
- 세 도구를 합치면 약 15만 자다. 엔진 원본을 그대로 Sonnet에 넣기에는 크다.

**② classify 출력 검토**

| 확인                             | 결과                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------ |
| 엔진 README·설계 0-1절 값과 대조 | 유형 98 / 55 / 101 / 1361, 긴급방문형 교류 38·보건 12·둘다 5로 일치                  |
| 네 유형 합 = 분류 대상 칸 수     | 98 + 55 + 101 + 1361 = 1615 = `n_universe_cells`                                     |
| 긴급방문형 태그 합               | 38 + 5 + 12 = 55 = `n_긴급방문형`                                                    |
| 예방인프라형 태그 합             | 55 + 14 + 32 = 101. 예방인프라형은 정의상 공백이 있는 칸이라 모든 칸에 태그가 붙는다 |
| 연계형 태그 없음                 | 정상. 연계형은 자원이 가까운 칸이라 공백 태그가 없다                                 |
| caveats                          | classify에 붙어야 할 6개가 모두 있다. 강남 보건 caveat는 춘천이라 없는 것이 맞다     |
| params                           | `engine/config.py` 기본값과 같다                                                     |

**③ 출력에서 확인된 특징**

- **관찰형에도 공백 태그가 277칸 있다 (176 + 20 + 81).** 자원은 멀지만 어르신 비중 상위 25%가 아니어서 관찰형으로 남은 칸이다. 설계 0-1절의 두 층 구분에 따라 긴급방문형 공백과 같은 층으로 묶어 말하지 않는다.
- **evidence에는 행정동 정보가 없다.** 행정동별 칸 수는 `result.by_emd_withdrawn`에만 있다.

#### 테스트

`python -m pytest agent/tests -v` → **11 passed**

| 테스트                                | 확인 내용                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| `test_fixture_shape` ×3               | 예시 응답이 공통 형식(8개 키)이고 경로에 `\`가 없다                                   |
| `test_fixture_matches_params`         | 인자(k=3, 반경 3000)에 맞는 예시를 고른다. 예시에 없는 기준값·없는 도구는 오류가 난다 |
| `test_fixture_returns_copy`           | 받은 결과를 고쳐도 다음 호출에 영향이 없다                                            |
| `test_live_equals_fixture` ×3         | 실제 엔진과 예시 응답의 evidence·caveats가 같다                                       |
| `test_live_does_not_touch_engine_out` | 실제 호출 전후로 `engine/out` 파일 수정 시각이 같다                                   |
| `test_live_bad_region`                | 없는 지역(부산)은 `EngineError`가 난다                                                |
| `test_store_refs_and_save`            | ref가 r1 → r2 → r3 순으로 붙고, 저장 폴더에 결과별 파일과 `index.json`이 생긴다       |

#### 직접 확인하는 방법

```bash
python -m pytest agent/tests -v
python -m agent.engine_client classify --region 춘천 --engine live
python -m agent.engine_client robustness --region 강남 --engine live
python -m agent.engine_client robustness --region 춘천 --engine live --save   # agent/out/runs/ 에 저장
```
