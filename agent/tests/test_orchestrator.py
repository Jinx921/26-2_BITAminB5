"""6단계: 오케스트레이터와 프롬프트. 가짜 Sonnet(정해진 응답 재생) + 예시 응답 엔진으로 API 없이 확인한다."""
import json
import re
from types import SimpleNamespace as NS

from agent.engine_client import FixtureEngine
from agent.orchestrator import MAX_CALLS, NUDGE, Orchestrator, save_run
from agent.prompts import COMMON, TARGET_DETAILS, TYPE_NAMES, build_system
from agent.screen import FALLBACK_TEXT
from agent.tests.test_verifier import QUESTION, _good
from agent.verifier import MIN_PARAGRAPHS, build_context


# ---------------------------------------------------------------- 가짜 Sonnet
def _use(name, inp, i):
    return NS(type='tool_use', id=f'tu_{i}', name=name, input=inp)


def _resp(*blocks, stop='tool_use'):
    return NS(stop_reason=stop, content=list(blocks),
              usage=NS(input_tokens=100, output_tokens=10, cache_read_input_tokens=0,
                       cache_creation_input_tokens=0))


class FakeClient:
    """messages.create 가 불릴 때마다 준비된 응답을 차례로 돌려주고, 받은 요청을 기록한다."""
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []
        self.messages = self

    def create(self, **kw):
        self.requests.append(json.loads(json.dumps(kw, default=lambda o: o.__dict__, ensure_ascii=False)))
        return self.responses.pop(0)


class SpyEngine(FixtureEngine):
    def __init__(self):
        super().__init__()
        self.called = []

    def call(self, tool, args):
        self.called.append((tool, args))
        return super().call(tool, args)


SCENARIO = [_resp(_use('find_candidates', {'region': '춘천'}, 1)),
            _resp(_use('classify', {'region': '춘천'}, 2)),
            _resp(_use('robustness', {'region': '춘천'}, 3))]


def _good_answer():
    return _good(build_context(FixtureEngine(), '춘천', QUESTION))   # r1~r3 순서가 시나리오와 같다


def _run(responses, mode='admin', engine=None):
    client, engine = FakeClient(responses), engine or SpyEngine()
    screen, turn = Orchestrator(engine, mode=mode, client=client).ask(QUESTION)
    return screen, turn, client, engine


# ---------------------------------------------------------------- 정상 흐름
def test_full_scenario_with_one_rewrite():
    bad = _good_answer()
    bad['details'] += '\n참고: 칸 기준입니다.'                       # 1차 제출은 검증 실패
    screen, turn, client, engine = _run(SCENARIO + [_resp(_use('submit_answer', bad, 4)),
                                                    _resp(_use('submit_answer', _good_answer(), 5))])
    assert [t for t, _ in engine.called] == ['find_candidates', 'classify', 'robustness']
    assert turn.end == 'passed' and turn.attempts == 2
    assert screen['display']['headline'] == _good_answer()['headline']
    assert [t['ref'] for t in screen['internal']['tool_trace']] == ['r1', 'r2', 'r3']
    # 다시 쓰기 요청: 마지막 요청의 마지막 메시지가 검증 오류를 담은 is_error tool_result
    last = client.requests[-1]['messages'][-1]['content'][0]
    assert last['is_error'] and '"칸"' in last['content']
    assert screen['internal']['run']['passed'] and len(screen['internal']['run']['calls']) == 5


def test_sonnet_gets_digest_not_raw_result():
    _, _, client, _ = _run(SCENARIO + [_resp(_use('submit_answer', _good_answer(), 4))])
    results = [m['content'][0] for m in client.requests[-1]['messages']
               if m['role'] == 'user' and isinstance(m['content'], list) and m['content'][0].get('type') == 'tool_result']
    assert len(results) == 3
    for r in results:
        assert r['content'].startswith('[r') and 'evidence (인용 가능)' in r['content']
        assert len(r['content']) < 3000 and '"grid"' not in r['content']


def test_request_settings():
    _, _, client, _ = _run(SCENARIO + [_resp(_use('submit_answer', _good_answer(), 4))])
    req = client.requests[0]
    assert req['model'] == 'claude-sonnet-5-5' and req['output_config'] == {'effort': 'medium'}
    assert req['cache_control'] == {'type': 'ephemeral'} and 'tool_choice' not in req
    assert req['system'] == build_system('admin')
    assert [t['name'] for t in req['tools']][-3:] == ['submit_answer', 'submit_document', 'submit_brief']


