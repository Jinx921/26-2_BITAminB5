"""백엔드 연결 전 점검에서 찾은 문제: 지도 없는 안내 문구, 빈 지도, 비어 있는 위치 값."""
from agent.orchestrator import Orchestrator
from agent.screen import FALLBACK_TEXT, FALLBACK_TEXT_NO_MAP, build_screen
from agent.store import ResultStore
from agent.tests.test_orchestrator import FakeClient
from agent.verifier import Context

CHECK_ROW = {'cell_id': '1_1', 'emd_name': '신북읍', 'lat': 37.9, 'lon': 127.7, 'level': '꼭 확인',
             'questions': ['낮에 어르신이 밖에 나오시나요?'], 'order': 1}


def _ctx_with(tool, result):
    st = ResultStore()
    st.put(tool, {'region': '춘천'}, {'tool': tool, 'region': '춘천', 'result': result, 'evidence': [],
                                     'caveats': [], 'figures': [], 'geojson': None, 'params': {}})
    return Context(st, {}, {}, '질문', 'admin')


def test_fallback_map_from_field_check():
    """현장 확인 목록 질문이 검증에 실패해도 확인 목록 지도와 '지도에 표시' 문구가 함께 나간다."""
    d = build_screen('현장 확인 목록 만들어 줘', 'admin', None, None, _ctx_with('field_check', {'cells': [CHECK_ROW]}))['display']
    assert d['map']['layer'] == 'checks' and d['headline'] == FALLBACK_TEXT['admin']


def test_fallback_without_map_does_not_mention_map():
    d = build_screen('질문', 'admin', None, None, Context(ResultStore(), {}, {}, '질문', 'admin'))['display']
    assert d['map'] is None and d['headline'] == FALLBACK_TEXT_NO_MAP['admin'] and '지도' not in d['headline']
    d = build_screen('질문', 'citizen', None, None, Context(ResultStore(), {}, {}, '질문', 'citizen'))['display']
    assert d['map'] is None and d['headline'] == FALLBACK_TEXT_NO_MAP['citizen'] and '지도' not in d['headline']


def test_no_points_means_no_map():
    """오류 결과(점 0개)는 빈 지도 대신 지도 없음."""
    ctx = _ctx_with('lookup_resources', {'error': '강남에 없는 칸'})
    d = build_screen('질문', 'admin', None, None, ctx)['display']
    assert d['map'] is None and d['headline'] == FALLBACK_TEXT_NO_MAP['admin']


def test_empty_location_values_ask_for_location():
    for loc in ({'lat': None, 'lon': None}, {'lat': 37.88}, {}):
        screen, turn = Orchestrator(None, mode='citizen', client=FakeClient([])).ask('근처에 갈 곳?', loc)
        assert turn.end == 'no_location' and screen['internal']['run']['errors'] == []


def test_brief_skips_auto_robustness():
    """도구를 부른 뒤 짧은 답으로 끝나면 신뢰도용 강건성 점검을 부르지 않는다 (짧은 답에는 신뢰도가 없다)."""
    from agent.tests.test_orchestrator import SpyEngine, _resp, _use
    from agent.tools import SUBMIT_BRIEF
    engine = SpyEngine()
    client = FakeClient([_resp(_use('region_context', {'region': '춘천'}, 1)),
                         _resp(_use(SUBMIT_BRIEF, {'message': '부산은 아직 안내하지 않아요. 춘천과 강남을 물어봐 주세요.'}, 2))])
    screen, turn = Orchestrator(engine, client=client).ask('부산은 어때?')
    assert turn.end == 'passed' and [t for t, _ in engine.called] == ['region_context']
    assert screen['display']['confidence'] is None


def test_placement_map_carries_radius():
    """배치·개입안 비교 지도에는 반경이 함께 간다 (프론트가 배치 지도 반경을 답변에 맞춘다)."""
    st = ResultStore()
    st.put('simulate_placement', {'region': '춘천'}, {'tool': 'simulate_placement', 'region': '춘천', 'evidence': [], 'caveats': [],
                                                     'figures': [], 'geojson': None, 'params': {'k': 2, 'radius_m': 3000},
                                                     'result': {'chosen_sites': [{'cell_id': '1_1', 'lat': 37.9, 'lon': 127.7,
                                                                                  'emd_name': '사북면', 'covers': 10}]}})
    m = build_screen('질문', 'admin', None, None, Context(st, {}, {}, '질문', 'admin'))['display']['map']
    assert m['layer'] == 'sites' and m['radius_m'] == 3000
    assert 'radius_m' not in build_screen('질문', 'admin', None, None,
                                          _ctx_with('field_check', {'cells': [CHECK_ROW]}))['display']['map']
