"""에이전트 쪽 도구: 엔진 도구를 감싸 필요한 값만 꺼낸다 (엔진 코드는 고치지 않는다).

senior_hours (시민 모드)
  엔진 region_context 에서 60대 이상 카드 결제 시간대만 꺼낸다.
  region_context 결과에는 유형별 칸 수(type_counts) 같은 위험 정보와 칸·유형 설명 caveat 가 있어
  시민 모드에 그대로 줄 수 없다. 시간대 값과 evidence 만 남기고, 한계 문장은 시민용으로 새로 붙인다.

반환 형식은 엔진 도구와 같다 (tool, region, result, evidence, caveats, figures, geojson, params).
"""
from __future__ import annotations

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


RUNNERS = {SENIOR_HOURS: senior_hours}


def call_tool(engine, name: str, args: dict) -> dict:
    """에이전트 도구면 에이전트가 처리하고, 아니면 엔진 도구를 그대로 부른다."""
    return RUNNERS[name](engine, args) if name in RUNNERS else engine.call(name, args)
