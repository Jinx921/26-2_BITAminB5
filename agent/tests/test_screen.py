"""5단계: 화면 조각."""
import json

from agent.engine_client import FIXTURE_DIR, FixtureEngine
from agent.screen import FALLBACK_TEXT, build_screen
from agent.tests.test_verifier import QUESTION, _ctx, _good
from agent.verifier import build_context, verify

INTERNAL_ONLY = ('citations', 'caveats_reflected', 'caveats', 'verification', 'tool_trace', 'confidence_basis')


def _screen(ans, ctx, mode='admin'):
    return build_screen(QUESTION, mode, ans, verify(ans, ctx) if ans else None, ctx)


def test_passed_answer_display():
    ctx = _ctx()
    ans = _good(ctx)
    s = _screen(ans, ctx)
    d = s['display']
    assert s['region'] == '춘천' and s['internal']['verification']['passed']
    assert d['headline'] == ans['headline'] and len(d['details']) >= 3 and d['caution']
    assert d['confidence']['label'] in ('높음', '보통')
    for k in INTERNAL_ONLY:                                   # 내부 기록은 display 에 없다
        assert k not in d
    assert s['internal']['citations'] == ans['citations']
    json.dumps(s, ensure_ascii=False)                        # JSON 으로 내보낼 수 있다


def test_map_points_from_classify():
    ctx = _ctx()
    m = _screen(_good(ctx), ctx)['display']['map']
    table = ctx.store.get('r2').data['result']['table']
    assert m['layer'] == 'types' and m['ref'] == 'r2' and len(m['points']) == len(table)
    p = m['points'][0]
    assert set(p) == {'id', 'lat', 'lon', 'emd_name', 'type', 'gap', 'highlight'} and p['lat'] and p['lon']


def test_map_ref_to_candidates():
    ctx = _ctx()
    ans = _good(ctx)
    ans['map_ref'] = 'r1'
    m = _screen(ans, ctx)['display']['map']
    assert m['layer'] == 'candidates' and 'months' in m['points'][0]


def test_failed_answer_shows_fallback_and_map():
    ctx = _ctx()
    ans = _good(ctx)
    ans['details'] += '\n참고: 칸 기준입니다.'                # 검증 실패
    s = _screen(ans, ctx)
    d = s['display']
    assert d['headline'] == FALLBACK_TEXT['admin'] and d['details'] == [] and d['caution'] == ''
    assert '칸 기준' not in json.dumps(d, ensure_ascii=False)   # 검증 안 된 문장은 화면에 없다
    assert d['confidence']['label'] == '낮음' and d['map']['points']
    assert not s['internal']['verification']['passed'] and s['internal']['rejected_answer'] == ans
    assert s['internal']['citations'] == []


def test_no_answer():
    ctx = _ctx()
    s = build_screen(QUESTION, 'admin', None, None, ctx)
    assert s['display']['headline'] == FALLBACK_TEXT['admin']
    assert s['internal']['verification']['errors'] == ['답변이 제출되지 않음']


def test_citizen_fallback_uses_facility_map():
    ctx = build_context(FixtureEngine(), '춘천', tools=(), mode='citizen')
    example = next(FIXTURE_DIR.glob('lookup_resources_*.json'))          # 자원 조회 예시 응답
    ctx.store.put('lookup_resources', {'region': '춘천'}, json.loads(example.read_text(encoding='utf-8')))
    s = build_screen('집 근처에 갈 만한 곳 있어요?', 'citizen', None, None, ctx)
    assert s['display']['headline'] == FALLBACK_TEXT['citizen']
    assert s['display']['map']['layer'] == 'facilities' and 'name' in s['display']['map']['points'][0]


def test_caveats_reflected_flags():
    ctx = _ctx()
    ans = _good(ctx)
    cav = _screen(ans, ctx)['internal']['caveats']
    assert {c['id'] for c in cav if c['reflected']} == set(ans['caveats_reflected'])
    assert len(cav) == len(ctx.caveat_ids)


def test_highlight_mentioned_emd_admin():
    ctx = _ctx()
    ans = _good(ctx)
    pts = _screen(ans, ctx)['display']['map']['points']
    named = {p['emd_name'] for p in pts if p['emd_name'] in ans['headline']}
    assert named and all(p['highlight'] == (p['emd_name'] in named) for p in pts)
    in_details_only = {p['emd_name'] for p in pts if p['emd_name'] in ans['details']} - named
    assert not any(p['highlight'] for p in pts if p['emd_name'] in in_details_only)   # 설명에만 나온 행정동은 강조 안 함


def test_highlight_off_when_failed():
    ctx = _ctx()
    ans = _good(ctx)
    ans['details'] += '\n참고: 칸 기준입니다.'
    assert not any(p['highlight'] for p in _screen(ans, ctx)['display']['map']['points'])


def test_mentioned_prefers_longer_names():
    from agent.screen import _mentioned
    names = {'야외운동기구 소양동1', '야외운동기구 소양동10', '중앙 경로당'}
    assert _mentioned(names, '야외운동기구 소양동10이 가까워요.') == {'야외운동기구 소양동10'}
    assert _mentioned(names, '야외운동기구 소양동1, 중앙 경로당') == {'야외운동기구 소양동1', '중앙 경로당'}