# ---------------------------------------------------------------- 막는 동작
def test_citizen_cannot_run_admin_tool():
    from agent.location import cell_of
    from agent.tests.test_location import StubEngine
    loc = {'lat': 37.8813, 'lon': 127.7298}
    engine = StubEngine({'춘천': {'{}_{}'.format(*cell_of(**loc))}})
    client = FakeClient([_resp(_use('classify', {'region': '춘천'}, 1)),
                         _resp(NS(type='text', text='...'), stop='end_turn'),
                         _resp(NS(type='text', text='...'), stop='end_turn')])
    screen, _ = Orchestrator(engine, mode='citizen', client=client).ask(QUESTION, loc)
    assert [t for t, a in engine.called if 'cell_id' not in a] == []    # 엔진까지 가지 않는다 (지역 판단 호출만)
    r = client.requests[1]['messages'][-1]['content'][0]
    assert r['is_error'] and '쓸 수 없는 도구' in r['content']
    assert screen['display']['headline'] == FALLBACK_TEXT['citizen']


def test_locked_args_dropped():
    _, _, client, engine = _run([_resp(_use('classify', {'region': '춘천', 'far_social_m': 1000}, 1)),
                                 _resp(NS(type='text', text='...'), stop='end_turn'), _resp(NS(type='text', text='...'), stop='end_turn')])
    assert engine.called == [('classify', {'region': '춘천'})]
    assert '기본값으로 계산했다' in client.requests[1]['messages'][-1]['content'][0]['content']


def test_engine_error_returned_to_sonnet():
    _, turn, client, _ = _run([_resp(_use('classify', {'region': '부산'}, 1)),
                               _resp(NS(type='text', text='...'), stop='end_turn'), _resp(NS(type='text', text='...'), stop='end_turn')])
    r = client.requests[1]['messages'][-1]['content'][0]
    assert r['is_error'] and turn.store.items == {}


def test_no_submit_nudges_once_then_fallback():
    screen, turn, client, _ = _run(SCENARIO + [_resp(NS(type='text', text='답'), stop='end_turn'),
                                               _resp(NS(type='text', text='답'), stop='end_turn')])
    nudge = client.requests[-1]['messages'][-1]
    assert nudge['role'] == 'user' and nudge['content'] == NUDGE.format(tools='submit_answer, submit_document, submit_brief')
    assert turn.end == 'no_submit' and screen['display']['headline'] == FALLBACK_TEXT['admin']
    assert screen['display']['map']['points']                           # 지도는 남는다


def test_two_failed_submits_fallback():
    bad = _good_answer()
    bad['caution'] = ''
    screen, turn, _, _ = _run(SCENARIO + [_resp(_use('submit_answer', bad, 4)), _resp(_use('submit_answer', bad, 5))])
    assert turn.end == 'verify_failed' and screen['internal']['rejected_answer'] == bad
    assert screen['display']['confidence']['label'] == '낮음'


def test_refusal_and_max_calls():
    screen, turn, _, _ = _run([_resp(stop='refusal')])
    assert turn.end == 'refusal' and screen['display']['headline'] == FALLBACK_TEXT['admin']
    loop = [_resp(_use('region_context', {'region': '춘천'}, i)) for i in range(MAX_CALLS)]
    _, turn, client, _ = _run(loop)
    assert turn.end == 'max_calls' and len(client.requests) == MAX_CALLS


def test_save_run(tmp_path, monkeypatch):
    import agent.store as store_mod
    monkeypatch.setattr(store_mod, 'RUNS_DIR', tmp_path)
    screen, turn, _, _ = _run(SCENARIO + [_resp(_use('submit_answer', _good_answer(), 4))])
    run = save_run(screen, turn)
    assert run == tmp_path and (tmp_path / 'screen.json').exists() and (tmp_path / 'r3_robustness.json').exists()


# ---------------------------------------------------------------- 프롬프트
def test_prompt_has_no_engine_numbers():
    """프롬프트 속 숫자는 에이전트 정책값(분량·문단 수)뿐이다."""
    from agent.prompts import SMS_MAX
    allowed = {str(TARGET_DETAILS[0]), f'{TARGET_DETAILS[1]:,}', str(MIN_PARAGRAPHS), str(SMS_MAX), '1', '2'}   # c1, c2 예시
    for mode in ('admin', 'citizen'):
        nums = set(re.findall(r'\d+(?:,\d{3})*', build_system(mode)))
        assert nums <= allowed, nums - allowed


def test_prompt_modes():
    admin, citizen = build_system('admin'), build_system('citizen')
    for t, name in TYPE_NAMES.items():
        assert t in admin and name in admin
    for word in ('긴급방문형', '연계형', 'find_candidates', 'classify'):
        assert word not in citizen                                       # 시민 프롬프트에는 위험 판정 개념이 없다
    assert admin.endswith(COMMON) and citizen.endswith(COMMON)                # 공통 규칙은 두 모드가 같다
