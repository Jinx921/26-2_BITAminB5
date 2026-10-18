"""시민 모드 1단계: 위치 → 서비스 지역 판단, 위치는 코드가 채움, 내부 기록에서 위치 가림."""
import copy
import json

import pytest

from agent.engine_client import ENGINE_DIR, FIXTURE_DIR, FixtureEngine, LiveEngine
from agent.location import cell_of, detect_region, region_by_boundary
from agent.screen import CITIZEN_NOTICE
from agent.tools import service_regions, tools_for

LOOKUP_EXAMPLE = json.loads(next(FIXTURE_DIR.glob('lookup_resources_*.json')).read_text(encoding='utf-8'))


class StubEngine(FixtureEngine):
    """칸 소속은 정해 둔 목록으로 답하고, 위치로 부르는 자원 조회는 예시 응답을 돌려준다."""
    def __init__(self, cells):
        super().__init__()
        self.cells, self.called = cells, []

    def call(self, tool, args):
        self.called.append((tool, dict(args)))
        if tool == 'lookup_resources' and 'cell_id' in args:
            ok = args['cell_id'] in self.cells.get(args['region'], set())
            return {'result': {} if ok else {'error': f"{args['region']}에 없는 칸"}}
        if tool == 'lookup_resources':
            return copy.deepcopy(LOOKUP_EXAMPLE)
        return super().call(tool, args)


def _cid(lat, lon):
    return '{}_{}'.format(*cell_of(lat, lon))


def test_cell_rule_matches_engine_ids():
    """칸 ID = UTM-K 좌표 ÷ 250m 몫 (예시 응답의 칸 좌표로 확인)."""
    for f in FIXTURE_DIR.glob('classify_*.json'):
        for r in json.loads(f.read_text(encoding='utf-8'))['result']['table'][:20]:
            assert _cid(r['lat'], r['lon']) == r['cell_id']


def test_service_regions_from_engine_schema():
    assert service_regions() and all(isinstance(r, str) for r in service_regions())


def test_detect_region_own_cell_and_neighbor():
    lat, lon = 37.88, 127.73
    cx, cy = cell_of(lat, lon)
    own = StubEngine({'춘천': {f'{cx}_{cy}'}})
    assert detect_region(own, lat, lon, ['강남', '춘천']) == '춘천'
    neighbor = StubEngine({'춘천': {f'{cx + 1}_{cy}'}})                  # 자기 칸이 없고 옆 칸만 있음
    assert detect_region(neighbor, lat, lon, ['강남', '춘천']) == '춘천'
    lat2, lon2 = 37.5665, 126.9780                                      # 서울시청 (두 지역 경계 밖)
    cx2, cy2 = cell_of(lat2, lon2)
    far = StubEngine({'강남': {f'{cx2 + 2}_{cy2}'}})                     # 두 칸 떨어지고 경계도 밖이면 지역 밖
    assert detect_region(far, lat2, lon2, ['강남', '춘천']) is None


def test_detect_region_boundary_fallback():
    """근처에 통신 칸이 없어도 시군구 경계 안이면 그 지역 (10/18 외곽 마을)."""
    lat, lon = 37.9925, 127.9010                                        # 춘천 북산면 추전리
    assert detect_region(StubEngine({}), lat, lon, ['강남', '춘천']) == '춘천'
    assert detect_region(StubEngine({}), lat, lon, ['강남']) is None     # 서비스 지역 목록에 없으면 밖


@pytest.mark.parametrize('lat, lon, expected', [
    (37.9925, 127.9010, '춘천'),        # 북산면 추전리
    (37.9690, 127.6380, '춘천'),        # 사북면
    (37.7480, 127.6450, '춘천'),        # 남산면
    (37.5006, 127.0364, '강남'),        # 역삼역 (강남역은 강남대로가 구 경계라 좌표가 서초 쪽)
    (37.4650, 127.1050, '강남'),        # 세곡동 부근
    (37.5133, 127.1001, None),          # 송파 잠실
    (37.5045, 127.0050, None),          # 서초 반포
    (37.8310, 127.5100, None),          # 가평읍
    (38.1060, 127.7080, None),          # 화천읍
    (37.6970, 127.8890, None),          # 홍천읍
])
def test_region_by_boundary(lat, lon, expected):
    assert region_by_boundary(lat, lon, ['강남', '춘천']) == expected


