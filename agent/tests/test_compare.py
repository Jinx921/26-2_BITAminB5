"""남은 일 3번: 세 개입안 비교."""
import pytest

from agent.agent_tools import call_tool
from agent.compare import COMPARE, OPTION_NAMES
from agent.digest import Digester
from agent.engine_client import ENGINE_DIR, LiveEngine
from agent.screen import _chart, _map
from agent.store import ResultStore
from agent.tools import tools_for
from agent.verifier import Context, REQUIRED_CAVEATS

live = pytest.mark.skipif(not (ENGINE_DIR / 'preprocessed' / 'cell_master.parquet').exists(), reason='엔진 데이터 없음')


@pytest.fixture(scope='module')
def eng():
    return LiveEngine()


@live
@pytest.mark.parametrize('region, k, radius', [('춘천', 3, 1000), ('춘천', 3, 3000), ('강남', 2, 1000)])
def test_numbers_match_engine_tools(eng, region, k, radius):
    r = call_tool(eng, COMPARE, {'region': region, 'k': k, 'radius_m': radius})
    ev = {e['metric']: e['value'] for e in r['evidence']}
    sim = eng.call('simulate_placement', {'region': region, 'k': k, 'radius_m': radius})
    assert ev['n_urgent'] == eng.call('classify', {'region': region})['result']['type_counts']['긴급방문형']
    assert ev['resolved_mobile'] == sim['result']['covered_cells']                      # 이동형 = 배치 시뮬레이션
    assert ev['resolved_baseline'] == 0 and 0 <= ev['resolved_hub'] <= ev['n_urgent']
    assert ev['remaining_hub'] + ev['resolved_hub'] == ev['n_urgent']
    assert [o['name'] for o in r['result']['options']] == list(OPTION_NAMES.values())
    hubs = [p for p in r['result']['map_points'] if p['option'] == OPTION_NAMES['hub']]
    assert 1 <= len(hubs) <= k and r['params']['k'] == k                               # 경로당 거점 수 ≤ 이동형 거점 수


@live
def test_digest_chart_map_and_caveats(eng):
    st = ResultStore()
    ref = st.put(COMPARE, {}, call_tool(eng, COMPARE, {'region': '춘천', 'k': 3, 'radius_m': 3000}))
    text = Digester()(st.get(ref)).text
    assert '해소가 많은 순' in text and '거점은 행정동 이름으로' in text
    ctx = Context(st, {}, {}, '', 'admin')
    chart = _chart(ctx)
    ev = {e['metric']: e['value'] for e in st.get(ref).data['evidence']}
    assert [i['value'] for i in chart['items']] == [ev['resolved_baseline'], ev['resolved_hub'], ev['resolved_mobile']]
    m = _map(ctx, ref)
    assert m['layer'] == 'interventions' and {p['option'] for p in m['points']} == {OPTION_NAMES['hub'], OPTION_NAMES['mobile']}
    for _, phrase, _ in [r for r in REQUIRED_CAVEATS['admin'] if r[0] == COMPARE]:
        assert any(phrase in c for c in st.get(ref).data['caveats'])


@live
def test_gangnam_tie_message(eng):
    st = ResultStore()
    ref = st.put(COMPARE, {}, call_tool(eng, COMPARE, {'region': '강남', 'k': 2, 'radius_m': 1000}))
    ev = {e['metric']: e['value'] for e in st.get(ref).data['evidence']}
    text = Digester()(st.get(ref)).text
    assert ('해소 수가 같다' in text) == (ev['resolved_hub'] == ev['resolved_mobile'])


def test_admin_only():
    assert COMPARE in {t['name'] for t in tools_for('admin')}
    assert COMPARE not in {t['name'] for t in tools_for('citizen')}


@live
def test_hub_points_named_by_emd(eng):
    r = call_tool(eng, COMPARE, {'region': '강남', 'k': 2, 'radius_m': 1000})
    for p in r['result']['map_points']:
        assert p['name'].endswith(f"({p['emd_name']})")                 # 화면용 이름은 행정동 기준
        if p['option'] == OPTION_NAMES['hub']:
            assert p['facility_name']                                    # 원천 시설명은 따로 보관
