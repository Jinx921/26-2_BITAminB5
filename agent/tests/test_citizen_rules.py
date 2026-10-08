"""시민 모드 3단계: 자원 조회 요약, 좌표 숨김, 시민 검증 규칙, 시민 화면."""
import copy
import json

from agent.agent_tools import SENIOR_HOURS, call_tool
from agent.digest import Digester
from agent.engine_client import FixtureEngine
from agent.screen import LOCATION_KEYS, build_screen
from agent.store import ResultStore
from agent.terms import TYPE_NAMES
from agent.tests.test_location import LOOKUP_EXAMPLE
from agent.verifier import Context, REQUIRED_CAVEATS, verify

LOC = {'lat': LOOKUP_EXAMPLE['params']['lat'], 'lon': LOOKUP_EXAMPLE['params']['lon']}


def _ctx(region='춘천', hours=True):
    st, dg, citable = ResultStore(), Digester(hidden_params=LOCATION_KEYS), {}
    data = copy.deepcopy(LOOKUP_EXAMPLE)
    data['region'] = region
    for tool, args, d in [('lookup_resources', {'region': region, 'radius_m': 1000, **LOC}, data)] + \
            ([(SENIOR_HOURS, {'region': region}, call_tool(FixtureEngine(), SENIOR_HOURS, {'region': region}))] if hours else []):
        ref = st.put(tool, args, d)
        citable[ref] = dg(st.get(ref)).citable
    return Context(st, citable, dict(dg.caveat_ids), '어머니 댁 근처에 다니실 만한 곳 있어요?', 'citizen'), dg


def _required(ctx):
    return [c for t, c in ctx.caveat_ids.items() if any(p in t for _, p, _ in REQUIRED_CAVEATS['citizen'])]


def _good(ctx):
    nb = {r['kind']: r for r in LOOKUP_EXAMPLE['result']['nearest_by_kind']}
    hall, d = nb['경로당'], int(ctx.citable['r1']['nearest_경로당_m'])
    details = (f"가장 가까운 경로당은 {hall['name']}이에요. 직선거리로 {d}m 떨어져 있어요. 주소는 {hall['addr']}예요.\n"
               '어르신들은 보통 낮 시간에 밖에서 많이 활동하세요. 12~17시 사이에 가 보시면 다른 분들을 만나기 좋아요. '
               '다만 이 시간은 시설 운영 시간이 아니라서, 문을 여는 시간은 미리 확인해 주세요.\n'
               '혼자 가시기 어려우면 앱에서 "함께 갈 이웃 찾기"나 "이동 도움 요청"을 눌러 주세요. 담당자가 확인한 뒤 연결해 드려요. '
               '프로그램 내용은 경로당에 직접 물어보시면 자세히 알려 줄 거예요. 처음 가실 때는 가족과 함께 가 보셔도 좋아요.')
    return {'headline': f"근처에 {hall['name']}이 있어요.", 'details': details,
            'caution': '거리는 직선거리라 실제로 걷는 길은 더 멀 수 있어요. 프로그램과 운영 시간은 시설에 직접 확인해 주세요.',
            'caveats_reflected': _required(ctx),
            'citations': [{'text': f'{d}m', 'op': 'value', 'sources': [{'ref': 'r1', 'metric': 'nearest_경로당_m'}]}],
            'map_ref': 'r1'}


def test_lookup_digest_has_names_not_coordinates():
    ctx, dg = _ctx()
    text = dg(ctx.store.get('r1')).text
    first = LOOKUP_EXAMPLE['result']['nearest_by_kind'][0]
    assert first['name'] in text and first['addr'] in text
    assert str(LOC['lat']) not in text and str(LOC['lon']) not in text      # 찾을 위치 좌표는 넘기지 않는다
    assert 'params.lat' not in ctx.citable['r1'] and 'None' not in text


def test_citizen_good_answer_passes_with_address_digits():
    ctx, _ = _ctx()
    r = verify(_good(ctx), ctx)
    assert r.passed, r.errors                                               # 주소 속 숫자·12~17시는 출처 없이 통과


