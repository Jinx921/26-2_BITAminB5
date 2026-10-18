"""외곽 시설 대체 (엔진 10/18 fallback_nearby): 반경 안 시설이 없어도 가장 가까운 시설을 지도·카드로 보여준다."""
from agent.digest import Digester
from agent.screen import build_screen
from agent.store import ResultStore
from agent.verifier import Context

NEAR = {'fac_id': 'CC_00001', 'kind': '경로당', 'group': 'social', 'name': '사암3리 경로당', 'addr': None,
        'dist_m': 2300.0, 'lat': 37.97, 'lon': 127.62, 'beyond_radius': True}


def _ctx(result, mode='citizen'):
    st = ResultStore()
    st.put('lookup_resources', {'region': '춘천'}, {'tool': 'lookup_resources', 'region': '춘천', 'result': result,
                                                   'evidence': [], 'caveats': [], 'figures': [], 'geojson': None,
                                                   'params': {'radius_m': 1000}})
    return Context(st, {}, {}, '근처에 갈 곳?', mode)


def _lookup(within, fallback):
    nearest = [{k: NEAR[k] for k in ('kind', 'name', 'dist_m', 'addr', 'lat', 'lon')}]
    return {'nearest_by_kind': nearest, 'within_radius': within, 'count_within_radius': {}, 'fallback_nearby': fallback}


def test_empty_radius_uses_fallback_points():
    d = build_screen('근처에 갈 곳?', 'citizen', None, None, _ctx(_lookup([], [NEAR])))['display']
    p = d['map']['points'][0]
    assert d['map']['layer'] == 'facilities' and p['id'] == 'CC_00001' and p['dist_m'] == 2300.0   # 카드·요청 버튼에 필요한 값


def test_within_radius_still_preferred():
    inside = {**NEAR, 'fac_id': 'CC_00002', 'name': '가까운 경로당', 'dist_m': 400.0, 'beyond_radius': False}
    d = build_screen('근처에 갈 곳?', 'citizen', None, None, _ctx(_lookup([inside], [NEAR])))['display']
    assert [p['id'] for p in d['map']['points']] == ['CC_00002']


def test_no_facility_nearby_means_no_map():
    d = build_screen('근처에 갈 곳?', 'citizen', None, None, _ctx(_lookup([], [])))['display']
    assert d['map'] is None


def test_digest_mentions_fallback_without_numbers():
    st = _ctx(_lookup([], [NEAR])).store
    text = Digester()(st.get('r1')).text
    assert '반경 안 시설은 없다' in text and '5km' not in text and '5000' not in text   # 인용할 수 없는 숫자는 넣지 않는다
