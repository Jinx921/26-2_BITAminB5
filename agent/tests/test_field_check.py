"""남은 일 4번: 현장 확인 목록 (칸별 안정도, 확인 질문, 방문 순서)."""
import pytest

from agent.agent_tools import call_tool
from agent.digest import Digester
from agent.engine_client import ENGINE_DIR, FixtureEngine, LiveEngine
from agent.field_check import FIELD_CHECK, MUST_CHECK, QUESTION, QUESTION_MIXED, STABLE, VARY
from agent.store import ResultStore
from agent.tools import tools_for

live = pytest.mark.skipif(not (ENGINE_DIR / 'preprocessed' / 'cell_master.parquet').exists(), reason='엔진 데이터 없음')


@pytest.fixture(scope='module')
def results():
    eng = LiveEngine()
    return {r: (call_tool(eng, FIELD_CHECK, {'region': r}), eng.call('classify', {'region': r})) for r in ('춘천', '강남')}


@live
@pytest.mark.parametrize('region', ['춘천', '강남'])
def test_counts_match_classify(results, region):
    fc, cl = results[region]
    ev = {e['metric']: e['value'] for e in fc['evidence']}
    assert ev['n_default_urgent'] == cl['result']['type_counts']['긴급방문형']
    assert ev['n_check'] == ev['n_must_check'] + ev['n_need_check'] == len(fc['result']['cells'])
    assert ev['n_stable'] + ev['n_check'] == ev['n_default_urgent']


@live
@pytest.mark.parametrize('region', ['춘천', '강남'])
def test_levels_questions_order(results, region):
    cells = results[region][0]['result']['cells']
    for c in cells:
        assert c['stability'] < STABLE
        assert c['level'] == ('꼭 확인' if c['stability'] < MUST_CHECK else '확인 필요')
        assert c['questions'] and all(q in list(QUESTION.values()) + [QUESTION_MIXED] for q in c['questions'])
    assert [c['order'] for c in cells] == list(range(1, len(cells) + 1))
    emds = [c['emd_name'] for c in cells]
    assert all(emds.index(e) + emds.count(e) - 1 == len(emds) - 1 - emds[::-1].index(e) for e in set(emds))  # 동별로 묶임


@live
def test_ranges_from_engine_defaults(results):
    import config as C
    r = results['춘천'][0]['params']['ranges']
    assert r['far_social_m'] == [C.FAR_SOCIAL_M * (1 - VARY), C.FAR_SOCIAL_M, C.FAR_SOCIAL_M * (1 + VARY)]
    assert r['persist_min'] == [C.PERSIST_MIN, C.PERSIST_MIN + 1]


@live
def test_digest_and_screen_layer(results):
    from agent.screen import _map
    from agent.verifier import Context
    st = ResultStore()
    ref = st.put(FIELD_CHECK, {'region': '춘천'}, results['춘천'][0])
    text = Digester()(st.get(ref)).text
    assert '확인할 동네가 많은 행정동 순' in text and 'stability' not in text
    m = _map(Context(st, {}, {}, '', 'admin'), ref)
    assert m['layer'] == 'checks' and {'level', 'questions', 'order'} <= set(m['points'][0])
    assert 'stability' not in m['points'][0]                                   # 안정도 숫자는 화면 데이터에 없다


def test_fixture_engine_returns_error_and_mode():
    r = call_tool(FixtureEngine(), FIELD_CHECK, {'region': '춘천'})
    assert 'error' in r['result']
    assert FIELD_CHECK in {t['name'] for t in tools_for('admin')}
    assert FIELD_CHECK not in {t['name'] for t in tools_for('citizen')}