def test_citizen_banned_words():
    ctx, _ = _ctx()
    for bad in ['긴급방문형', TYPE_NAMES['긴급방문형'], '고립', '취약', '독거', '위험 동네', '고위험']:
        a = _good(ctx)
        a['details'] += f'\n이 동네는 {bad} 기준으로 보면 괜찮아요.'
        assert any(f'"{bad}"' in e for e in verify(a, ctx).errors), bad
    a = _good(ctx)
    a['caution'] += ' 비 오는 날에는 넘어질 위험이 있으니 조심하세요.'           # 안전 안내의 "위험"은 허용
    assert verify(a, ctx).passed


def test_admin_still_allows_type_names():
    from agent.tests.test_verifier import _ctx as admin_ctx, _good as admin_good
    c = admin_ctx()
    assert verify(admin_good(c), c).passed                                  # 관리자 답변에는 유형 이름이 들어 있다


def test_citizen_radius_allowed_admin_not():
    ctx, _ = _ctx()
    a = _good(ctx)
    a['details'] += '\n반경 1000m 안에서 찾았어요.'
    a['citations'].append({'text': '1000m', 'op': 'value', 'sources': [{'ref': 'r1', 'metric': 'params.radius_m'}]})
    assert verify(a, ctx).passed, verify(a, ctx).errors


def test_citizen_required_caveats():
    ctx, _ = _ctx()
    a = _good(ctx)
    a['caveats_reflected'] = []
    errs = ' '.join(verify(a, ctx).errors)
    assert '직선거리' in errs and '시설에 직접 확인' in errs and '운영 시간이 아니다' in errs
    assert '거주자' not in errs                                             # 관리자용 필수 한계는 시민에 걸리지 않는다


def test_citizen_invented_hour_caught():
    ctx, _ = _ctx()
    a = _good(ctx)
    a['details'] += '\n경로당은 오전 10시에 문을 열어요.'                    # 결과에 없는 운영 시간
    assert any('출처 없는 숫자: "10"' in e for e in verify(a, ctx).errors)


def test_citizen_screen_has_no_confidence_and_hidden_location():
    ctx, _ = _ctx()
    a = _good(ctx)
    s = build_screen(ctx.question, 'citizen', a, verify(a, ctx), ctx)
    assert s['display']['confidence'] is None and s['display']['map']['layer'] == 'facilities'
    dump = json.dumps(s, ensure_ascii=False)
    assert str(LOC['lat']) not in dump                                      # 화면 조각 어디에도 좌표가 없다


def test_shortened_address_and_labels():
    """줄여 쓴 주소 속 숫자, 시간대·연령 표기는 출처 없이 써도 되고, citations 에 적어도 오류가 아니다."""
    ctx, _ = _ctx()
    a = _good(ctx)
    road = next(r['addr'] for r in LOOKUP_EXAMPLE['result']['nearest_by_kind'] if r['addr'] and '번길' in r['addr'])
    short = road.split('시', 1)[-1].strip()                               # "강원특별자치도 춘천시" 를 뺀 주소
    a['details'] += f'\n도서관 주소는 {short}이에요. 60대 이상 어르신들이 12~17시에 많이 다니세요.'
    a['citations'].append({'text': '12~17시', 'op': 'value',
                           'sources': [{'ref': 'r2', 'metric': 'senior60_card_time_12_17'}]})
    r = verify(a, ctx)
    assert r.passed, r.errors
    a['details'] += '\n근처에 경로당이 7곳 더 있어요.'                       # 이름과 상관없는 숫자는 그대로 검사
    assert any('출처 없는 숫자: "7"' in e for e in verify(a, ctx).errors)


def test_citizen_highlight_mentioned_facility():
    ctx, _ = _ctx()
    a = _good(ctx)
    pts = build_screen(ctx.question, 'citizen', a, verify(a, ctx), ctx)['display']['map']['points']
    hall = next(r['name'] for r in LOOKUP_EXAMPLE['result']['nearest_by_kind'] if r['kind'] == '경로당')
    assert [p['name'] for p in pts if p['highlight']] == [hall]
