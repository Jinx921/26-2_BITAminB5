"""Sonnet 에게 주는 도구 목록과 모드별 권한.

- 엔진 도구 정의는 engine/tool_schemas.py 를 그대로 불러온다 (엔진 파일은 수정하지 않는다)
- 기준값 인자(LOCKED_ARGS)는 스키마에서 뺀다. Sonnet 이 기준을 바꿔 다시 계산하지 못하게 해서
  답변이 항상 엔진 기본값 기준이 되게 한다. 기준을 바꾼 결과는 robustness 가 보여준다
- 모드별로 도구 목록을 나누고, 목록에 없는 도구는 실행 단계에서도 거절한다
- submit_answer: Sonnet 이 최종 답변을 내는 도구. 엔진으로 가지 않고 검증 단계로 간다
  · 화면에 보이는 부분(headline, details, caution)은 결론과 설명만 쉬운 말로 쓴다
  · 내부 기록(caveats_reflected, citations, map_ref)은 검증·백엔드용이며 화면에 그리지 않는다
"""
from __future__ import annotations

import copy
import importlib
import sys

from agent.agent_tools import SCHEMAS as AGENT_SCHEMAS
from agent.agent_tools import SENIOR_HOURS
from agent.engine_client import ENGINE_DIR

# Sonnet 이 바꾸지 못하게 스키마에서 빼는 기준값 인자
LOCKED_ARGS = {
    'find_candidates': ('persist_min', 'residential_filter'),
    'classify': ('far_social_m', 'far_health_m'),
}

# 모드별로 코드가 채우는 인자: Sonnet 이 정하지 못하게 스키마에서 빼고, 실행할 때 앱이 준 위치로 채운다
FIXED_ARGS = {
    'citizen': {'lookup_resources': ('region', 'lat', 'lon', 'cell_id'), SENIOR_HOURS: ('region',)},
}

# 모드별 엔진 도구. 엔진에 새 도구가 생기면 여기서 어느 모드에 줄지 정해야 한다 (테스트가 확인)
MODE_TOOLS = {
    'admin': ('find_candidates', 'check_residential', 'lookup_resources', 'classify',
              'simulate_placement', 'robustness', 'facility_change', 'region_context'),
    # 시민 모드: 위험 판정이 나올 수 있는 도구는 넣지 않는다.
    # region_context 는 결과에 유형별 칸 수(type_counts)가 들어 있어 시민 모드에서 빼고,
    # 시간대만 꺼내는 에이전트 도구(senior_hours)를 대신 준다
    'citizen': ('lookup_resources', SENIOR_HOURS),
}

SUBMIT = 'submit_answer'

_SOURCE = {
    'type': 'object',
    'properties': {
        'ref': {'type': 'string', 'description': '숫자가 나온 도구 결과 번호 (예: r2)'},
        'metric': {'type': 'string',
                   'description': 'evidence 의 metric 이름 그대로, 또는 params.<이름> (예: n_긴급방문형, params.far_social_m)'},
    },
    'required': ['ref', 'metric'],
    'additionalProperties': False,
}

SUBMIT_SCHEMA = {
    'name': SUBMIT,
    'description': ('최종 답변을 제출한다. 필요한 도구를 모두 부른 뒤 마지막에 한 번 부른다. '
                    'headline·details·caution 은 사용자 화면에 그대로 보이므로 결론과 설명만 쉬운 말로 쓴다. '
                    '정보량은 줄이지 않되, 긴 문장은 여러 짧은 문장으로 나눠 한 문장에 한 가지 내용만 쓴다 '
                    '(도구 이름, 지표 이름, 결과 번호, 분석 기준값, 계산 과정은 쓰지 않는다). '
                    '이 세 곳에 쓴 숫자는 하나도 빠짐없이 citations 에 출처를 적는다.'),
    'strict': True,
    'input_schema': {
        'type': 'object',
        'properties': {
            'headline': {'type': 'string',
                         'description': '결론 한두 문장: 어디를 먼저, 무엇을 하면 좋은지'},
            'details': {'type': 'string',
                        'description': '결론을 구체적으로 설명한다. 짧게 끝내지 않는다: 왜 그곳인지, 그 동네가 어떤 상황인지, '
                                       '어떤 도움을 어떻게 하면 좋은지를 쉬운 말로 여러 문장에 걸쳐 쓴다. '
                                       '설명할 내용은 빠짐없이 쓰되, 긴 문장은 짧은 문장 여러 개로 나누고 내용이 바뀌면 줄을 바꾼다'},
            'caution': {'type': 'string',
                        'description': '사용자가 알아두거나 확인할 점을 쉬운 말로 (예: 방문 전 현장 확인). 없으면 빈 문자열'},
            'caveats_reflected': {'type': 'array', 'items': {'type': 'string'},
                                  'description': '도구 결과의 caveats 중 답변에 쉬운 말로 반영한 것의 번호 (예: c1, c6)'},
            'citations': {
                'type': 'array',
                'description': '화면 문장에 쓴 숫자마다 하나씩 (화면에는 보이지 않는 내부 기록)',
                'items': {
                    'type': 'object',
                    'properties': {
                        'text': {'type': 'string', 'description': '답변에 쓴 숫자 표기 그대로 (예: 55, 1,361, 3km, 27%)'},
                        'op': {'type': 'string', 'enum': ['value', 'ratio', 'percent', 'diff', 'sum'],
                               'description': 'value: 출처 값 그대로. 그 밖에는 sources 값으로 계산한 수 '
                                              '(ratio·percent: 첫째÷둘째, diff: 첫째-둘째, sum: 합)'},
                        'sources': {'type': 'array', 'items': _SOURCE},
                    },
                    'required': ['text', 'op', 'sources'],
                    'additionalProperties': False,
                },
            },
            'map_ref': {'type': 'string', 'description': '지도에 그릴 도구 결과 번호 (예: r2). 없으면 빈 문자열'},
        },
        'required': ['headline', 'details', 'caution', 'caveats_reflected', 'citations', 'map_ref'],
        'additionalProperties': False,
    },
}


