"""세 개입안 비교 (설계 차별점 ①): 같은 기준으로 비교한다.

공통 지표: 긴급방문형 동네 중 해소되는 동네 수
  ① 기존 시설 안내     유형 분류 기본 결과 (기준선, 해소 0)
  ② 경로당 거점 프로그램 이동형 거점마다 가장 가까운 경로당에 보건 기능을 더한다 (facility_change, kind=보건)
                       → 다른 유형으로 바뀌는 긴급방문형 동네 수
  ③ 이동형 서비스 배치   배치 시뮬레이션 (simulate_placement) → 반경 안에 드는 긴급방문형 동네 수

②와 ③을 같은 수·같은 동네로 맞춰 "서비스를 동네로 보낼지, 동네 경로당을 거점으로 키울지"를 비교한다.
엔진 공개 도구만 조합한다. 이용량·운영 비용·고립 감소 효과는 계산하지 않는다 (접근성만).
"""
from __future__ import annotations

import math

COMPARE = 'compare_interventions'
OPTION_NAMES = {'baseline': '기존 시설 안내', 'hub': '경로당 거점 프로그램', 'mobile': '이동형 서비스 배치'}
ACCESS_NOTE = '세 안은 접근성(닿을 수 있는지)만 비교했다. 이용량·운영 비용·고립 감소 효과는 계산하지 않았다.'
HUB_NOTE = '경로당 거점 프로그램은 거점 경로당에 방문 간호·건강상담 같은 보건 기능을 더한다고 가정했다.'
HUB_RULE = '이동형 거점마다 가장 가까운 경로당'

SCHEMA = {
    'name': COMPARE,
    'description': ('세 가지 개입안을 같은 기준(가장 먼저 방문이 필요한 동네 중 해소되는 동네 수)으로 비교한다: '
                    '기존 시설 안내 / 경로당 거점 프로그램(경로당에 보건 기능 추가) / 이동형 서비스 배치. '
                    '"어떤 방식이 좋아?", "이동형이랑 경로당 거점 중 뭐가 나아?"에 쓴다. 거점 수와 반경은 질문에 있으면 넣는다.'),
    'input_schema': {'type': 'object', 'properties': {
        'region': {'type': 'string', 'description': '분석 지역 (목록은 tools.py 가 엔진 스키마에서 채운다)'},
        'k': {'type': 'integer', 'minimum': 1, 'maximum': 10, 'description': '거점 수. 없으면 엔진 기본값'},
        'radius_m': {'type': 'integer', 'description': '이동형 서비스 반경(m). 도보 500·1000, 차량 약 3000. 없으면 엔진 기본값'}},
        'required': ['region']},
}


def _nearest_hall(halls, lat: float, lon: float):
    """가장 가까운 경로당 (위경도 근사 거리)."""
    c = math.cos(math.radians(lat))
    d = ((halls.lat - lat) ** 2 + ((halls.lon - lon) * c) ** 2)
    return halls.loc[d.idxmin()]


def compare_interventions(engine, args: dict) -> dict:
    from agent.agent_tools import _facilities
    region = args['region']
    sim_args = {'region': region, **{k: args[k] for k in ('k', 'radius_m') if args.get(k)}}
    cl = engine.call('classify', {'region': region})
    sim = engine.call('simulate_placement', sim_args)
    if 'error' in sim['result'] or 'message' in sim['result']:
        return {**sim, 'tool': COMPARE}
    n0 = cl['result']['type_counts']['긴급방문형']
    k, radius = sim['params']['k'], sim['params']['radius_m']
    sites = sim['result']['chosen_sites']

    halls = _facilities()
    halls = halls[(halls.region == region) & (halls.kind == '경로당')]
    hubs = {}
    for s in sites:
        h = _nearest_hall(halls, s['lat'], s['lon'])
        hubs.setdefault(h.fac_id, {'name': h['name'], 'lat': round(float(h.lat), 4), 'lon': round(float(h.lon), 4),
                                   'emd_name': s['emd_name']})
    fc = engine.call('facility_change', {'region': region, 'add_points': [
        {'lat': h['lat'], 'lon': h['lon'], 'kind': '보건', 'name': h['name']} for h in hubs.values()]})
    hub_resolved = sum(v for b, t in fc['result']['transitions'].items() if b == '긴급방문형'
                       for a, v in t.items() if a != b)
    mobile_resolved = sim['result']['covered_cells']

    options = [
        {'key': 'baseline', 'name': OPTION_NAMES['baseline'], 'resolved': 0, 'remaining': n0, 'where': []},
        {'key': 'hub', 'name': OPTION_NAMES['hub'], 'resolved': hub_resolved, 'remaining': n0 - hub_resolved,
         'where': list(dict.fromkeys(h['emd_name'] for h in hubs.values()))},
        {'key': 'mobile', 'name': OPTION_NAMES['mobile'], 'resolved': mobile_resolved, 'remaining': n0 - mobile_resolved,
         'where': list(dict.fromkeys(s['emd_name'] for s in sites))},
    ]
    points = ([{'id': s['cell_id'], 'lat': s['lat'], 'lon': s['lon'], 'emd_name': s['emd_name'],
                'option': OPTION_NAMES['mobile'], 'name': f"이동형 거점 ({s['emd_name']})"} for s in sites] +
              [{'id': fid, 'lat': h['lat'], 'lon': h['lon'], 'emd_name': h['emd_name'],
                'option': OPTION_NAMES['hub'], 'name': f"경로당 거점 ({h['emd_name']})",
                'facility_name': h['name']} for fid, h in hubs.items()])     # 원천 시설명은 알아보기 어려울 수 있어 따로 둔다
    caveats = [ACCESS_NOTE, HUB_NOTE] + [c for c in sim['caveats'] + cl['caveats'] if c not in (ACCESS_NOTE, HUB_NOTE)]
    return {
        'tool': COMPARE, 'region': region,
        'result': {'options': options, 'n_urgent': n0, 'map_points': points},
        'evidence': [{'metric': 'n_urgent', 'value': n0},
                     {'metric': 'resolved_baseline', 'value': 0},
                     {'metric': 'resolved_hub', 'value': hub_resolved},
                     {'metric': 'resolved_mobile', 'value': mobile_resolved},
                     {'metric': 'remaining_hub', 'value': n0 - hub_resolved},
                     {'metric': 'remaining_mobile', 'value': n0 - mobile_resolved}],
        'caveats': list(dict.fromkeys(caveats)),
        'figures': [], 'geojson': None,
        'params': {'k': k, 'radius_m': radius, 'hub_rule': HUB_RULE},
    }
