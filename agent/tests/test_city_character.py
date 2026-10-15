"""차별점 ③ 도시 성격: 엔진 지역 맥락의 로컬 결제 비율로 방문 도시 / 주민 생활권을 밝히고, 생활 반경·고립 신호로 해석하지 않는다."""
from agent.digest import CITY_CHARACTER, Digester
from agent.prompts import build_system
from agent.tests.test_verifier import _ctx, _good
from agent.verifier import verify

TOOLS = ('find_candidates', 'classify', 'robustness', 'region_context')
LOCAL_PHRASE = '생활 반경·고립 신호로 해석하지 않고'


def _with_local(ctx, reflect=True):
    ans = _good(ctx)
    pct = ctx.citable['r4']['local_payment_pct']
    ans['details'] += f'\n지역 가게 결제의 {pct}%를 지역 주민이 써서, 주민이 사는 동네로 찾아가는 방식이 맞는 도시입니다.'
    ans['citations'].append({'text': f'{pct}%', 'op': 'value', 'sources': [{'ref': 'r4', 'metric': 'local_payment_pct'}]})
    if not reflect:
        local = next(c for t, c in ctx.caveat_ids.items() if LOCAL_PHRASE in t)
        ans['caveats_reflected'] = [c for c in ans['caveats_reflected'] if c != local]
    return ans


def test_digest_city_character_line():
    for region, label in CITY_CHARACTER.items():
        ctx = _ctx(region, TOOLS)
        text = Digester()(ctx.store.get('r4')).text
        assert f'도시 성격: {label}' in text and 'local_payment_pct' in text


def test_citing_local_payment_requires_caveat():
    ctx = _ctx('춘천', TOOLS)
    assert verify(_with_local(ctx), ctx).passed
    res = verify(_with_local(ctx, reflect=False), ctx)
    assert any('반드시 반영할 한계가 빠짐' in e and '도시 성격' in e for e in res.errors)


def test_local_caveat_not_required_without_citation():
    ctx = _ctx('춘천', TOOLS)
    ans = _good(ctx)
    local = next(c for t, c in ctx.caveat_ids.items() if LOCAL_PHRASE in t)
    ans['caveats_reflected'] = [c for c in ans['caveats_reflected'] if c != local]
    assert verify(ans, ctx).passed                                  # 로컬 결제 비율을 쓰지 않았으면 요구하지 않는다


def test_prompt_city_rules_admin_only():
    admin, citizen = build_system('admin'), build_system('citizen')
    assert '[도시 성격]' in admin and '생활 반경이나 고립 신호로 말하지 않는다' in admin
    assert '도시 성격·지역 가게 결제 비중은 쓰지 않는다' in admin               # 주민 안내문 제외
    assert '[도시 성격]' not in citizen