def _engine_schemas() -> list[dict]:
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    return copy.deepcopy(importlib.import_module('tool_schemas').SCHEMAS)   # 엔진 쪽 원본은 건드리지 않는다


def _lock(schema: dict, mode: str = 'admin') -> dict:
    locked = LOCKED_ARGS.get(schema['name'], ()) + FIXED_ARGS.get(mode, {}).get(schema['name'], ())
    props = schema['input_schema']['properties']
    for arg in locked:
        props.pop(arg, None)
    req = schema['input_schema'].get('required', [])
    schema['input_schema']['required'] = [r for r in req if r not in locked]
    return schema


def tools_for(mode: str) -> list[dict]:
    """모드에 맞는 Claude tool 정의 목록 (엔진 도구 + submit_answer). 순서는 엔진 스키마 순서로 고정."""
    if mode not in MODE_TOOLS:
        raise ValueError(f'없는 모드: {mode}')
    allowed = MODE_TOOLS[mode]
    engine = [_lock(s, mode) for s in _engine_schemas() if s['name'] in allowed]
    agent = [copy.deepcopy(s) for n, s in AGENT_SCHEMAS.items() if n in allowed]
    return engine + agent + [copy.deepcopy(SUBMIT_SCHEMA)]


def is_allowed(mode: str, tool: str) -> bool:
    """실행 직전 확인: 모드 목록에 없는 도구 호출은 거절한다."""
    return tool == SUBMIT or tool in MODE_TOOLS.get(mode, ())


def strip_locked(tool: str, args: dict, mode: str = 'admin') -> tuple[dict, list[str]]:
    """스키마에서 뺀 인자가 그래도 들어오면 버린다. (정리된 인자, 버린 기준값 인자 이름)
    모드별로 코드가 채우는 인자(FIXED_ARGS)도 버리지만, 기준값이 아니므로 버린 목록에는 넣지 않는다."""
    locked = LOCKED_ARGS.get(tool, ())
    fixed = FIXED_ARGS.get(mode, {}).get(tool, ())
    dropped = [a for a in args if a in locked]
    return {k: v for k, v in args.items() if k not in locked and k not in fixed}, dropped


def service_regions() -> list[str]:
    """엔진이 다루는 지역 (엔진 스키마의 region 목록)."""
    s = next(s for s in _engine_schemas() if s['name'] == 'lookup_resources')
    return list(s['input_schema']['properties']['region']['enum'])


if __name__ == '__main__':
    # 예: python -m agent.tools
    import json

    original = {s['name']: s for s in _engine_schemas()}
    for mode in MODE_TOOLS:
        print(f'===== {mode} 모드 =====')
        for t in tools_for(mode):
            props = list(t['input_schema']['properties'])
            removed = [a for a in original.get(t['name'], t)['input_schema']['properties'] if a not in props]
            note = f'  (뺀 인자: {", ".join(removed)})' if removed else ''
            print(f"  {t['name']:20} 인자: {', '.join(props)}{note}")
        print()
    print('===== submit_answer 입력 예 =====')
    print(json.dumps({
        'headline': '...을 먼저 확인하세요...',
        'details': '...긴급방문형(가장 먼저 방문이 필요한 동네) N곳... (여러 문장)',
        'caution': '...방문 전 현장 확인...',
        'caveats_reflected': ['c1', 'c6'],
        'citations': [{'text': 'N', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'n_긴급방문형'}]}],
        'map_ref': 'r2'}, ensure_ascii=False, indent=1))
