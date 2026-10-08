"""오케스트레이터: Sonnet 의 도구 호출을 반복해 질문 하나를 화면 조각까지 처리한다.

질문 → Sonnet ─┬─ 엔진 도구 호출 → 권한 확인 → 기준값 인자 제거 → 엔진 실행 → 보관 → 요약을 돌려줌 → 다시 Sonnet
               ├─ submit_answer → 검증 ─┬─ 통과 → 화면 조각
               │                        └─ 실패 → 고칠 점을 돌려주고 다시 쓰게 함 (MAX_REWRITES 회)
               └─ 제출 없이 끝남·거절·호출 한도 초과 → 안내 문구 + 지도
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agent.digest import Digester
from agent.engine_client import EngineError
from agent.prompts import build_system
from agent.screen import build_screen
from agent.store import ResultStore
from agent.tools import SUBMIT, is_allowed, strip_locked, tools_for
from agent.verifier import Context, VerifyResult, feedback, verify

MODEL = 'claude-sonnet-5-5'
EFFORT = 'medium'          # 여러 단계 도구 사용에 권장되는 시작값
MAX_TOKENS = 16000
MAX_CALLS = 8              # 질문 하나에 Sonnet 을 부르는 최대 횟수
MAX_REWRITES = 1           # 검증 실패 후 다시 쓰게 하는 횟수
NUDGE = '답을 submit_answer 도구로 제출해 주세요.'
ENV_FILE = Path(__file__).resolve().parent / '.env'


def default_client():
    import anthropic
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
        args, dropped = strip_locked(block.name, dict(block.input))
        try:
            data = self.engine.call(block.name, args)
        except EngineError as e:
            return result(str(e), error=True)
        ref = turn.store.put(block.name, args, data)
        d = turn.digester(turn.store.get(ref))
        turn.citable[ref] = d.citable
        note = f'\n(기준값 인자 {", ".join(dropped)} 는 바꿀 수 없어 기본값으로 계산했다)' if dropped else ''
        return result(d.text + note)

    # ------------------------------------------------------------ 답변 제출
    def _submit(self, turn: Turn, block) -> dict | None:
        """검증 통과면 None (끝), 다시 쓰게 할 때는 돌려줄 tool_result."""
        turn.attempts += 1
        turn.answer = dict(block.input)
        turn.check = verify(turn.answer, turn.context())
        if turn.check.passed:
            turn.end = 'passed'
            return None
        turn.rejected.append({'attempt': turn.attempts, 'errors': turn.check.errors})
        if turn.attempts > MAX_REWRITES:
            turn.end = 'verify_failed'
            return None
        return {'type': 'tool_result', 'tool_use_id': block.id, 'content': feedback(turn.check), 'is_error': True}

    # ------------------------------------------------------------ 질문 하나
    def ask(self, question: str) -> tuple[dict, Turn]:
        turn = Turn(question, self.mode)
        messages = [{'role': 'user', 'content': question}]
        nudged = False
        for _ in range(MAX_CALLS):
            resp = self.client.messages.create(
                model=self.model, max_tokens=MAX_TOKENS, system=self.system, tools=self.tools,
                messages=messages, output_config={'effort': self.effort},
                cache_control={'type': 'ephemeral'})          # 시스템 프롬프트·도구 정의 캐시
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
                messages.append({'role': 'user', 'content': NUDGE})
                continue
            results = []
            for b in uses:
                if b.name == SUBMIT:
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

        ok = turn.end == 'passed'
        check = turn.check if turn.answer is not None else None
        screen = build_screen(question, self.mode, turn.answer, check, turn.context(), turn.attempts)
        screen['internal']['run'] = {'model': self.model, 'effort': self.effort, 'end': turn.end,
                                     'passed': ok, 'calls': turn.calls, 'rejected': turn.rejected}
        return screen, turn


def save_run(screen: dict, turn: Turn) -> Path:
    """agent/out/runs/ 에 엔진 원본(r*.json)과 화면 조각(screen.json)을 저장한다."""
    run = turn.store.save()
    (run / 'screen.json').write_text(json.dumps(screen, ensure_ascii=False, indent=1), encoding='utf-8')
    return run
