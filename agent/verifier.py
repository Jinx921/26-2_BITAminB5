"""검증 단계: Sonnet 이 낸 답(분석 답변 / 문서 / 짧은 답)을 코드로 확인하고 신뢰도 등급을 정한다.

오류(errors)가 있으면 답변을 그대로 내보내지 않는다 (사유를 Sonnet 에 돌려 다시 쓰게 한다).
경고(warnings)는 기록만 한다.

① 숫자 대조   화면 문장의 숫자는 모두 citations 에 있고, 출처 값과 맞아야 한다
② 금지 표현   내부 식별자·용어, 과정 수치(기준값·강건성 출처)는 화면에 쓰지 않는다
③ 필수 caveat 반드시 반영할 한계 문장이 caveats_reflected 에 있어야 한다
④ 분량·가독성 설명은 바닥선 이상, 문단 여러 개. 긴 문장은 경고 (정보는 그대로 두고 나누라는 뜻)
⑤ 신뢰도 등급 robustness 결과로 코드가 정한다
그 밖에: 소수로 된 원래 비율 값·괄호 중복 표기 금지, 도구 결과 없는 분석 답변·제안서·보고 금지.
문서(verify_document)는 목차·분량을 문서 규격대로, 짧은 답(verify_brief)은 숫자 금지·길이 제한으로 본다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent.agent_tools import SENIOR_HOURS_NOTE, slot_label
from agent.documents import DOC_SPECS, PLACEHOLDERS, SUBMIT_DOC, doc_fields
from agent.store import ResultStore
from agent.terms import CITIZEN_BANNED
from agent.tools import AGENT_SCHEMAS, BRIEF_MAX, MODE_TOOLS, SUBMIT, SUBMIT_BRIEF

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
# 관리자: 배치 시뮬레이션의 거점 수·반경은 분석 기준이 아니라 사업 설계 조건(결론)이다
ALLOWED_PARAMS = {'citizen': ('params.radius_m',), 'admin': ('params.k', 'params.radius_m')}

# ③ 필수 caveat: 엔진 caveat 문장에서 찾을 핵심 구절 (엔진 문구가 바뀌면 테스트가 알려준다)
REQUIRED_CAVEATS = {
    # 모드: ((조건, 핵심 구절, 설명), ...). 조건 = always / 도구 이름 / 지역 이름
    'admin': (
        ('always', '거주자와 같지 않다', '유동인구는 거주자와 다르다 → 현장 확인'),
        ('classify', '두 층', '위축 신호 층과 자원 구조 층을 합쳐 말하지 않는다'),
        ('강남', '공공 보건기관', '강남 보건 거리는 공공 보건기관만 반영'),
        ('simulate_placement', '고립 감소 효과를 뜻하지 않는다', '커버는 도달 가능성일 뿐 고립 감소 효과가 아니다'),
        ('compare_interventions', '접근성(닿을 수 있는지)만 비교', '접근성만 비교, 이용량·비용·고립 감소 효과는 계산하지 않음'),
        ('compare_interventions', '보건 기능을 더한다고 가정', '경로당 거점은 보건 기능을 더한다는 가정'),
        ('senior_industries', '가게의 위치는 알 수 없다', '카드 업종은 시·구 전체 기준, 가게 위치는 모름'),
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
_RAW_RATIO = re.compile(r'(?<![\d.])0\.\d{2,}(?!\s*(?:km|㎞|m\b))')         # 0.5453 처럼 비율의 원래 값
_DOUBLED = re.compile(r'\d[\d,.]*\s*%?\s*\(\s*\d[\d,.]*\s*%?\s*\)')       # 55%(0.5453), 54%(53.66)
_AGE = re.compile(r'\d+\s*(?:대|세)\s*(?:이상|이하|미만|초과)')          # 연령 표기 (60대 이상, 65세 이상)
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
        names |= {slot_label(k) for k in (r.get('senior60_card_time_pct') or {})}     # region_context 시간대
        names |= {re.sub(r'(?<!\d)0(\d)', r'\1', n) for n in list(names) if re.fullmatch(r'\d+~\d+시', n)}  # 06~11시 = 6~11시
        names |= set(r.get('industries') or [])                 # 업종 이름 (예: 통신요금(이동,시내전화))
        if r.get('age_label'):
            names.add(r['age_label'])
        for k in ('by_emd', 'by_emd_withdrawn'):
            names |= set(r.get(k) or {})
        for k in ('cells', 'table', 'chosen_sites', 'changed_cells', 'within_radius', 'nearest_by_kind', 'matches', 'removed'):
            for row in r.get(k) or []:
                names |= {row[f] for f in ('emd_name', 'name', 'addr') if row.get(f)}
    return names


def _numbers(text: str) -> list[tuple[str, str]]:
    """문장 속 숫자 → [(정규화한 숫자, 단위)]. 칸 ID·지표 이름·목록 번호 속 숫자는 뺀다."""
    text = _IDENT.sub(' ', _CELL_ID.sub(' ', text))
    text = _AGE.sub(' ', _LIST_MARK.sub(' ', text))
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
    elif op == 'percent' and len(values) == 1:          # 비율 하나를 %로 (0.5453 → 54.5%)
        v = values[0] * 100 if values[0] <= 1 else values[0]
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
def _check_numbers(ans: dict, ctx: Context, res: VerifyResult, texts: dict | None = None,
                   params_in: tuple = ()) -> None:
    """texts: 검사할 문장 {필드: 문장} (없으면 답변의 화면 필드). params_in: 기준값을 써도 되는 필드 (제안서 '근거 데이터')."""
    texts = texts if texts is not None else {f: ans[f] for f in DISPLAY_FIELDS}
    allowed = {n for n, _ in _numbers(ctx.question)}            # 사용자가 질문에 쓴 숫자
    names = sorted(place_names(ctx.store), key=len, reverse=True)
    cited = {}
    for c in ans['citations']:
        ns = _numbers(c['text'])
        if ns:
            cited.setdefault(ns[0], c)
    # 같은 숫자를 허용된 출처(evidence·허용 params)로도 인용했으면, 기준값 위치 제한은 그 숫자에 걸지 않는다
    # (예: 보건 기준 3km 와 이동형 반경 3km 가 함께 나온 경우)
    free = set()
    for c in ans['citations']:
        ns = _numbers(c['text'])
        if ns and any(not src['metric'].startswith(PROCESS_METRIC_PREFIX)
                      or src['metric'] in ALLOWED_PARAMS.get(ctx.mode, ()) for src in c['sources']):
            free.add(ns[0])
    where = {}                                                  # 숫자 → 나온 필드들
    for f, raw in texts.items():
        text = _strip_names(raw, names)                         # 이름 속 숫자는 출처가 필요 없다
        for nu in _numbers(text):
            where.setdefault(nu, set()).add(f)
    # 거점 수별 지표(…_k3)를 인용했다면, 그 거점 수 표기("3곳")는 지표 이름의 일부로 본다
    k_cited = {m.group(1) for c in ans['citations'] for src in c['sources']
               if (m := re.search(r'_k(\d+)$', src['metric']))}
    k_label = re.compile(r'(?<!\d)(' + '|'.join(sorted(k_cited, key=len, reverse=True)) + r')\s*(?:곳|개)') if k_cited else None
    for f, raw in texts.items():
        text = _strip_names(raw, names)
        if k_label:
            text = k_label.sub(' ', text)
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
            if table is None or s['metric'] not in table or s['ref'] not in ctx.store.items:
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
            if s['metric'].startswith(PROCESS_METRIC_PREFIX) and params_in and not allowed_param:
                nu = _numbers(c['text'])[0] if _numbers(c['text']) else None
                shown_in = where.get(nu, set()) if nu else set()
                if shown_in - set(params_in) and nu not in free:
                    res.errors.append(f'기준값은 {"·".join(params_in)} 목차에만 쓴다: "{c["text"]}" ({", ".join(sorted(shown_in))})')
                continue
            if tool in PROCESS_TOOLS or (s['metric'].startswith(PROCESS_METRIC_PREFIX) and not allowed_param):
                res.errors.append(f'과정 수치를 화면에 씀: "{c["text"]}" ({tool} 결과 또는 기준값). '
                                  '기준값이나 기준을 바꾼 결과는 쓰지 않고 "현장 확인이 필요하다"처럼 쉬운 말로 쓴다')
        ks = {m.group(1) for s in c['sources'] if (m := re.search(r'_k(\d+)$', s['metric']))}
        num = _numbers(c['text'])
        if ks and num and num[0][0] in ks:                       # "3곳" = 지표 이름의 거점 수 (…_k3)
            continue
        if not bad and not _value_ok(c['text'], c['op'], values):
            res.errors.append(f'값이 출처와 다름: "{c["text"]}" ({c["op"]}, 출처 값 {values})')


def _check_banned(ans: dict, ctx: Context, res: VerifyResult, texts: dict | None = None,
                   audience: str | None = None) -> None:
    """audience: 금지어 기준 (문서는 읽는 사람 기준. 주민 안내문은 관리자 모드에서 만들어도 시민 기준)."""
    texts = texts if texts is not None else {f: ans[f] for f in DISPLAY_FIELDS}
    tool_names = set(MODE_TOOLS['admin']) | set(AGENT_SCHEMAS) | {SUBMIT, SUBMIT_DOC, SUBMIT_BRIEF}
    for f, t in texts.items():
        found = [w for w in BANNED_WORDS + BANNED_BY_MODE.get(audience or ctx.mode, ()) if w in t]
        found += [n for n in tool_names if n in t]
        found += _CELL_ID.findall(t) + _REF.findall(t)
        found += [w for w in _IDENT.findall(t) if w not in tool_names]
        for w in dict.fromkeys(found):
            res.errors.append(f'화면에 쓰면 안 되는 표현: "{w}" ({f}). 내부 이름·용어 대신 쉬운 말로 쓴다')
        for w in dict.fromkeys(_DOUBLED.findall(t)):
            res.errors.append(f'같은 값을 괄호로 두 번 쓰지 않는다: "{w}" ({f}). 숫자는 한 번만 쓴다')
        for w in dict.fromkeys(_RAW_RATIO.findall(_DOUBLED.sub(' ', t))):
            res.errors.append(f'비율의 원래 값을 쓰지 않는다: "{w}" ({f}). %로만 쓴다')


def _check_caveats(ans: dict, ctx: Context, res: VerifyResult, rules_mode: str | None = None,
                   need_caution: bool = True) -> None:
    known = set(ctx.caveat_ids.values())
    for cid in ans['caveats_reflected']:
        if cid not in known:
            res.errors.append(f'없는 caveat 번호: {cid}')
    tools = {s.tool for s in ctx.store.items.values()}
    regions = {s.data.get('region') for s in ctx.store.items.values()}
    for cond, phrase, desc in REQUIRED_CAVEATS.get(rules_mode or ctx.mode, ()):
        if cond == 'always' or cond in tools or cond in regions:
            for text, cid in ctx.caveat_ids.items():
                if phrase in text and cid not in ans['caveats_reflected']:
                    res.errors.append(f'반드시 반영할 한계가 빠짐: {cid} ({desc})')
    if need_caution and not ans['caution'].strip():
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
    if not ctx.store.items:                                       # 데이터 없이 일반 지식으로 분석하지 않게
        res.errors.append('도구 결과 없이 분석 답변을 낼 수 없다. 필요한 도구를 부르거나, '
                          '분석할 수 없는 질문(지역 밖·관계없는 질문 등)이면 submit_brief 로 짧게 답한다')
    _check_numbers(ans, ctx, res)
    _check_banned(ans, ctx, res)
    _check_caveats(ans, ctx, res)
    _check_length(ans, res)
    _check_map(ans, ctx, res)
    res.grade, res.grade_basis = grade(ctx.store, res.passed)
    res.grade_note = GRADE_NOTE[res.grade]
    return res


def _check_document(doc: dict, res: VerifyResult) -> None:
    spec = DOC_SPECS[doc['doc_type']]
    headings = [s['heading'].strip() for s in doc['sections']]
    if headings != list(spec['sections']):
        res.errors.append(f"{spec['name']} 목차가 다름: {headings} → 정해진 목차 {list(spec['sections'])} 를 순서대로 쓴다")
    for s in doc['sections']:
        body = s['body'].strip()
        if len(body) < spec['min_section']:
            res.errors.append(f"'{s['heading']}' 본문이 너무 짧음: {len(body)}자 (최소 {spec['min_section']}자)")
        limit = spec.get('max_chars', {}).get(s['heading'].strip())
        if limit and len(body) > limit:
            res.errors.append(f"'{s['heading']}'은 {limit}자 이내로 쓴다: 지금 {len(body)}자")
        for sent in re.split(r'(?<=[.!?])\s+|\n+', body):
            if len(sent.strip()) > MAX_SENTENCE_CHARS:
                res.warnings.append(f"긴 문장 ({len(sent.strip())}자, {s['heading']}): \"{sent.strip()[:30]}…\" "
                                    '→ 정보는 그대로 두고 짧은 문장 여러 개로 나눈다')


def verify_document(doc: dict, ctx: Context) -> VerifyResult:
    """문서 검증: 숫자 출처·금지 표현·필수 한계는 답변과 같게, 목차·분량은 문서 규격대로."""
    spec = DOC_SPECS[doc['doc_type']]
    texts = doc_fields(doc)
    for p in PLACEHOLDERS:                                       # 빈칸 표시는 검사하지 않는다
        texts = {f: t.replace(p, ' ') for f, t in texts.items()}
    res = VerifyResult()
    if spec['needs_data'] and not ctx.store.items:              # 제안서·보고는 데이터가 있어야 한다
        res.errors.append(f"도구 결과 없이 {spec['name']}를 쓸 수 없다. 근거가 될 도구를 먼저 부른다")
    _check_numbers(doc, ctx, res, texts, spec['params_in'])
    _check_banned(doc, ctx, res, texts, audience=spec['audience'])
    _check_caveats(doc, ctx, res, rules_mode=spec['audience'], need_caution=False)
    _check_document(doc, res)
    _check_map(doc, ctx, res)
    res.grade, res.grade_basis = grade(ctx.store, res.passed)
    res.grade_note = GRADE_NOTE[res.grade]
    return res


def verify_brief(ans: dict, ctx: Context) -> VerifyResult:
    """짧은 답 검증: 분량·필수 한계는 보지 않는 대신 숫자를 쓰지 못하고 길이를 제한한다
    (분석 내용을 짧은 답으로 내보내 검증을 피하지 못하게)."""
    res = VerifyResult()
    msg = ans['message'].strip()
    texts = {'message': msg}
    if not msg:
        res.errors.append('짧은 답이 비어 있음')
    if len(msg) > BRIEF_MAX:
        res.errors.append(f'짧은 답은 {BRIEF_MAX}자 이내로 쓴다: 지금 {len(msg)}자. 분석 결과를 전하려면 submit_answer 로 낸다')
    allowed = {n for n, _ in _numbers(ctx.question)}
    names = sorted(place_names(ctx.store), key=len, reverse=True)   # 결과에 나온 이름(개포2동 등) 속 숫자는 괜찮다
    for num, unit in _numbers(_strip_names(msg, names)):
        if num not in allowed:
            res.errors.append(f'짧은 답에는 숫자를 쓰지 않는다: "{num}{unit}". 숫자가 필요한 답은 submit_answer 로 낸다')
    _check_banned(ans, ctx, res, texts)
    res.grade, res.grade_basis = '낮음', {'reason': '짧은 답 (분석 없음)'}
    res.grade_note = ''
    return res


def feedback(res: VerifyResult, tool: str = SUBMIT) -> str:
    """다시 쓰게 할 때 Sonnet 에 돌려줄 문장. tool: 실패한 제출 도구 (같은 도구로 다시 내게 한다)."""
    lines = [f'검증에서 고칠 점이 있다. 아래를 고쳐 {tool} 로 다시 제출한다.']
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
    # 예: python -m agent.verifier agent/out/examples/4_검증_사례/실패한_답변.json --engine live
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
