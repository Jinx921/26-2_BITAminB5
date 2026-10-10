"""짧은 답 (인사·관계없는 질문·서비스 지역 밖·데이터 없음)과 도구 없는 분석 답변 차단."""
from agent.store import ResultStore
from agent.tests.test_verifier import _ctx, _good
from agent.tools import BRIEF_MAX, SUBMIT_BRIEF, tools_for
from agent.verifier import Context, verify, verify_brief

HELLO = '안녕하세요. 동네별로 먼저 확인할 곳을 찾거나 이동형 상담 거점을 정하는 일을 도와드릴 수 있어요.'


def _empty(mode='admin', q='안녕'):
    return Context(ResultStore(), {}, {}, q, mode)


def test_brief_passes_without_length_rules():
    r = verify_brief({'message': HELLO}, _empty())
    assert r.passed, r.errors


def test_brief_blocks_numbers_length_and_banned():
    assert any('숫자를 쓰지 않는다' in e for e in verify_brief({'message': '먼저 볼 동네는 55곳이에요.'}, _empty()).errors)
    assert any(f'{BRIEF_MAX}자 이내' in e for e in verify_brief({'message': '가' * (BRIEF_MAX + 1)}, _empty()).errors)
    assert any('"고립"' in e for e in verify_brief({'message': '고립된 동네는 알려드릴 수 없어요.'}, _empty('citizen')).errors)
    assert verify_brief({'message': '부산 3곳은 분석할 수 없어요.'}, _empty(q='부산 3곳 알려줘')).passed   # 질문에 있던 숫자


def test_analysis_answer_needs_tool_results():
    c = _ctx()
    ans = _good(c)
    assert verify(ans, c).passed
    errs = verify(ans, Context(ResultStore(), c.citable, c.caveat_ids, c.question, 'admin')).errors
    assert any('도구 결과 없이 분석 답변을 낼 수 없다' in e for e in errs)


def test_brief_in_both_modes_and_screen():
    for mode in ('admin', 'citizen'):
        assert SUBMIT_BRIEF in {t['name'] for t in tools_for(mode)}
    from agent.orchestrator import Orchestrator
    from agent.tests.test_orchestrator import FakeClient, SpyEngine, _resp, _use
    client = FakeClient([_resp(_use(SUBMIT_BRIEF, {'message': HELLO}, 1))])
    screen, turn = Orchestrator(SpyEngine(), client=client).ask('안녕')
    d = screen['display']
    assert turn.end == 'passed' and d['headline'] == HELLO and d['details'] == []
    assert d['map'] is None and d['confidence'] is None
