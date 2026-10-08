"""1단계: 엔진 연결 (실제 엔진 / 예시 응답) 과 결과 보관소"""
import json

import pytest

from agent.engine_client import ENGINE_DIR, EngineError, FixtureEngine, LiveEngine
from agent.store import ResultStore

KEYS = {'tool', 'region', 'result', 'evidence', 'caveats', 'figures', 'geojson', 'params'}
SCENARIO = ['find_candidates', 'classify', 'robustness']     # "춘천에서 어디부터 확인해야 해?"


@pytest.fixture(scope='module')
def fixture_engine():
    return FixtureEngine()


@pytest.fixture(scope='module')
def live_engine():
    if not (ENGINE_DIR / 'preprocessed' / 'cell_master.parquet').exists():
        pytest.skip('엔진 데이터 없음')
    return LiveEngine()


def _out_snapshot():
    out = ENGINE_DIR / 'out'
    return {p.name: p.stat().st_mtime_ns for p in out.rglob('*') if p.is_file()}


@pytest.mark.parametrize('tool', SCENARIO)
def test_fixture_shape(fixture_engine, tool):
    r = fixture_engine.call(tool, {'region': '춘천'})
    assert set(r) == KEYS and r['tool'] == tool and r['region'] == '춘천'
    assert all('\\' not in p for p in r['figures'])
    assert r['geojson'] is None or '\\' not in r['geojson']


def test_fixture_matches_params(fixture_engine):
    r = fixture_engine.call('simulate_placement', {'region': '춘천', 'k': 3, 'radius_m': 3000})
    assert r['params']['radius_m'] == 3000
    with pytest.raises(EngineError):
        fixture_engine.call('classify', {'region': '춘천', 'far_social_m': 123})
    with pytest.raises(EngineError):
        fixture_engine.call('no_such_tool', {'region': '춘천'})


def test_fixture_returns_copy(fixture_engine):
    a = fixture_engine.call('classify', {'region': '춘천'})
    a['evidence'].clear()
    assert fixture_engine.call('classify', {'region': '춘천'})['evidence']


@pytest.mark.parametrize('tool', SCENARIO)
def test_live_equals_fixture(live_engine, fixture_engine, tool):
    """실제 엔진과 예시 응답이 같은 숫자를 낸다 (그림 경로만 다름: 실제는 render=False)."""
    live = live_engine.call(tool, {'region': '춘천'})
    fix = fixture_engine.call(tool, {'region': '춘천'})
    assert set(live) == KEYS
    assert live['evidence'] == fix['evidence']
    assert live['caveats'] == fix['caveats']
    assert live['figures'] == [] and live['geojson'] is None


def test_live_does_not_touch_engine_out(live_engine):
    before = _out_snapshot()
    for tool in SCENARIO + ['simulate_placement']:
        live_engine.call(tool, {'region': '춘천'})
    assert _out_snapshot() == before


def test_live_bad_region(live_engine):
    with pytest.raises(EngineError):
        live_engine.call('classify', {'region': '부산'})


def test_store_refs_and_save(fixture_engine, tmp_path):
    st = ResultStore()
    refs = [st.put(t, {'region': '춘천'}, fixture_engine.call(t, {'region': '춘천'})) for t in SCENARIO]
    assert refs == ['r1', 'r2', 'r3']
    assert st.get('r2').tool == 'classify' and st.by_tool('robustness')[0].ref == 'r3'
    run = st.save(tmp_path / 'run')
    index = json.loads((run / 'index.json').read_text(encoding='utf-8'))
    assert [i['file'] for i in index] == ['r1_find_candidates.json', 'r2_classify.json', 'r3_robustness.json']
