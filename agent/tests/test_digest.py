"""2단계: 요약 계층. 엔진 결과를 Sonnet 에 넘길 크기로 줄이되, 인용 가능한 숫자는 evidence·params 뿐이다."""
import json
import re

import pytest

from agent.digest import Digester, digest_all
from agent.engine_client import FixtureEngine
from agent.store import ResultStore, StoredResult

SCENARIO = ['find_candidates', 'classify', 'robustness']
MAX_CHARS = 3000            # 도구 하나의 요약 상한


@pytest.fixture(scope='module')
def engine():
    return FixtureEngine()


def _items(engine, region='춘천', tools=SCENARIO):
    st = ResultStore()
    for t in tools:
        st.put(t, {'region': region}, engine.call(t, {'region': region}))
    return list(st.items.values())


def _core_lines(text):
    """'핵심 값' 부분만 (caveats 앞까지)."""
    body = text.split('핵심 값 (숫자 없음, 설명용):')[1]
    return body.split('caveats:')[0]


@pytest.mark.parametrize('region', ['춘천', '강남'])
def test_size(engine, region):
    items = _items(engine, region)
    for s, d in zip(items, digest_all(items)):
        assert len(d.text) <= MAX_CHARS, (s.tool, len(d.text))
    raw = sum(len(json.dumps(s.data, ensure_ascii=False)) for s in items)
    assert sum(len(d.text) for d in digest_all(items)) < raw * 0.05


def test_all_evidence_and_params_citable(engine):
    items = _items(engine)
    for s, d in zip(items, digest_all(items)):
        for e in s.data['evidence']:
            assert d.citable[e['metric']] == e['value']
            assert f"  {e['metric']} = " in d.text
        for k, v in s.data['params'].items():
            assert d.citable[f'params.{k}'] == v
        assert len(d.citable) == len(s.data['evidence']) + len(s.data['params'])   # 그 밖의 숫자는 없다


def test_core_has_no_numbers(engine):
    """핵심 값에는 숫자를 넣지 않는다 (칸 ID 는 이름이라 제외)."""
    items = _items(engine)
    for s, d in zip(items, digest_all(items)):
        core = re.sub(r'\d+_\d+', '', _core_lines(d.text))
        assert not re.search(r'\d', core), (s.tool, core)


def test_classify_core(engine):
    items = _items(engine, tools=['classify'])
    text = digest_all(items)[0].text
    res = items[0].data['result']
    for layer in res['layers']:                     # 두 층 이름이 그대로 들어간다
        assert layer in text
    emd = res['by_emd_withdrawn']                   # 긴급방문형이 가장 많은 행정동이 맨 앞
    top = max(emd, key=lambda e: emd[e].get('긴급방문형', 0))
    assert f'긴급방문형이 많은 행정동 순: {top} >' in text


def test_robustness_core_order(engine):
    items = _items(engine, tools=['robustness'])
    text = digest_all(items)[0].text
    oat = items[0].data['result']['one_at_a_time']
    most = min((o for o in oat if o['urgent_jaccard'] is not None), key=lambda o: o['urgent_jaccard'])['param']
    assert f'(긴급방문형 판정 겹침이 낮은 순): {most} >' in text
    assert 'grid' not in text


def test_caveats_once_per_question(engine):
    """같은 caveat 문장은 한 질문 안에서 한 번만 원문으로 나오고, 이후에는 번호만 나온다."""
    items = _items(engine)
    texts = [d.text for d in digest_all(items)]
    all_caveats = {c for s in items for c in s.data['caveats']}
    joined = '\n'.join(texts)
    for c in all_caveats:
        assert joined.count(c) == 1
    assert '앞 결과와 같은 caveat: c1' in texts[1]


def test_gangnam_health_caveat(engine):
    text = digest_all(_items(engine, '강남', ['classify']))[0].text
    assert '공공 보건기관(3곳)만' in text


def test_error_result():
    s = StoredResult('r1', 'simulate_placement', {}, {
        'tool': 'simulate_placement', 'region': '춘천', 'result': {'error': 'k는 1 이상 정수: 0'},
        'evidence': [], 'caveats': [], 'figures': [], 'geojson': None, 'params': {'k': 0}})
    d = Digester()(s)
    assert '결과: k는 1 이상 정수: 0' in d.text and d.citable == {}


def test_other_tools_digest(engine):
    """시나리오 밖 도구도 요약이 깨지지 않는다 (기본 요약)."""
    for tool, args in [('region_context', {'region': '춘천'}),
                       ('simulate_placement', {'region': '춘천', 'k': 3, 'radius_m': 1000})]:
        st = ResultStore()
        st.put(tool, args, engine.call(tool, args))
        d = digest_all(list(st.items.values()))[0]
        assert 'evidence (인용 가능):' in d.text and len(d.text) <= MAX_CHARS
