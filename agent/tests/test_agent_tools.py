"""시민 모드 2단계: 시민용 시간대 도구 (region_context 에서 시간대만 꺼냄)."""
import json

from agent.agent_tools import SENIOR_HOURS, SENIOR_HOURS_NOTE, call_tool, slot_label
from agent.digest import Digester
from agent.engine_client import FixtureEngine
from agent.store import ResultStore
from agent.tools import tools_for
from agent.verifier import place_names


def _hours(region='춘천'):
    return call_tool(FixtureEngine(), SENIOR_HOURS, {'region': region})


def test_only_time_values_pass_through():
    r = _hours()
    src = FixtureEngine().call('region_context', {'region': '춘천'})
    assert set(r) == set(src)                                            # 엔진 도구와 같은 형식
    assert r['result']['senior60_card_time_pct'] == src['result']['senior60_card_time_pct']
    assert {e['metric'] for e in r['evidence']} == {e['metric'] for e in src['evidence'] if 'time' in e['metric']}
    text = json.dumps(r, ensure_ascii=False)
    for risk in ('type_counts', '긴급방문형', '연계형', 'local_payment', 'population', '칸'):
        assert risk not in text, risk                                    # 위험 정보·내부 설명은 넘어가지 않는다
    assert r['caveats'] == [SENIOR_HOURS_NOTE]


def test_slot_label():
    assert slot_label('12_17') == '12~17시'


def test_citizen_tools_and_schema():
    citizen = {t['name']: t for t in tools_for('citizen')}
    assert SENIOR_HOURS in citizen and citizen[SENIOR_HOURS]['input_schema']['properties'] == {}
    assert SENIOR_HOURS not in {t['name'] for t in tools_for('admin')}  # 관리자는 region_context 를 그대로 쓴다
    assert 'region_context' not in citizen


def test_digest_lists_slots_in_order():
    st = ResultStore()
    ref = st.put(SENIOR_HOURS, {'region': '춘천'}, _hours())
    text = Digester()(st.get(ref)).text
    pct = st.get(ref).data['result']['senior60_card_time_pct']
    top = slot_label(max(pct, key=pct.get))
    assert f'활동이 많은 시간대 순: {top} >' in text and SENIOR_HOURS_NOTE in text


def test_slot_labels_exempt_from_number_check():
    st = ResultStore()
    st.put(SENIOR_HOURS, {'region': '춘천'}, _hours())
    names = place_names(st)
    assert '12~17시' in names and '10시' not in names                  # 결과에 없는 시각은 그대로 검사


def test_orchestrator_injects_region():
    from agent.location import cell_of
    from agent.orchestrator import Orchestrator
    from agent.tests.test_location import StubEngine
    from agent.tests.test_orchestrator import FakeClient, _resp, _use
    loc = {'lat': 37.8813, 'lon': 127.7298}
    engine = StubEngine({'춘천': {'{}_{}'.format(*cell_of(**loc))}})
    client = FakeClient([_resp(_use(SENIOR_HOURS, {}, 1)), _resp(stop='end_turn'), _resp(stop='end_turn')])
    screen, turn = Orchestrator(engine, mode='citizen', client=client).ask('언제 가면 좋아요?', loc)
    assert ('region_context', {'region': '춘천'}) in engine.called
    r = client.requests[1]['messages'][-1]['content'][0]
    assert not r.get('is_error') and '12~17시' in r['content']
    assert screen['internal']['tool_trace'][0]['args'] == {'region': '춘천'}
