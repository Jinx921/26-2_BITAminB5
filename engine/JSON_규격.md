# 분석 엔진 JSON 규격 (혜진·채원·사랑용) · 2026-10-01

## 한눈에
- 엔진 도구 8개는 **모두 같은 겉모양**의 JSON을 돌려준다. 겉모양만 맞추면 어떤 도구든 같은 코드로 받을 수 있다.
- **혜진(에이전트):** `out/tool_schemas.json`을 Claude tool 정의로 그대로 쓰고, 답변 숫자는 `evidence`에서만 인용한다.
- **채원(백엔드):** 도구 함수를 호출해 받은 dict를 그대로 API 응답으로 넘기면 된다. 그림·지도 파일은 `engine/out/` 폴더를 정적 경로로 서빙한다.
- **사랑(프론트):** 지도는 `geojson` 파일(WGS84 폴리곤) 또는 각 행의 `lat`·`lon`(칸 중심)을 쓰면 된다. 예시 응답은 `out/json/*.json`에 전부 있어 목업 데이터로 바로 쓸 수 있다.

## 1. 공통 겉모양 (모든 도구)

```json
{
  "tool": "classify",
  "region": "춘천",
  "result":   { ... 도구별 내용 ... },
  "evidence": [ {"metric": "n_긴급방문형", "value": 55}, ... ],
  "caveats":  [ "통신 유동인구는 머무는 사람 기준이며 거주자와 같지 않다...", ... ],
  "figures":  [ "out/types_춘천.png" ],
  "geojson":  "out/types_춘천.geojson",
  "params":   { "far_social_m": 500, ... }
}
```

| 키 | 뜻 | 누가 쓰나 |
|---|---|---|
| `tool` | 도구 이름 | 전원 |
| `region` | `"강남"` 또는 `"춘천"` (check_residential에서 여러 지역이 섞이면 `null`) | 전원 |
| `result` | 도구별 본문 (아래 2절) | 프론트 화면, 에이전트 |
| `evidence` | LLM이 인용해도 되는 숫자 목록. `metric` 이름 + `value` | 에이전트(답변 검증) |
| `caveats` | 답변에 붙여야 할 한계 문장 | 에이전트, 관리자 화면 하단 |
| `figures` | PNG 경로 목록 (engine 폴더 기준 상대경로). 없으면 `[]` | 관리자 화면 |
| `geojson` | GeoJSON 경로 (engine 기준 상대경로, WGS84). 없으면 `null` | 지도 |
| `params` | 이번 계산에 쓴 기준값 (재현용) | 백엔드 로그 |

규칙
- 숫자는 소수 4자리로 반올림, 결측은 `null`. NaN·Infinity는 나오지 않는다.
- `evidence`의 값은 `result`의 같은 지표와 **같은 값**이다.
- **잘못된 입력**(없는 칸, 다른 지역 칸, k=0 등)이면 예외 대신 `result: {"error": "설명"}`을 돌려준다. 백엔드는 `"error" in result`로 확인하면 된다.
- **대상이 없을 때**(예: 배치할 긴급방문형 칸 0개)는 `result: {"message": "대상 칸 없음"}`이다. 오류가 아니다.
- 한국어 키가 있다: 유형 이름(`연계형`, `긴급방문형`, `예방인프라형`, `관찰형`)과 행정동 이름이 dict 키로 쓰인다. UTF-8로 주고받으면 문제없다.

## 2. 도구별 `result`

좌표: 행 단위 `lat`·`lon` = 250m 칸 중심(WGS84). `x`·`y`는 엔진 내부 좌표(UTM-K, EPSG:5179)라 지도에는 쓰지 않는다.

### find_candidates: 후보 찾기 (활동 위축 칸)
| 필드 | 형식 | 내용 |
|---|---|---|
| `n_candidates` | int | 후보 칸 수 |
| `by_emd` | {행정동: int} | 행정동별 후보 수 |
| `cells` | list | 칸별 `cell_id, emd_name, lat, lon, persistent_months, senior_ratio, day_share, res_status, senior65_share, hh_1p_share` |
| `n_dropped_nonresidential` | int | 주거건물 없어 뺀 칸 수 |
| `dropped_status` | {상태: int} | 뺀 이유별 수 |

### check_residential: 거주 확인 (입력 `cell_ids`)
| 필드 | 형식 | 내용 |
|---|---|---|
| `cells` | list | `cell_id, region, emd_name, res_status(주거/용도미상/비주거/건물없음), n_bldg, n_res, n_apt, n_na, n_semi, old_share, night_share` |
| `status_counts` | {상태: int} | |
| `not_found` | list[str] | 없는 칸 ID |

### lookup_resources: 자원 조회 (입력 `cell_id` 또는 `lat`·`lon`)
| 필드 | 형식 | 내용 |
|---|---|---|
| `nearest_by_kind` | list | 시설 종류별 가장 가까운 곳 `kind, name, dist_m(정수 m), addr, lat, lon` |
| `within_radius` | list | 반경 안 시설 `fac_id, kind, group(social/health), name, addr, dist_m, lat, lon` |
| `count_within_radius` | {종류: int} | |
| `fallback_nearby` | list | 화면 대체용: 종류별 가장 가까운 곳 중 5km(`config.FALLBACK_MAX_M`) 안. `within_radius`와 같은 필드 + `beyond_radius`(반경 밖이면 true). 외곽처럼 `within_radius`가 비었을 때 지도·카드에 쓴다. `nearest_by_kind`(거리 제한 없음)는 그대로 (10/18 추가) |

