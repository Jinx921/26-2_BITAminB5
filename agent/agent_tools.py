"""에이전트 쪽 도구: 엔진 도구를 감싸거나 엔진 데이터를 읽기만 한다 (엔진 코드는 고치지 않는다).

senior_hours (시민 모드)
  엔진 region_context 에서 60대 이상 카드 결제 시간대만 꺼낸다.
  region_context 결과에는 유형별 칸 수(type_counts) 같은 위험 정보와 칸·유형 설명 caveat 가 있어
  시민 모드에 그대로 줄 수 없다. 시간대 값과 evidence 만 남기고, 한계 문장은 시민용으로 새로 붙인다.

find_facility (관리자 모드)
  시설 이름으로 시설 ID 를 찾는다 (facility_change 에 필요). 엔진 공개 도구에 이름 검색이 없어
  엔진 데이터 파일(preprocessed/facility.parquet)을 읽기만 한다. 엔진에 공개 도구가 생기면 바꾼다.
  같은 이름이 여러 곳에 있을 수 있어(예: 지내2리 경로당이 신북읍·동면에 하나씩) 주소와 함께 모두 돌려준다.

senior_industries (관리자 모드)
  어르신이 자주 쓰는 생활 업종 (설계 6절: 카드 근거를 운영안에 반영). 엔진에 업종 정보가 없어
  팀 EDA 결과표(outputs/tables, 신한카드 데이터1·2)를 읽기만 한다. 시군구 단위라 가게 위치는 알 수 없다.

반환 형식은 엔진 도구와 같다 (tool, region, result, evidence, caveats, figures, geojson, params).
"""
from __future__ import annotations

from functools import lru_cache

from agent.engine_client import ENGINE_DIR

SENIOR_HOURS = 'senior_hours'
_TIME_METRIC = 'senior60_card_time_'           # 엔진 region_context 의 시간대 evidence 이름

AGE_LABEL = '60대 이상'                          # 연령 표기 (화면에 써도 되는 이름)
SENIOR_HOURS_NOTE = f'시·구 전체의 {AGE_LABEL} 카드 결제 시간대 비중이다. 동네별 값이나 시설 운영 시간이 아니다.'

SCHEMAS = {
    SENIOR_HOURS: {
        'name': SENIOR_HOURS,
        'description': ('찾는 동네가 속한 시·구 전체에서 60대 이상 주민의 카드 결제가 많은 시간대를 알려준다. '
                        '어르신들이 밖에서 많이 활동하는 때라서, 모임이나 시설에 가기 좋은 시간을 안내할 때 참고로 쓴다. '
                        '시설 운영 시간이 아니다. 지역은 자동으로 들어간다.'),
        'input_schema': {'type': 'object', 'properties': {}, 'required': []},
    },
}


def slot_label(key: str) -> str:
    """엔진 시간대 키(예: 12_17)를 화면 표기(12~17시)로."""
    a, b = key.split('_')
    return f'{a}~{b}시'


def senior_hours(engine, args: dict) -> dict:
    src = engine.call('region_context', {'region': args['region']})
    times = src['result'].get('senior60_card_time_pct', {})
    return {
        'tool': SENIOR_HOURS, 'region': src['region'],
        'result': {'senior60_card_time_pct': times, 'slot_labels': {k: slot_label(k) for k in times},
                   'age_label': AGE_LABEL},
        'evidence': [e for e in src['evidence'] if e['metric'].startswith(_TIME_METRIC)],
        'caveats': [SENIOR_HOURS_NOTE],
        'figures': [], 'geojson': None, 'params': {},
    }


FIND_FACILITY = 'find_facility'
FACILITY_FILE = ENGINE_DIR / 'preprocessed' / 'facility.parquet'
FACILITY_GROUPS = ('social', 'health')         # 엔진 자원 조회와 같은 범위 (민간 체육 등 제외 시설은 뺀다)
MAX_MATCHES = 10

SCHEMAS[FIND_FACILITY] = {
    'name': FIND_FACILITY,
    'description': ('시설 이름으로 시설을 찾아 시설 ID(fac_id)와 주소를 알려준다. "○○경로당이 문을 닫으면?"처럼 '
                    '시설 변화 가정(facility_change)에 시설 ID 가 필요할 때 먼저 쓴다. 같은 이름이 여러 곳에 있으면 모두 돌려준다.'),
    'input_schema': {'type': 'object', 'properties': {
        'region': {'type': 'string', 'description': '분석 지역 (목록은 tools.py 가 엔진 스키마에서 채운다)'},
        'name': {'type': 'string', 'description': '시설 이름 (일부만 써도 된다. 띄어쓰기는 무시한다)'}},
        'required': ['region', 'name']},
}


@lru_cache(maxsize=1)
def _facilities():
    import pandas as pd
    f = pd.read_parquet(FACILITY_FILE)
    f = f[f.group.isin(FACILITY_GROUPS)].copy()
    f['key'] = f.name.fillna('').str.replace(' ', '')
    return f


