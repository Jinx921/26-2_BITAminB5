"""검증 단계: Sonnet 이 낸 submit_answer 를 코드로 확인하고 신뢰도 등급을 정한다.

오류(errors)가 있으면 답변을 그대로 내보내지 않는다 (사유를 Sonnet 에 돌려 다시 쓰게 한다).
경고(warnings)는 기록만 한다.

① 숫자 대조   화면 문장의 숫자는 모두 citations 에 있고, 출처 값과 맞아야 한다
② 금지 표현   내부 식별자·용어, 과정 수치(기준값·강건성 출처)는 화면에 쓰지 않는다
③ 필수 caveat 반드시 반영할 한계 문장이 caveats_reflected 에 있어야 한다
④ 분량·가독성 설명은 바닥선 이상, 문단 여러 개. 긴 문장은 경고 (정보는 그대로 두고 나누라는 뜻)
⑤ 신뢰도 등급 robustness 결과로 코드가 정한다
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.agent_tools import SENIOR_HOURS_NOTE
from agent.store import ResultStore
from agent.terms import CITIZEN_BANNED
from agent.tools import AGENT_SCHEMAS, MODE_TOOLS, SUBMIT

DISPLAY_FIELDS = ('headline', 'details', 'caution')

# ④ 분량·가독성 (에이전트 정책값)
MIN_DETAILS_CHARS = 300
MIN_PARAGRAPHS = 3
MAX_SENTENCE_CHARS = 80

# ⑤ 신뢰도: 기준값을 하나씩 바꿨을 때 긴급방문형 판정 겹침(urgent_jaccard)이 모두 이 값 이상이면 '높음'
GRADE_JACCARD = 0.7
GRADE_NOTE = {
    '높음': '',
    '보통': '방문 전에 현장 확인을 권합니다.',
    '낮음': '참고용입니다. 추가 확인이 필요합니다.',
}

# ② 금지 표현
BANNED_WORDS = ('evidence', 'params', 'metric', 'jaccard', 'SGIS', 'robust', '칸', '위축 신호', '위축신호')
BANNED_BY_MODE = {'citizen': CITIZEN_BANNED}   # 모드별로 더 막는 말
PROCESS_TOOLS = ('robustness',)          # 이 도구에서 온 숫자는 과정 수치
PROCESS_METRIC_PREFIX = 'params.'        # 기준값도 과정 수치
# 모드별로 화면에 써도 되는 params (시민에게 반경은 "걸어서 갈 만한 범위"라는 결론 정보)
ALLOWED_PARAMS = {'citizen': ('params.radius_m',)}

# ③ 필수 caveat: 엔진 caveat 문장에서 찾을 핵심 구절 (엔진 문구가 바뀌면 테스트가 알려준다)
REQUIRED_CAVEATS = {
    # 모드: ((조건, 핵심 구절, 설명), ...). 조건 = always / 도구 이름 / 지역 이름
    'admin': (
        ('always', '거주자와 같지 않다', '유동인구는 거주자와 다르다 → 현장 확인'),
        ('classify', '두 층', '위축 신호 층과 자원 구조 층을 합쳐 말하지 않는다'),
        ('강남', '공공 보건기관', '강남 보건 거리는 공공 보건기관만 반영'),
    ),
    'citizen': (
        ('lookup_resources', '직선거리', '거리는 직선거리라 실제로 걷는 거리와 다를 수 있다'),
        ('lookup_resources', '세부 프로그램은 기관 확인', '세부 프로그램·운영 시간은 시설에 직접 확인'),
        ('senior_hours', SENIOR_HOURS_NOTE[-14:], '시·구 전체 기준이며 시설 운영 시간이 아니다'),
        ('강남', '공공 보건기관', '보건기관은 공공 보건기관만 안내'),
    ),
}

_IDENT = re.compile(r'\b[A-Za-z]+(?:_\w+)+')                   # housing_thr, n_긴급방문형 같은 지표 이름
_CELL_ID = re.compile(r'\b\d+_\d+\b')
_REF = re.compile(r'\br\d+\b')
_LIST_MARK = re.compile(r'^\s*\d+[.)]\s', re.M)
_NUM = re.compile(r'(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(%|퍼센트|km|㎞|m(?![a-zA-Z]))?')


@dataclass
class VerifyResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    grade: str = '낮음'
    grade_note: str = GRADE_NOTE['낮음']
    grade_basis: dict = field(default_factory=dict)      # 내부 기록 (화면에 안 보임)

    @property
    def passed(self) -> bool:
        return not self.errors


@dataclass
class Context:
    """검증에 필요한 질문 단위 정보 (오케스트레이터가 채운다)."""
    store: ResultStore
    citable: dict[str, dict[str, object]]     # ref → {metric: 값} (digest 의 인용 가능 숫자)
    caveat_ids: dict[str, str]                # caveat 문장 → c 번호 (Digester.caveat_ids)
    question: str = ''
    mode: str = 'admin'


# ------------------------------------------------------------------ 숫자 읽기
def place_names(store: ResultStore) -> set[str]:
    """결과에 나온 이름: 행정동·시설 이름과 시간대 표기 (개포2동, 12~17시처럼 숫자가 든 이름은 숫자 검사에서 뺀다).
    결과에 없는 시각(예: 10시)은 이름이 아니므로 그대로 검사한다."""
    names = set()
    for s in store.items.values():
        r = s.data.get('result', {})
        names |= set((r.get('slot_labels') or {}).values())
        if r.get('age_label'):
            names.add(r['age_label'])
        for k in ('by_emd', 'by_emd_withdrawn'):
            names |= set(r.get(k) or {})
        for k in ('cells', 'table', 'chosen_sites', 'changed_cells', 'within_radius', 'nearest_by_kind'):
            for row in r.get(k) or []:
                names |= {row[f] for f in ('emd_name', 'name', 'addr') if row.get(f)}
    return names


def _numbers(text: str) -> list[tuple[str, str]]:
    """문장 속 숫자 → [(정규화한 숫자, 단위)]. 칸 ID·지표 이름·목록 번호 속 숫자는 뺀다."""
    text = _IDENT.sub(' ', _CELL_ID.sub(' ', text))
    text = _LIST_MARK.sub(' ', text)
    out = []
    for m in _NUM.finditer(text):
        num = m.group(1).replace(',', '') + (m.group(2) or '')
        unit = {'퍼센트': '%', '㎞': 'km'}.get(m.group(3), m.group(3) or '')
        out.append((num, unit))
    return out


def _strip_names(text: str, names: list[str]) -> str:
    """이름 속 숫자를 지운다. 이름 전체가 그대로 있거나(개포2동), 숫자와 그 앞 글자가 이름의 일부이면
    (줄여 쓴 주소 "서부대성로 71", "107번길 14") 이름으로 본다."""
    for n in names:                                             # 긴 이름부터
        text = text.replace(n, ' ')
    out, last = [], 0
    for m in re.finditer(r'\d+', text):
        s, e = m.span()
        is_name = any(len(text[s - k:s].strip()) >= 2 and text[s - k:e] in n
                      for k in range(2, 12) if s - k >= 0 for n in names)
        if is_name:
            out.append(text[last:s] + ' ')
            last = e
    return ''.join(out) + text[last:]


def _close(shown: float, expected: float, decimals: int) -> bool:
    return round(expected, decimals) == shown or abs(expected - shown) < 1e-9


def _value_ok(text: str, op: str, values: list[float]) -> bool:
    nums = _numbers(text)
    if len(nums) != 1:
        return False
    num, unit = nums[0]
    shown, dec = float(num), len(num.split('.')[1]) if '.' in num else 0
    if op == 'value':
        if len(values) != 1:
            return False
        v = values[0]
    elif op in ('ratio', 'percent'):
        if len(values) != 2 or values[1] == 0:
            return False
        v = values[0] / values[1]
        if op == 'percent':
            v *= 100
    elif op == 'diff':
        if len(values) != 2:
            return False
        v = values[0] - values[1]
    elif op == 'sum':
        v = sum(values)
    else:
        return False
    if unit == '%':
        cands = [v] if op == 'percent' else [v * 100, v]       # 0.55 → 55%, 82.2(이미 %) → 82.2%
    elif unit == 'km':
        cands = [v / 1000]
    else:
        cands = [v]
    return any(_close(shown, c, dec) for c in cands)


# ------------------------------------------------------------------ 검사
def _check_numbers(ans: dict, ctx: Context, res: VerifyResult) -> None:
    allowed = {n for n, _ in _numbers(ctx.question)}            # 사용자가 질문에 쓴 숫자
    names = sorted(place_names(ctx.store), key=len, reverse=True)
    cited = {}
    for c in ans['citations']:
        ns = _numbers(c['text'])
        if ns:
            cited.setdefault(ns[0], c)
    for f in DISPLAY_FIELDS:
        text = _strip_names(ans[f], names)                      # 이름 속 숫자는 출처가 필요 없다
        for num, unit in _numbers(text):
            if num in allowed:
                continue
            if (num, unit) not in cited:
                res.errors.append(f'출처 없는 숫자: "{num}{unit}" ({f}). 결과에 있는 값만 쓰고 citations 에 출처를 적는다')

    for c in ans['citations']:
        if not _numbers(_strip_names(c['text'], names)):          # 이름(시간대 등)을 출처로 적은 경우는 검사하지 않는다
            continue
        values, bad = [], False
        for s in c['sources']:
            table = ctx.citable.get(s['ref'])
            if table is None or s['metric'] not in table:
                res.errors.append(f'없는 출처: {s["ref"]}.{s["metric"]} ("{c["text"]}")')
                bad = True
                continue
            v = table[s['metric']]
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                res.errors.append(f'숫자가 아닌 출처: {s["ref"]}.{s["metric"]} ("{c["text"]}")')
                bad = True
                continue
            values.append(float(v))
            tool = ctx.store.get(s['ref']).tool
            allowed_param = s['metric'] in ALLOWED_PARAMS.get(ctx.mode, ())
            if tool in PROCESS_TOOLS or (s['metric'].startswith(PROCESS_METRIC_PREFIX) and not allowed_param):
                res.errors.append(f'과정 수치를 화면에 씀: "{c["text"]}" ({tool} 결과 또는 기준값). '
                                  '기준값이나 기준을 바꾼 결과는 쓰지 않고 "현장 확인이 필요하다"처럼 쉬운 말로 쓴다')
        if not bad and not _value_ok(c['text'], c['op'], values):
            res.errors.append(f'값이 출처와 다름: "{c["text"]}" ({c["op"]}, 출처 값 {values})')


def _check_banned(ans: dict, ctx: Context, res: VerifyResult) -> None:
    tool_names = set(MODE_TOOLS['admin']) | set(AGENT_SCHEMAS) | {SUBMIT}
    for f in DISPLAY_FIELDS:
        t = ans[f]
        found = [w for w in BANNED_WORDS + BANNED_BY_MODE.get(ctx.mode, ()) if w in t]
        found += [n for n in tool_names if n in t]
        found += _CELL_ID.findall(t) + _REF.findall(t)
        found += [w for w in _IDENT.findall(t) if w not in tool_names]
        for w in dict.fromkeys(found):
            res.errors.append(f'화면에 쓰면 안 되는 표현: "{w}" ({f}). 내부 이름·용어 대신 쉬운 말로 쓴다')


def _check_caveats(ans: dict, ctx: Context, res: VerifyResult) -> None:
    known = set(ctx.caveat_ids.values())
    for cid in ans['caveats_reflected']:
        if cid not in known:
            res.errors.append(f'없는 caveat 번호: {cid}')
    tools = {s.tool for s in ctx.store.items.values()}
    regions = {s.data.get('region') for s in ctx.store.items.values()}
    for cond, phrase, desc in REQUIRED_CAVEATS.get(ctx.mode, ()):
        if cond == 'always' or cond in tools or cond in regions:
            for text, cid in ctx.caveat_ids.items():
                if phrase in text and cid not in ans['caveats_reflected']:
                    res.errors.append(f'반드시 반영할 한계가 빠짐: {cid} ({desc})')
    if not ans['caution'].strip():
        res.errors.append('확인할 점(caution)이 비어 있음')


def _check_length(ans: dict, res: VerifyResult) -> None:
    d = ans['details'].strip()
    if len(d) < MIN_DETAILS_CHARS:
        res.errors.append(f'설명이 너무 짧음: {len(d)}자 (최소 {MIN_DETAILS_CHARS}자). 정보를 더 구체적으로 쓴다')
    paras = [p for p in re.split(r'\n+', d) if p.strip()]
    if len(paras) < MIN_PARAGRAPHS:
        res.errors.append(f'설명 문단이 {len(paras)}개 (최소 {MIN_PARAGRAPHS}개). '
                          '어디·왜 / 어떤 상황 / 무엇을 하면 좋은지를 문단으로 나눈다')
    for f in DISPLAY_FIELDS:
        for s in re.split(r'(?<=[.!?])\s+|\n+', ans[f]):
            if len(s.strip()) > MAX_SENTENCE_CHARS:
                res.warnings.append(f'긴 문장 ({len(s.strip())}자, {f}): "{s.strip()[:30]}…" '
                                    '→ 정보는 그대로 두고 짧은 문장 여러 개로 나눈다')


def _check_map(ans: dict, ctx: Context, res: VerifyResult) -> None:
    ref = ans['map_ref']
    if not ref:
        return
    if ref not in ctx.store.items:
        res.errors.append(f'없는 지도 참조: {ref}')
    elif ctx.store.get(ref).tool in ('robustness', 'region_context'):
        res.errors.append(f'지도로 그릴 수 없는 결과: {ref} ({ctx.store.get(ref).tool})')


def grade(store: ResultStore, passed: bool) -> tuple[str, dict]:
    """신뢰도 등급과 내부 근거. 검증 실패·robustness 없음 → 낮음."""
    rob = store.by_tool('robustness')
    if not passed:
        return '낮음', {'reason': '검증 실패'}
    if not rob:
        return '낮음', {'reason': 'robustness 결과 없음'}
    rows = [o for o in rob[-1].data['result'].get('one_at_a_time', [])
            if not o['is_default'] and o['urgent_jaccard'] is not None]
    if not rows:
        return '낮음', {'reason': '비교할 강건성 결과 없음'}
    low = sorted((o for o in rows if o['urgent_jaccard'] < GRADE_JACCARD), key=lambda o: o['urgent_jaccard'])
    basis = {'ref': rob[-1].ref, 'threshold': GRADE_JACCARD, 'min_jaccard': min(o['urgent_jaccard'] for o in rows),
             'sensitive': [{'param': o['param'], 'value': o['value'], 'urgent_jaccard': o['urgent_jaccard']} for o in low]}
    return ('보통' if low else '높음'), basis


def verify(ans: dict, ctx: Context) -> VerifyResult:
    res = VerifyResult()
    _check_numbers(ans, ctx, res)
    _check_banned(ans, ctx, res)
    _check_caveats(ans, ctx, res)
    _check_length(ans, res)
    _check_map(ans, ctx, res)
    res.grade, res.grade_basis = grade(ctx.store, res.passed)
    res.grade_note = GRADE_NOTE[res.grade]
    return res


def feedback(res: VerifyResult) -> str:
    """다시 쓰게 할 때 Sonnet 에 돌려줄 문장."""
    lines = ['답변 검증에서 고칠 점이 있다. 아래를 고쳐 submit_answer 로 다시 제출한다.']
    lines += [f'- {e}' for e in res.errors]
    lines += [f'- (권장) {w}' for w in res.warnings]
    return '\n'.join(lines)


def build_context(engine, region: str, question: str = '',
                  tools=('find_candidates', 'classify', 'robustness'), mode: str = 'admin') -> Context:
    """도구들을 차례로 불러 검증 문맥을 만든다 (터미널 확인·예시 생성용. 실제 흐름은 오케스트레이터가 채운다)."""
    from agent.digest import Digester
    st, dg, citable = ResultStore(), Digester(), {}
    for t in tools:
        ref = st.put(t, {'region': region}, engine.call(t, {'region': region}))
        citable[ref] = dg(st.get(ref)).citable
    return Context(st, citable, dict(dg.caveat_ids), question, mode)


if __name__ == '__main__':
    # 예: python -m agent.verifier agent/out/examples/3_Sonnet답변_춘천_검증전.json --engine live
    # 답변 JSON(submit_answer 입력)을 시나리오 도구 세 개 결과에 대고 검증한다 (도구 호출 순서 r1, r2, r3 가정)
    import argparse
    import json
    from pathlib import Path

    from agent.engine_client import make_engine

    ap = argparse.ArgumentParser(description='저장된 submit_answer 답변을 검증한다')
    ap.add_argument('answer')
    ap.add_argument('--region', default='춘천')
    ap.add_argument('--engine', choices=['live', 'fixture'], default='fixture')
    ap.add_argument('--question', default='')
    a = ap.parse_args()

    ctx = build_context(make_engine(a.engine), a.region, a.question)
    ans = json.loads(Path(a.answer).read_text(encoding='utf-8'))
    r = verify(ans, ctx)
    print('통과' if r.passed else f'오류 {len(r.errors)}개')
    for e in r.errors:
        print('  [오류]', e)
    for w in r.warnings:
        print('  [경고]', w)
    print(f'신뢰도: {r.grade}  {r.grade_note}')
    print('신뢰도 근거 (내부):', json.dumps(r.grade_basis, ensure_ascii=False))