### classify: 유형 분류
| 필드 | 형식 | 내용 |
|---|---|---|
| `type_counts` | {유형: int} | 4유형 칸 수 |
| `gap_tags` | {유형: {교류/보건/둘다: int}} | 무엇이 멀어서 공백인지 |
| `n_universe_cells` | int | 분류 대상 거주 칸 수 |
| `by_emd_withdrawn` | {행정동: {유형: int}} | 긴급방문·연계형의 행정동별 수 |
| `table` | list(위축 칸 전체: 긴급방문형+연계형) | 원인·추천 표 `cell_id, emd_name, lat, lon, type, gap_tag, priority, cause, recommendation, near_social_name, dist_social, near_health_name, dist_health, res_status` |
| `type_actions` | {유형: {priority, action}} | 유형별 우선순위·조치 |
| `layers` | {층 이름: {유형: int}} | 위축 신호 층 / 자원 구조 층. **두 층을 합쳐 위험 숫자로 말하지 말 것** |

### simulate_placement: 배치 시뮬레이션 (이동형 거점)
| 필드 | 형식 | 내용 |
|---|---|---|
| `chosen_sites` | list | 고른 거점 `cell_id, emd_name, lat, lon, covers(덮는 대상 칸 수)` (+내부 x, y) |
| `n_target_cells` | int | 대상(기본 긴급방문형) 칸 수 |
| `covered_cells` | int | 반경 안에 든 대상 칸 수 |
| `covered_senior_share` | float | 덮은 60대+ 유동 비율 |
| `k_curve` | list | 거점 수별 `k, covered_cells, covered_cells_share, covered_senior_share, optimal` (그래프용) |
| `type_after` | {유형: int} | 배치 후 유형 (덮이면 `연계형(이동형 도달)`) |

### robustness: 강건성 점검
| 필드 | 형식 | 내용 |
|---|---|---|
| `one_at_a_time` | list | 기준값 하나씩 바꾼 결과 `param, value, 4유형 수, urgent_retained, urgent_precision, urgent_jaccard, is_default` (표·그래프용) |
| `type_range_all_combos` | {유형: [min, max]} | 모든 조합에서 유형 수 범위 |
| `urgent_jaccard_median_all_combos` | float | 긴급방문형 판정 겹침 중앙값 |
| `default_row` | dict | 기본값 행 |
| `grid` | list | 전체 조합 (수백 행, 화면엔 보통 안 씀) |

### facility_change: 시설 변화 가정 (2차)
| 필드 | 형식 | 내용 |
|---|---|---|
| `removed` | list | 실제 뺀 시설 `fac_id, kind, name` |
| `not_found` | list[str] | 이 지역에 없는 시설 ID (반영 안 됨) |
| `added` | list | 더한 시설 (입력 그대로) |
| `n_changed_cells` | int | 유형이 바뀐 칸 수 |
| `transitions` | {이전유형: {이후유형: int}} | |
| `changed_cells` | list | `cell_id, emd_name, before, after` |

### region_context: 지역 맥락 (2차, 시군구 단위)
| 필드 | 형식 | 내용 |
|---|---|---|
| `local_payment_pct` | float | 지역 가맹점 결제 중 같은 시도 거주자 비중(%). 주민이 다른 지역에서 쓴 결제는 포함되지 않음 |
| `local_payment_by_age_pct` | {연령대: float} | 같은 정의의 연령대별 값. 생활 반경으로 해석하지 않는다 |
| `senior60_card_time_pct` | {시간대: float} | 60대+ 결제 시간대 비중 |
| `population` | dict | `pop, p65, p85, solo65, solo_mid_male, solo_top_age` |
| `lens` | str | 지역 해석 관점 한 줄 |
| `type_counts` | {유형: int} | |

카드·인구는 시군구 값이라 칸 단위로 쓰지 않는다.

## 3. 에이전트 tool 정의 (`out/tool_schemas.json`)
- Claude tool use 형식(`name`, `description`, `input_schema`) 8개. `python tool_schemas.py`로 다시 만든다.
- 기준값 인자(야간·주택 기준, 강건성 목록 등)는 **일부러 스키마에서 뺐다.** LLM이 기준을 마음대로 바꾸지 않게 하려는 것이고, 필요하면 백엔드에서 직접 넣어 호출한다.

## 4. 확인받을 것
- [ ] 혜진: evidence만 인용하는 방식으로 에이전트 검증 가능한지, 필드 이름 바꿀 것 있는지
- [ ] 채원: 도구 호출 방식 (파이썬 함수 직접 import vs HTTP 래핑), `out/` 파일 서빙 경로
- [ ] 사랑: 지도에 `geojson` 파일을 쓸지 행의 `lat`·`lon`을 쓸지
