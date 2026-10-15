"""최종 점검에서 찾은 문제: 짧은 답 실패 시 멈춤, 다시 쓰기 안내의 제출 도구, 도구 없는 문서, 모드별 재요청 문구, 짧은 답 이름 속 숫자."""
from agent.documents import SUBMIT_DOC
from agent.orchestrator import NUDGE, Orchestrator
from agent.screen import FALLBACK_TEXT_NO_MAP
from agent.store import ResultStore
from agent.tests.test_documents import _proposal
from agent.tests.test_orchestrator import SCENARIO, FakeClient, SpyEngine, _resp, _use
from agent.tests.test_verifier import _ctx
from agent.tools import SUBMIT_BRIEF
from agent.verifier import Context, verify_brief, verify_document

BAD_BRIEF = {'message': '먼저 볼 동네는 55곳이에요.'}                       # 숫자가 있어 검증 실패


def test_failed_brief_twice_returns_fallback_not_crash():
    client = FakeClient([_resp(_use(SUBMIT_BRIEF, BAD_BRIEF, 1)), _resp(_use(SUBMIT_BRIEF, BAD_BRIEF, 2))])
    screen, turn = Orchestrator(SpyEngine(), client=client).ask('안녕')
    assert turn.end == 'verify_failed' and screen['display']['headline'] == FALLBACK_TEXT_NO_MAP['admin']
    assert screen['internal']['rejected_answer'] == BAD_BRIEF


def test_feedback_names_the_same_submit_tool():
    bad = _proposal(_ctx())
    bad['sections'] = bad['sections'][:-1]                                        # 목차 빠짐 → 실패
    client = FakeClient(SCENARIO + [_resp(_use(SUBMIT_DOC, bad, 9)), _resp(_use(SUBMIT_DOC, _proposal(_ctx()), 10))])
    screen, turn = Orchestrator(SpyEngine(), client=client).ask('제안서 써줘')
    fb = client.requests[-1]['messages'][-1]['content'][0]['content']
    assert f'{SUBMIT_DOC} 로 다시 제출' in fb and turn.end == 'passed'


def test_proposal_and_report_need_tool_results():
    c = _ctx()
    empty = Context(ResultStore(), c.citable, c.caveat_ids, '제안서 써줘', 'admin')
    assert any('도구 결과 없이 사업 제안서를' in e for e in verify_document(_proposal(c), empty).errors)


def test_nudge_lists_mode_submit_tools():
    client = FakeClient([_resp(stop='end_turn'), _resp(stop='end_turn')])
    from agent.location import cell_of
    from agent.tests.test_location import StubEngine
    loc = {'lat': 37.8813, 'lon': 127.7298}
    Orchestrator(StubEngine({'춘천': {'{}_{}'.format(*cell_of(**loc))}}), mode='citizen', client=client).ask('안녕', loc)
    assert client.requests[-1]['messages'][-1]['content'] == NUDGE.format(tools='submit_answer, submit_brief')


def test_brief_allows_place_names_with_digits():
    c = _ctx('강남')
    name = next(e for e in c.store.get('r2').data['result']['by_emd_withdrawn'] if any(ch.isdigit() for ch in e))
    assert verify_brief({'message': f'{name} 이야기는 분석 질문으로 물어봐 주세요.'}, c).passed
