"""남은 일 2번: 관리자의 다른 질문 (배치, 시설 폐쇄, 믿어도 돼)."""
import json

import pytest

from agent.agent_tools import FACILITY_FILE, FIND_FACILITY, call_tool
from agent.digest import Digester
from agent.engine_client import FIXTURE_DIR, FixtureEngine
from agent.store import ResultStore
from agent.tools import service_regions, tools_for
from agent.verifier import Context, REQUIRED_CAVEATS, verify

needs_data = pytest.mark.skipif(not FACILITY_FILE.exists(), reason='엔진 시설 데이터 없음')
FAC_EXAMPLE = json.loads(next(FIXTURE_DIR.glob('facility_change_*.json')).read_text(encoding='utf-8'))
REMOVED = FAC_EXAMPLE['result']['removed'][0]                       # 예시 응답에서 뺀 시설


@needs_data
def test_find_facility_returns_same_name_places():
    r = call_tool(None, FIND_FACILITY, {'region': '춘천', 'name': REMOVED['name'].replace(' ', '')})
    ids = [m['fac_id'] for m in r['result']['matches']]
    assert REMOVED['fac_id'] in ids                                  # 띄어쓰기 없이 찾아도 나온다
    assert r['evidence'] == [{'metric': 'n_matches', 'value': r['result']['n_matches']}]
    assert all(m['addr'] or m['addr'] is None for m in r['result']['matches'])


@needs_data
def test_find_facility_digest_and_region_enum():
    st = ResultStore()
    ref = st.put(FIND_FACILITY, {}, call_tool(None, FIND_FACILITY, {'region': '춘천', 'name': REMOVED['name']}))
    text = Digester()(st.get(ref)).text
    assert REMOVED['fac_id'] in text and '시설 ID' in text
    schema = next(t for t in tools_for('admin') if t['name'] == FIND_FACILITY)
    assert schema['input_schema']['properties']['region']['enum'] == service_regions()
    assert FIND_FACILITY not in {t['name'] for t in tools_for('citizen')}


def _ctx(*calls):
    eng, st, dg, citable = FixtureEngine(), ResultStore(), Digester(), {}
    for tool, args in calls:
        ref = st.put(tool, args, eng.call(tool, args))
        citable[ref] = dg(st.get(ref)).citable
    return Context(st, citable, dict(dg.caveat_ids), '이동형 상담 3곳 어디가 좋아?', 'admin'), dg


def test_placement_digest_and_allowed_params():
    ctx, dg = _ctx(('simulate_placement', {'region': '춘천', 'k': 3, 'radius_m': 3000}))
    text = dg(ctx.store.get('r1')).text
    sites = [s['emd_name'] for s in ctx.store.get('r1').data['result']['chosen_sites']]
    assert '고른 거점 위치 (행정동' in text and sites[0] in text
    ev = ctx.citable['r1']
    req = [c for t, c in ctx.caveat_ids.items() if any(p in t for _, p, _ in REQUIRED_CAVEATS['admin'])]
    share = round(ev['covered_senior_share_k3'] * 100)
    details = (f'이동형 상담 거점은 {sites[0]}, {sites[1]}, {sites[2]}에 두는 것이 좋습니다.\n'
               f'차량으로 반경 3km 안을 돌면 대상 동네 어르신 유동의 {share}%에 닿을 수 있습니다.\n'
               '다만 이것은 닿을 수 있는 범위일 뿐입니다. 실제로 이용이 늘어나는지는 운영하면서 확인해야 합니다. '
               '거점마다 방문 안부와 건강상담을 함께 운영하면 좋습니다. 운영 요일은 동네 사정에 맞춰 정하면 됩니다. '
               '처음 몇 달은 이용자 수를 기록해 두면 다음 배치를 정할 때 도움이 됩니다. '
               '거점 주변 경로당과 마을회관에 미리 알려 두면 어르신들이 찾아오기 쉽습니다. '
               '이장님이나 통장님께 방문 일정을 공유해 주시면 안내 방송으로 알릴 수 있습니다.')
    ans = {'headline': f'{sites[0]}부터 거점을 두세요.', 'details': details,
           'caution': '이 결과는 머무는 사람 기준이라 실제 사는 사람과 다를 수 있어 현장 확인이 필요합니다. 닿을 수 있는 범위이지 고립이 줄어드는 효과는 아닙니다.',
           'caveats_reflected': req, 'map_ref': 'r1',
           'citations': [{'text': '3km', 'op': 'value', 'sources': [{'ref': 'r1', 'metric': 'params.radius_m'}]},
                         {'text': f'{share}%', 'op': 'value', 'sources': [{'ref': 'r1', 'metric': 'covered_senior_share_k3'}]}]}
    r = verify(ans, ctx)
    assert r.passed, r.errors                                         # 반경(params)은 관리자 배치 답변에서 허용
    ans['caveats_reflected'] = [c for c in req if '고립 감소' not in next(t for t, i in ctx.caveat_ids.items() if i == c)]
    assert any('고립 감소 효과가 아니다' in e for e in verify(ans, ctx).errors)


def test_facility_change_digest():
    ctx, dg = _ctx(('facility_change', FAC_EXAMPLE['params'] | {'region': '춘천'}))
    text = dg(ctx.store.get('r1')).text
    assert f"뺀 시설: {REMOVED['name']}" in text and '→' in text and '행정동 순' in text