def find_facility(engine, args: dict) -> dict:
    region, query = args['region'], args.get('name', '')
    f = _facilities()
    key = query.replace(' ', '')
    hit = f[(f.region == region) & f.key.str.contains(key, regex=False)] if key else f.iloc[0:0]
    rows = [{'fac_id': r.fac_id, 'kind': r.kind, 'name': r.name, 'addr': r.addr if isinstance(r.addr, str) else None,
             'lat': round(float(r.lat), 4), 'lon': round(float(r.lon), 4)} for r in hit.head(MAX_MATCHES).itertuples()]
    return {
        'tool': FIND_FACILITY, 'region': region,
        'result': {'matches': rows, 'n_matches': len(hit)},
        'evidence': [{'metric': 'n_matches', 'value': len(hit)}],
        'caveats': ['시설 이름 검색은 엔진 시설 목록(경로당·마을회관·도서관·공공체육·문화시설·보건기관)에서 찾는다.'],
        'figures': [], 'geojson': None, 'params': {'query': query},
    }


SENIOR_INDUSTRIES = 'senior_industries'
TABLE_DIR = ENGINE_DIR.parent / 'outputs' / 'tables'
INDUSTRY_TABLES = {   # 지역: (60대 이상 비중 상위 업종 표, 업종별 로컬 결제 비율 상·하위 표)
    '춘천': ('19_춘천__60대__비중_상위_10_업종.csv', '23_춘천__업종별_로컬_결제_비율_____상_하위_8.csv'),
    '강남': ('18_강남__60대__비중_상위_10_업종.csv', '24_강남__업종별_로컬_결제_비율_____상_하위_8.csv'),
}
LOCAL_TOP = 8                                  # 로컬 비율 표는 앞 8줄이 상위, 뒤 8줄이 하위
INDUSTRY_NOTE = '카드 업종 값은 시·구 전체 결제 기준이다. 업종 가게의 위치는 알 수 없다.'
INDUSTRY_NOTE_SHARE = '60대 이상 비중은 그 업종 결제 중 60대 이상 카드 결제의 비율이다.'

SCHEMAS[SENIOR_INDUSTRIES] = {
    'name': SENIOR_INDUSTRIES,
    'description': ('어르신(60대 이상)이 자주 쓰는 생활 업종과 지역 주민 이용 비율이 높은 업종을 알려준다 (카드 결제, 시·구 단위). '
                    '운영안에서 안내문을 둘 곳이나 함께 알릴 곳(예: 약국·의원·시장)을 제안할 때 쓴다. 가게 위치는 알 수 없다.'),
    'input_schema': {'type': 'object', 'properties': {
        'region': {'type': 'string', 'description': '분석 지역 (목록은 tools.py 가 엔진 스키마에서 채운다)'}},
        'required': ['region']},
}


def senior_industries(engine, args: dict) -> dict:
    import pandas as pd
    region = args['region']
    if region not in INDUSTRY_TABLES:
        return {'tool': SENIOR_INDUSTRIES, 'region': region, 'result': {'error': f'업종 표가 없는 지역: {region}'},
                'evidence': [], 'caveats': [], 'figures': [], 'geojson': None, 'params': {}}
    senior_f, local_f = INDUSTRY_TABLES[region]
    sen = pd.read_csv(TABLE_DIR / senior_f, encoding='utf-8-sig')
    loc = pd.read_csv(TABLE_DIR / local_f, encoding='utf-8-sig').head(LOCAL_TOP)
    sen = sen[~sen.MCT_RY_CD.str.startswith('ZZ_')]           # '나머지' 묶음은 업종이 아니다
    loc = loc[~loc.MCT_RY_CD.str.startswith('ZZ_')]
    senior_top = [{'industry': r.MCT_RY_CD, 'senior_pct': float(r[1])} for r in sen.itertuples(index=False)]
    local_top = [{'industry': r.MCT_RY_CD, 'local_pct': float(r[1])} for r in loc.itertuples(index=False)]
    both = [x['industry'] for x in senior_top if x['industry'] in {y['industry'] for y in local_top}]
    return {
        'tool': SENIOR_INDUSTRIES, 'region': region,
        'result': {'senior_top': senior_top, 'local_top': local_top, 'everyday_senior': both,
                   'industries': list(dict.fromkeys([x['industry'] for x in senior_top + local_top]))},
        'evidence': [{'metric': f"senior_pct_{x['industry']}", 'value': x['senior_pct']} for x in senior_top] +
                    [{'metric': f"local_pct_{x['industry']}", 'value': x['local_pct']} for x in local_top],
        'caveats': [INDUSTRY_NOTE, INDUSTRY_NOTE_SHARE],
        'figures': [], 'geojson': None,
        'params': {'source': f'팀 EDA 결과표 {senior_f}, {local_f}'},
    }


from agent.field_check import FIELD_CHECK, field_check                     # noqa: E402 (현장 확인 목록, 별도 파일)
from agent.field_check import SCHEMA as _FIELD_CHECK_SCHEMA                  # noqa: E402

from agent.compare import COMPARE, compare_interventions                   # noqa: E402 (세 개입안 비교, 별도 파일)
from agent.compare import SCHEMA as _COMPARE_SCHEMA                          # noqa: E402

SCHEMAS[FIELD_CHECK] = _FIELD_CHECK_SCHEMA
SCHEMAS[COMPARE] = _COMPARE_SCHEMA
RUNNERS = {SENIOR_HOURS: senior_hours, FIND_FACILITY: find_facility, FIELD_CHECK: field_check,
           COMPARE: compare_interventions, SENIOR_INDUSTRIES: senior_industries}


def call_tool(engine, name: str, args: dict) -> dict:
    """에이전트 도구면 에이전트가 처리하고, 아니면 엔진 도구를 그대로 부른다."""
    return RUNNERS[name](engine, args) if name in RUNNERS else engine.call(name, args)
