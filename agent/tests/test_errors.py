"""오류 처리: Sonnet API 오류·엔진 도구 오류·시민 지역 판단 오류를 에이전트가 잡아 같은 형식의 화면 조각으로 돌려준다."""
import anthropic
import httpx2

from agent.orchestrator import Orchestrator
from agent.screen import FALLBACK_TEXT, FALLBACK_TEXT_NO_MAP
from agent.tests.test_orchestrator import FakeClient, SCENARIO, SpyEngine, _good_answer, _resp, _use


class FailingClient(FakeClient):
    """준비된 응답을 다 쓰면 API 오류를 낸다."""
    def create(self, **kw):
        if not self.responses:
            raise anthropic.APIConnectionError(request=httpx2.Request('POST', 'https://api.anthropic.com/v1/messages'))
        return super().create(**kw)


class BrokenEngine(SpyEngine):
    def __init__(self, broken):
        super().__init__()
        self.broken = broken

    def call(self, tool, args):
        if tool == self.broken:
            raise RuntimeError('MCLP 풀이 실패: 시간 초과')
        return super().call(tool, args)


def test_api_error_returns_fallback_screen():
    screen, turn = Orchestrator(SpyEngine(), client=FailingClient(SCENARIO[:1])).ask('춘천에서 어디부터 확인해야 해?')
    assert turn.end == 'api_error' and screen['display']['headline'] == FALLBACK_TEXT['admin']
    assert screen['display']['map'] is not None                                   # 받아 둔 결과로 지도는 남는다
    err = screen['internal']['run']['errors'][0]
    assert err['where'] == 'sonnet' and err['type'] == 'APIConnectionError'


def test_engine_error_in_tool_keeps_going():
    engine = BrokenEngine('classify')
    client = FakeClient([_resp(_use('classify', {'region': '춘천'}, 1)), _resp(stop='end_turn'), _resp(stop='end_turn')])
    screen, turn = Orchestrator(engine, client=client).ask('춘천에서 어디부터 확인해야 해?')
    r = client.requests[1]['messages'][-1]['content'][0]
    assert r['is_error'] and '실행 중 오류' in r['content']                      # Sonnet 은 오류 결과를 받고 계속한다
    assert screen['internal']['run']['errors'][0]['where'] == 'tool:classify'


def test_auto_robustness_error_does_not_block_answer():
    client = FakeClient(SCENARIO[:2] + [_resp(_use('submit_answer', _good_answer(), 3))])
    screen, turn = Orchestrator(BrokenEngine('robustness'), client=client).ask('춘천에서 어디부터 확인해야 해?')
    assert turn.end == 'passed' and screen['display']['confidence']['label'] == '낮음'
    assert screen['internal']['run']['errors'][0]['where'] == 'tool:robustness(auto)'


def test_citizen_region_error():
    class NoLookup(SpyEngine):
        def call(self, tool, args):
            raise RuntimeError('데이터 파일을 읽지 못함')
    screen, turn = Orchestrator(NoLookup(), mode='citizen', client=FakeClient([])).ask('근처에 갈 곳?', {'lat': 37.88, 'lon': 127.73})
    assert turn.end == 'engine_error' and screen['display']['headline'] == FALLBACK_TEXT_NO_MAP['citizen']
    assert screen['display']['map'] is None