def test_region_context_time_labels_are_names():
    ctx, dg = _ctx(('region_context', {'region': '춘천'}))
    from agent.verifier import place_names
    assert '12~17시' in place_names(ctx.store) and '12~17시' in dg(ctx.store.get('r1')).text


def test_robustness_auto_called_for_confidence():
    """Sonnet 이 강건성 점검을 부르지 않아도 코드가 불러 신뢰도를 정한다 (Sonnet 에는 넘기지 않음)."""
    from agent.orchestrator import Orchestrator
    from agent.tests.test_orchestrator import FakeClient, SpyEngine, _good_answer, _resp, _use
    client, engine = FakeClient([_resp(_use('find_candidates', {'region': '춘천'}, 1)),
                                 _resp(_use('classify', {'region': '춘천'}, 2)),
                                 _resp(_use('submit_answer', _good_answer(), 3))]), SpyEngine()
    screen, turn = Orchestrator(engine, client=client).ask('춘천에서 어디부터 확인해야 해?')
    assert [t for t, _ in engine.called] == ['find_candidates', 'classify', 'robustness']
    assert turn.end == 'passed' and screen['display']['confidence']['label'] in ('높음', '보통')
    assert screen['internal']['tool_trace'][-1]['args']['auto'].startswith('신뢰도 계산용')
    assert 'robustness' not in json.dumps(client.requests[-1]['messages'], ensure_ascii=False)


def test_percent_k_labels_and_ages():
    """비율 하나를 %로, 지표 이름의 거점 수(…_k3 → 3곳), 연령 표기(60대 이상)는 맞는 표기로 인정한다."""
    ctx, _ = _ctx(('simulate_placement', {'region': '춘천', 'k': 3, 'radius_m': 3000}))
    ev = ctx.citable['r1']
    pct = round(ev['covered_senior_share_k3'] * 100, 1)
    from agent.verifier import VerifyResult, _check_numbers
    ans = {'headline': '', 'caution': '', 'details': f'60대 이상 어르신 기준으로 3곳이면 {pct}%에 닿습니다.',
           'citations': [{'text': '3곳', 'op': 'value', 'sources': [{'ref': 'r1', 'metric': 'covered_senior_share_k3'}]},
                         {'text': f'{pct}%', 'op': 'percent', 'sources': [{'ref': 'r1', 'metric': 'covered_senior_share_k3'}]}]}
    res = VerifyResult()
    _check_numbers(ans, ctx, res)
    assert res.errors == []
    ans['citations'][1]['text'] = f'{pct + 5}%'
    ans['details'] = ans['details'].replace(f'{pct}%', f'{pct + 5}%')
    res = VerifyResult()
    _check_numbers(ans, ctx, res)
    assert any('값이 출처와 다름' in e for e in res.errors)


@needs_data
def test_found_facility_address_is_a_name():
    st = ResultStore()
    st.put(FIND_FACILITY, {}, call_tool(None, FIND_FACILITY, {'region': '춘천', 'name': REMOVED['name']}))
    from agent.verifier import place_names
    addrs = {m['addr'] for m in st.get('r1').data['result']['matches'] if m['addr']}
    assert addrs and addrs <= place_names(st)


@needs_data
def test_highlight_only_removed_facility():
    from agent.screen import _map
    st = ResultStore()
    st.put(FIND_FACILITY, {}, call_tool(None, FIND_FACILITY, {'region': '춘천', 'name': REMOVED['name']}))
    st.put('facility_change', {}, FixtureEngine().call('facility_change', FAC_EXAMPLE['params'] | {'region': '춘천'}))
    ctx = Context(st, {}, {}, '', 'admin')
    pts = _map(ctx, 'r1', f"{REMOVED['name']}이 문을 닫으면")['points']
    assert len(pts) > 1 and [p['id'] for p in pts if p['highlight']] == [REMOVED['fac_id']]


def test_k_counts_next_to_cited_curve():
    """거점 수별 비율을 인용했으면 '1곳·3곳' 같은 거점 수는 출처 없이 써도 된다 (인용 안 한 거점 수는 검사)."""
    ctx, _ = _ctx(('simulate_placement', {'region': '춘천', 'k': 3, 'radius_m': 3000}))
    ev = ctx.citable['r1']
    p1, p3 = round(ev['covered_senior_share_k1'] * 100, 1), round(ev['covered_senior_share_k3'] * 100, 1)
    from agent.verifier import VerifyResult, _check_numbers
    cit = [{'text': f'{p1}%', 'op': 'percent', 'sources': [{'ref': 'r1', 'metric': 'covered_senior_share_k1'}]},
           {'text': f'{p3}%', 'op': 'percent', 'sources': [{'ref': 'r1', 'metric': 'covered_senior_share_k3'}]}]
    ans = {'headline': '', 'caution': '', 'citations': cit, 'details': f'1곳이면 {p1}%, 3곳이면 {p3}%입니다.'}
    res = VerifyResult(); _check_numbers(ans, ctx, res)
    assert res.errors == []
    ans['details'] += ' 5곳이면 더 넓어집니다.'                                     # k5 는 인용하지 않음
    res = VerifyResult(); _check_numbers(ans, ctx, res)
    assert any('출처 없는 숫자: "5"' in e for e in res.errors)
