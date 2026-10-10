"""현장 확인 목록 (설계 차별점 ④): 기준을 현실적인 범위에서 바꾸면 판정이 흔들리는 동네와 동네별 확인 질문.

지금 긴급방문형인 동네마다, 기준값을 엔진 기본값 ±20%(위축 개월은 +1)로 바꾼 모든 조합에서 다시 계산해
긴급방문형으로 남는 비율(안정도)을 센다. 안정도가 낮은 동네만 목록에 넣고, 기준 하나만 바꿨을 때 판정이 바뀌는
기준을 흔들리는 이유로 보아 확인 질문을 붙인다.

엔진 공개 도구에 칸별 결과가 없어 엔진 내부 함수 core._universe 를 쓴다 (설계 4절에서 정한 유일한 예외).
극단값은 넣지 않는다: 넣으면 거의 모든 동네가 흔들려 목록이 쓸모없어진다 (결과 전체의 민감도는 robustness 가 보여준다).
"""
from __future__ import annotations

import importlib
import itertools

FIELD_CHECK = 'field_check'
VARY = 0.2                      # 거리·주택 기준을 기본값의 ±20% 로 바꾼다
STABLE = 0.8                    # 이 비율 이상 유지되면 '안정' (목록에서 뺀다)
MUST_CHECK = 0.5                # 이 비율 미만이면 '꼭 확인', 그 사이는 '확인 필요'

PARAMS = ('far_social_m', 'far_health_m', 'persist_min', 'housing_thr')
REASON_LABEL = {'housing_thr': '주택 수 기준', 'far_social_m': '교류시설 거리',
                'far_health_m': '보건기관 거리', 'persist_min': '낮 외출이 줄어든 기간'}
QUESTION = {
    'housing_thr': '실제로 사람이 사는 집이 있나요?',
    'far_social_m': '가까운 경로당·마을회관까지 실제로 걸어가기 어려운가요?',
    'far_health_m': '보건소·보건진료소까지 실제로 가기 어려운가요?',
    'persist_min': '낮에 어르신이 밖에 나오시나요?',
}
QUESTION_MIXED = '동네 상황을 전반적으로 확인해 주세요.'
NOTE = ('확인 수준은 기준을 현실적인 범위에서 바꿔 다시 계산했을 때 판정이 유지되는 정도다. '
        '현장 확인 결과가 최종이다.')

SCHEMA = {
    'name': FIELD_CHECK,
    'description': ('현장 확인 목록을 만든다: 가장 먼저 방문이 필요한 동네(긴급방문형) 중 기준을 조금만 바꿔도 판정이 흔들리는 동네와 '
                    '동네별 확인 질문, 방문 순서. "현장 확인 목록 만들어 줘", "어느 동네가 확실하지 않아?"에 쓴다.'),
    'input_schema': {'type': 'object', 'properties': {
        'region': {'type': 'string', 'description': '분석 지역 (목록은 tools.py 가 엔진 스키마에서 채운다)'}},
        'required': ['region']},
}


def _engine_modules(engine):
    core = getattr(engine, '_core', None)
    if core is None:
        return None, None
    return core, importlib.import_module('config')


def _options(C, region: str) -> dict:
    s, h, p, ht = C.FAR_SOCIAL_M, C.FAR_HEALTH_M, C.PERSIST_MIN, C.HOUSING_THR[region]
    return {'far_social_m': [s * (1 - VARY), s, s * (1 + VARY)],
            'far_health_m': [h * (1 - VARY), h, h * (1 + VARY)],
            'persist_min': [p, p + 1],
            'housing_thr': [ht * (1 - VARY), ht, ht * (1 + VARY)]}


def field_check(engine, args: dict) -> dict:
    region = args['region']
    core, C = _engine_modules(engine)
    if core is None:                                        # 예시 응답 엔진에는 칸별 계산이 없다
        return {'tool': FIELD_CHECK, 'region': region, 'result': {'error': '현장 확인 목록은 실제 엔진 데이터가 필요하다'},
                'evidence': [], 'caveats': [], 'figures': [], 'geojson': None, 'params': {}}
    opts = _options(C, region)
    default = {k: v[1] if k != 'persist_min' else v[0] for k, v in opts.items()}
    base = core._universe(region)
    urgent0 = base[base.type == '긴급방문형'].set_index('cell_id')

    combos = [dict(zip(PARAMS, vals)) for vals in itertools.product(*(opts[k] for k in PARAMS))]
    urgent_in = []                                          # 조합마다 긴급방문형 칸 집합
    for c in combos:
        u = core._universe(region, **c)
        urgent_in.append(set(u.cell_id[u.type == '긴급방문형']))

    rows = []
    for cid, r in urgent0.iterrows():
        stab = sum(cid in s for s in urgent_in) / len(combos)
        if stab >= STABLE:
            continue
        reasons = []
        for k in PARAMS:                                    # 이 기준 하나만 바꿨을 때 판정이 바뀌나
            alone = [i for i, c in enumerate(combos) if all(c[o] == default[o] for o in PARAMS if o != k) and c[k] != default[k]]
            if any(cid not in urgent_in[i] for i in alone):
                reasons.append(k)
        rows.append({'cell_id': cid, 'emd_name': r.emd_name, 'lat': round(float(r.lat), 4), 'lon': round(float(r.lon), 4),
                     'level': '꼭 확인' if stab < MUST_CHECK else '확인 필요', 'stability': round(stab, 4),
                     'reasons': [REASON_LABEL[k] for k in reasons],
                     'questions': [QUESTION[k] for k in reasons] or [QUESTION_MIXED]})

    # 방문 순서: 확인할 동네가 많은 행정동부터 묶고, 같은 동 안에서는 꼭 확인 → 확인 필요, 안정도 낮은 순
    per_emd = {}
    for r in rows:
        per_emd[r['emd_name']] = per_emd.get(r['emd_name'], 0) + 1
    rows.sort(key=lambda r: (-per_emd[r['emd_name']], r['emd_name'], r['level'] != '꼭 확인', r['stability']))
    for i, r in enumerate(rows, 1):
        r['order'] = i
    must = sum(r['level'] == '꼭 확인' for r in rows)
    reason_counts = {}
    for r in rows:
        for x in r['reasons'] or ['여러 기준이 겹침']:
            reason_counts[x] = reason_counts.get(x, 0) + 1
    return {
        'tool': FIELD_CHECK, 'region': region,
        'result': {'cells': rows, 'by_emd': per_emd, 'reason_counts': reason_counts,
                   'n_default_urgent': len(urgent0), 'n_check': len(rows), 'n_must_check': must},
        'evidence': [{'metric': 'n_default_urgent', 'value': len(urgent0)},
                     {'metric': 'n_check', 'value': len(rows)},
                     {'metric': 'n_must_check', 'value': must},
                     {'metric': 'n_need_check', 'value': len(rows) - must},
                     {'metric': 'n_stable', 'value': len(urgent0) - len(rows)}],
        'caveats': [NOTE],
        'figures': [], 'geojson': None,
        'params': {'ranges': {k: [round(x, 4) for x in v] for k, v in opts.items()}, 'n_combos': len(combos),
                   'stable': STABLE, 'must_check': MUST_CHECK},
    }
