"""오케스트레이터: Sonnet 의 도구 호출을 반복해 질문 하나를 화면 조각까지 처리한다.

질문 → Sonnet ─┬─ 엔진 도구 호출 → 권한 확인 → 기준값 인자 제거 → 엔진 실행 → 보관 → 요약을 돌려줌 → 다시 Sonnet
               ├─ 제출 (submit_answer 분석 답변 / submit_document 문서 / submit_brief 짧은 답)
               │    → 검증 ─┬─ 통과 → 화면 조각
               │            └─ 실패 → 고칠 점을 돌려주고 같은 도구로 다시 쓰게 함 (MAX_REWRITES 회)
               └─ 제출 없이 끝남·거절·호출 한도 초과 → 안내 문구 + 지도

오류 처리 (에이전트가 뜻을 아는 오류만 잡는다. 그 밖의 예외는 백엔드가 감싼다)
  - Sonnet API 오류(네트워크·요금 한도·키·시간 초과) → 안내 문구 화면 조각 (end='api_error')
  - 엔진 도구 실행 중 오류 → 그 도구 결과만 오류로 Sonnet 에 돌려주고 계속 (internal.run.errors 에 기록)
  - 시민 지역 판단 중 엔진 오류 → 안내 문구 (end='engine_error')
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from agent.agent_tools import call_tool
from agent.digest import Digester
from agent.engine_client import EngineError
from agent.location import detect_region
from agent.prompts import build_system
from agent.screen import CITIZEN_NOTICE, LOCATION_KEYS, REGION_NAMES, build_screen
from agent.store import ResultStore
from agent.documents import SUBMIT_DOC
from agent.tools import FIXED_ARGS, SUBMIT_BRIEF, SUBMITS, is_allowed, service_regions, strip_locked, tools_for
from agent.verifier import Context, VerifyResult, feedback, verify, verify_brief, verify_document

MODEL = 'claude-sonnet-5-5'
EFFORT = 'medium'          # 여러 단계 도구 사용에 권장되는 시작값
MAX_TOKENS = 16000
MAX_CALLS = 8              # 질문 하나에 Sonnet 을 부르는 최대 횟수
MAX_REWRITES = 1           # 검증 실패 후 다시 쓰게 하는 횟수
NUDGE = '답을 제출 도구로 제출해 주세요: {tools}'          # 모드별 제출 도구 이름이 들어간다
ENV_FILE = Path(__file__).resolve().parent / '.env'


def default_client():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    return anthropic.Anthropic()


@dataclass
class Turn:
    """질문 하나를 처리하는 동안의 상태."""
    question: str
    mode: str
    store: ResultStore = field(default_factory=ResultStore)
    digester: Digester = field(default_factory=Digester)
    citable: dict = field(default_factory=dict)
    answer: dict | None = None
    check: VerifyResult | None = None
    attempts: int = 0
    rejected: list = field(default_factory=list)   # 통과 전 실패한 제출의 오류 (디버깅용)
    location: dict | None = None                   # 시민 모드: 앱이 준 위치 + 판단한 지역 (저장하지 않음)
    errors: list = field(default_factory=list)     # 잡은 오류 (어디서, 종류, 내용)
    calls: list = field(default_factory=list)      # Sonnet 호출 기록 (stop_reason, 토큰)
    end: str = ''                                  # 끝난 이유

    def context(self) -> Context:
        return Context(self.store, self.citable, dict(self.digester.caveat_ids), self.question, self.mode)


class Orchestrator:
    def __init__(self, engine, mode: str = 'admin', client=None, model: str = MODEL, effort: str = EFFORT):
        self.engine, self.mode, self.model, self.effort = engine, mode, model, effort
        self.client = client or default_client()
        self.system = build_system(mode)
        self.tools = tools_for(mode)

    # ------------------------------------------------------------ 엔진 도구 하나 실행
    def _run_tool(self, turn: Turn, block) -> dict:
        def result(text, error=False):
            r = {'type': 'tool_result', 'tool_use_id': block.id, 'content': text}
            return {**r, 'is_error': True} if error else r

        if not is_allowed(self.mode, block.name):
            return result(f'이 모드에서 쓸 수 없는 도구: {block.name}', error=True)
        args, dropped = strip_locked(block.name, dict(block.input), self.mode)
        fixed = FIXED_ARGS.get(self.mode, {}).get(block.name, ())
        if turn.location and fixed:                                       # 위치는 코드가 채운다
            args.update({k: turn.location[k] for k in fixed if k in turn.location})
        try:
            data = call_tool(self.engine, block.name, args)
        except EngineError as e:
            return result(str(e), error=True)
        except Exception as e:                                            # 엔진 내부 오류 (예: 배치 최적화 실패)
            turn.errors.append({'where': f'tool:{block.name}', 'type': type(e).__name__, 'message': str(e)})
            return result(f'{block.name} 실행 중 오류가 나서 결과가 없다. 이 결과 없이 답하거나 다른 도구를 쓴다.', error=True)
        ref = turn.store.put(block.name, args, data)
        d = turn.digester(turn.store.get(ref))
        turn.citable[ref] = d.citable
        note = f'\n(기준값 인자 {", ".join(dropped)} 는 바꿀 수 없어 기본값으로 계산했다)' if dropped else ''
        return result(d.text + note)

    # ------------------------------------------------------------ 신뢰도용 강건성 점검
    def _ensure_robustness(self, turn: Turn) -> None:
        """관리자 모드에서 Sonnet 이 강건성 점검을 부르지 않았으면 코드가 부른다 (신뢰도는 코드가 정하는 값).
        Sonnet 에는 넘기지 않고 보관소에만 둔다."""
        if self.mode != 'admin' or turn.store.by_tool('robustness'):
            return
        regions = [s.data.get('region') for s in turn.store.items.values() if s.data.get('region')]
        if not regions:
            return
        try:
            data = self.engine.call('robustness', {'region': regions[0]})
        except Exception as e:                                            # 신뢰도만 '낮음'이 되고 답은 그대로 낸다
            turn.errors.append({'where': 'tool:robustness(auto)', 'type': type(e).__name__, 'message': str(e)})
            return
        turn.store.put('robustness', {'region': regions[0], 'auto': '신뢰도 계산용 (코드가 호출)'}, data)

    # ------------------------------------------------------------ 답변 제출
    def _submit(self, turn: Turn, block) -> dict | None:
        """검증 통과면 None (끝), 다시 쓰게 할 때는 돌려줄 tool_result."""
        if block.name != SUBMIT_BRIEF:                     # 짧은 답은 신뢰도를 보여주지 않아 강건성이 필요 없다
            self._ensure_robustness(turn)
        turn.attempts += 1
        turn.answer = dict(block.input)
        check = {SUBMIT_DOC: verify_document, SUBMIT_BRIEF: verify_brief}.get(block.name, verify)
        turn.check = check(turn.answer, turn.context())
        if turn.check.passed:
            turn.end = 'passed'
            return None
        turn.rejected.append({'attempt': turn.attempts, 'errors': turn.check.errors})
        if turn.attempts > MAX_REWRITES:
            turn.end = 'verify_failed'
            return None
        return {'type': 'tool_result', 'tool_use_id': block.id, 'content': feedback(turn.check, block.name),
                'is_error': True}

    # ------------------------------------------------------------ 질문 하나
    def _finish(self, turn: Turn) -> tuple[dict, Turn]:
        ok = turn.end == 'passed'
        check = turn.check if turn.answer is not None else None
        screen = build_screen(turn.question, self.mode, turn.answer, check, turn.context(), turn.attempts)
        screen['internal']['run'] = {'model': self.model, 'effort': self.effort, 'end': turn.end, 'passed': ok,
                                     'calls': turn.calls, 'rejected': turn.rejected, 'errors': turn.errors}
        return screen, turn

    def _notice(self, turn: Turn, key: str) -> tuple[dict, Turn]:
        turn.end = key
        screen = build_screen(turn.question, self.mode, None, None, turn.context(), notice=CITIZEN_NOTICE[key])
        screen['internal']['run'] = {'model': self.model, 'effort': self.effort, 'end': key, 'passed': False,
                                     'calls': [], 'rejected': [], 'errors': []}
        return screen, turn

    def ask(self, question: str, location: dict | None = None) -> tuple[dict, Turn]:
        """location: 시민 모드에서 앱이 넘겨주는 찾을 위치 {'lat': 위도, 'lon': 경도}.
        사용자가 지금 있는 곳(위치 허용)일 수도, 지도에서 고르거나 주소로 입력한 곳일 수도 있다
        (예: 부산에 사는 자녀가 춘천에 계신 어머니 동네를 대신 찾는 경우)."""
        turn = Turn(question, self.mode)
        if self.mode == 'citizen':
            turn.digester = Digester(hidden_params=LOCATION_KEYS)        # 찾을 위치 좌표는 Sonnet 에 넘기지 않는다
        content = [{'type': 'text', 'text': question}]
        if self.mode == 'citizen':
            if not location or location.get('lat') is None or location.get('lon') is None:
                return self._notice(turn, 'no_location')
            try:
                region = detect_region(self.engine, location['lat'], location['lon'], service_regions())
            except Exception as e:
                turn.errors.append({'where': 'detect_region', 'type': type(e).__name__, 'message': str(e)})
                turn.end = 'engine_error'
                return self._finish(turn)
            if region is None:
                return self._notice(turn, 'out_of_area')
            turn.location = {'region': region, 'lat': location['lat'], 'lon': location['lon']}
            content.append({'type': 'text', 'text': f'[앱 정보] 찾는 위치는 {REGION_NAMES[region]} 안이다. '
                                                    '사용자가 지금 있는 곳이 아닐 수 있다 (가족이 대신 찾는 경우 등). '
                                                    '주변 시설은 lookup_resources 로 찾는다. 위치는 자동으로 들어간다.'})
        messages = [{'role': 'user', 'content': content}]
        nudged = False
        for _ in range(MAX_CALLS):
            try:
                resp = self.client.messages.create(
                    model=self.model, max_tokens=MAX_TOKENS, system=self.system, tools=self.tools,
                    messages=messages, output_config={'effort': self.effort},
                    cache_control={'type': 'ephemeral'})      # 시스템 프롬프트·도구 정의 캐시
            except anthropic.APIError as e:                   # 네트워크·요금 한도·키·시간 초과 (SDK 가 재시도한 뒤)
                turn.errors.append({'where': 'sonnet', 'type': type(e).__name__, 'message': str(e)[:300]})
                turn.end = 'api_error'
                break
            u = resp.usage
            turn.calls.append({'stop_reason': resp.stop_reason, 'input_tokens': u.input_tokens,
                               'output_tokens': u.output_tokens,
                               'cache_read_input_tokens': getattr(u, 'cache_read_input_tokens', None) or 0,
                               'cache_creation_input_tokens': getattr(u, 'cache_creation_input_tokens', None) or 0})
            if resp.stop_reason == 'refusal':
                turn.end = 'refusal'
                break
            messages.append({'role': 'assistant', 'content': resp.content})   # thinking 블록 포함 그대로
            uses = [b for b in resp.content if b.type == 'tool_use']
            if not uses:
                if nudged or resp.stop_reason == 'max_tokens':
                    turn.end = 'no_submit'
                    break
                nudged = True
                messages.append({'role': 'user', 'content': NUDGE.format(tools=', '.join(SUBMITS[self.mode]))})
                continue
            results = []
            for b in uses:
                if b.name in SUBMITS[self.mode]:
                    r = self._submit(turn, b)
                    if r is None:
                        break
                    results.append(r)
                else:
                    results.append(self._run_tool(turn, b))
            if turn.end:
                break
            messages.append({'role': 'user', 'content': results})            # 도구 결과는 한 메시지에 모아서
        else:
            turn.end = 'max_calls'
        return self._finish(turn)


def save_run(screen: dict, turn: Turn) -> Path:
    """agent/out/runs/ 에 엔진 원본(r*.json)과 화면 조각(screen.json)을 저장한다."""
    run = turn.store.save()
    (run / 'screen.json').write_text(json.dumps(screen, ensure_ascii=False, indent=1), encoding='utf-8')
    doc_md = run / 'document.md'
    if screen['display'].get('document'):
        doc_md.write_text(screen['display']['document']['markdown'], encoding='utf-8')
    elif doc_md.exists():
        doc_md.unlink()                                            # 이전 실행의 문서가 남지 않게
    return run