@pytest.mark.skipif(not (ENGINE_DIR / 'preprocessed' / 'cell_master.parquet').exists(), reason='엔진 데이터 없음')
@pytest.mark.parametrize('lat, lon, expected', [
    (37.4979, 127.0276, '강남'),        # 강남역
    (37.8813, 127.7298, '춘천'),        # 춘천시청 부근
    (37.97, 127.62, '춘천'),            # 춘천 외곽, 자기 칸이 격자에 없음 → 옆 칸
    (37.5133, 127.1001, None),          # 송파 잠실 (강남 바로 옆)
    (37.5045, 127.0050, None),          # 서초 반포 (강남 바로 옆)
    (37.5665, 126.9780, None),          # 서울시청
])
def test_detect_region_live(lat, lon, expected):
    assert detect_region(LiveEngine(), lat, lon, service_regions()) == expected


def test_citizen_lookup_schema_has_no_location():
    lookup = next(t for t in tools_for('citizen') if t['name'] == 'lookup_resources')
    props = lookup['input_schema']['properties']
    assert set(props) == {'radius_m'} and lookup['input_schema']['required'] == []
    admin = next(t for t in tools_for('admin') if t['name'] == 'lookup_resources')
    assert {'region', 'lat', 'lon'} <= set(admin['input_schema']['properties'])      # 관리자 모드는 그대로


# ---------------------------------------------------------------- 오케스트레이터
def _citizen(responses, location, cells):
    from agent.orchestrator import Orchestrator
    from agent.tests.test_orchestrator import FakeClient
    client, engine = FakeClient(responses), StubEngine(cells)
    screen, turn = Orchestrator(engine, mode='citizen', client=client).ask('집 근처에 갈 만한 곳 있어요?', location)
    return screen, turn, client, engine


def test_no_location_and_out_of_area_skip_sonnet():
    screen, turn, client, _ = _citizen([], None, {})
    assert screen['display']['headline'] == CITIZEN_NOTICE['no_location'] and client.requests == []
    screen, turn, client, _ = _citizen([], {'lat': 37.5, 'lon': 127.0}, {})
    assert screen['display']['headline'] == CITIZEN_NOTICE['out_of_area'] and client.requests == []
    assert screen['display']['map'] is None and turn.end == 'out_of_area'


def test_location_filled_by_code_and_hidden_in_trace():
    from agent.tests.test_orchestrator import _resp, _use
    loc = {'lat': 37.8813, 'lon': 127.7298}
    cells = {'춘천': {_cid(**loc)}}
    sonnet_args = {'radius_m': 500, 'lat': 1.0, 'lon': 1.0, 'region': '강남'}   # Sonnet 이 위치를 넣어도 무시
    screen, turn, client, engine = _citizen([_resp(_use('lookup_resources', sonnet_args, 1)),
                                             _resp(stop='end_turn'), _resp(stop='end_turn')], loc, cells)
    called = [a for t, a in engine.called if t == 'lookup_resources' and 'cell_id' not in a]
    assert called == [{'radius_m': 500, 'region': '춘천', 'lat': loc['lat'], 'lon': loc['lon']}]
    first = client.requests[0]['messages'][0]['content']
    assert '찾는 위치는 춘천시 안' in first[1]['text'] and str(loc['lat']) not in json.dumps(first)   # 좌표는 Sonnet 에 안 감
    sent = json.dumps(client.requests, ensure_ascii=False)                # Sonnet 에 보낸 모든 요청 (도구 결과 포함)
    assert str(loc['lat']) not in sent and str(loc['lon']) not in sent
    trace = screen['internal']['tool_trace'][0]['args']
    assert trace['lat'] == trace['lon'] == '(사용자 위치)' and trace['region'] == '춘천'
