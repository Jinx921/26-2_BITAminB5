"""4단계: 검증. 답변 숫자는 예시 응답 evidence 에서 꺼내 쓴다 (엔진 숫자를 테스트에 적지 않는다)."""
import copy
import json

import pytest

from agent.digest import Digester
from agent.engine_client import FIXTURE_DIR, FixtureEngine
from agent.store import ResultStore, StoredResult
from agent.verifier import (GRADE_NOTE, MIN_DETAILS_CHARS, REQUIRED_CAVEATS, Context, feedback, grade, verify)

QUESTION = '춘천에서 어디부터 확인해야 해?'


def _ctx(region='춘천', tools=('find_candidates', 'classify', 'robustness')):
    eng, st, dg = FixtureEngine(), ResultStore(), Digester()
    citable = {}
    for t in tools:
        ref = st.put(t, {'region': region}, eng.call(t, {'region': region}))
        citable[ref] = dg(st.get(ref)).citable
    return Context(store=st, citable=citable, caveat_ids=dict(dg.caveat_ids), question=QUESTION)


def _cid(ctx, phrase):
    return next(c for t, c in ctx.caveat_ids.items() if phrase in t)


def _required(ctx):
    return [c for t, c in ctx.caveat_ids.items() if any(p in t for _, p, _ in REQUIRED_CAVEATS)]


def _good(ctx):
    """통과해야 하는 답변: 결론 수치만, 출처 있음, 필수 caveat 반영, 문단 3개."""
    ev = ctx.citable['r2']
    urgent, link = ev['n_긴급방문형'], ev['n_연계형']
    details = (f'가장 먼저 방문이 필요한 동네(긴급방문형)는 {urgent}곳입니다.\n'
               '이 동네들은 어르신의 낮 외출이 몇 달째 줄었습니다. 경로당이나 보건소도 멀리 떨어져 있습니다.\n'
               f'가까운 시설과 이어 주면 좋은 동네(연계형)는 {link}곳입니다. 시설은 가깝지만 이용이 적은 곳입니다.\n'
               '먼저 방문 안부와 이동형 건강상담을 권합니다. 연계형 동네는 경로당 프로그램과 동행 지원을 함께 안내하면 좋습니다. '
               '두 종류의 동네는 필요한 도움이 다르므로 담당 인력을 나눠 배치하는 것이 효과적입니다.\n'
               '방문할 때는 어르신이 혼자 지내시는지, 가까운 이웃과 연락이 닿는지도 함께 살펴 주세요. '
               '도움이 필요하면 보건소 방문 건강관리와 연결할 수 있습니다.')
    assert len(details) >= MIN_DETAILS_CHARS
    return {
        'headline': '사북면과 서면을 먼저 확인하세요.',
        'details': details,
        'caution': '실제로 사람이 사는 집인지는 현장에서 확인해야 합니다.',
        'caveats_reflected': _required(ctx),
        'citations': [{'text': f'{urgent}곳', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'n_긴급방문형'}]},
                      {'text': f'{link}곳', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'n_연계형'}]}],
        'map_ref': 'r2',
    }


@pytest.fixture
def ctx():
    return _ctx()


def test_good_answer_passes(ctx):
    r = verify(_good(ctx), ctx)
    assert r.passed, r.errors


# ---------------------------------------------------------------- ① 숫자 대조
def test_uncited_number(ctx):
    a = _good(ctx)
    a['details'] += '\n먼저 볼 곳은 서면 2곳입니다.'          # 첫 실제 출력의 "서면 2곳" 같은 경우
    assert any('출처 없는 숫자: "2"' in e for e in verify(a, ctx).errors)


def test_wrong_value(ctx):
    a = _good(ctx)
    wrong = ctx.citable['r2']['n_긴급방문형'] + 1
    a['details'] = a['details'].replace(a['citations'][0]['text'], f'{wrong}곳')
    a['citations'][0]['text'] = f'{wrong}곳'
    assert any('값이 출처와 다름' in e for e in verify(a, ctx).errors)


def test_unknown_source(ctx):
    a = _good(ctx)
    a['citations'][0]['sources'] = [{'ref': 'r2', 'metric': 'n_없는지표'}]
    assert any('없는 출처' in e for e in verify(a, ctx).errors)


def test_renderings(ctx):
    """1,361 = 1361 / 3km = 3000(m) / 표시 자릿수로 반올림한 비율·퍼센트는 통과."""
    ev = ctx.citable['r2']
    big, urgent, total = ev['n_관찰형'], ev['n_긴급방문형'], ev['n_universe_cells']
    pct = round(urgent / total * 100, 1)
    a = _good(ctx)
    a['details'] += f'\n전체 거주 동네 중 {pct}%가 긴급방문형입니다. 정기적으로 지켜볼 동네는 {big:,}곳입니다.'
    a['citations'] += [
        {'text': f'{pct}%', 'op': 'percent', 'sources': [{'ref': 'r2', 'metric': 'n_긴급방문형'},
                                                        {'ref': 'r2', 'metric': 'n_universe_cells'}]},
        {'text': f'{big:,}곳', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'n_관찰형'}]}]
    r = verify(a, ctx)
    assert r.passed, r.errors
    a['citations'][-2]['text'] = f'{pct + 1}%'                  # 계산이 틀리면 오류
    a['details'] = a['details'].replace(f'{pct}%', f'{pct + 1}%')
    assert any('값이 출처와 다름' in e for e in verify(a, ctx).errors)


def test_question_and_list_numbers_ignored(ctx):
    a = _good(ctx)
    c = _ctx()
    c.question = '춘천에서 3곳만 골라줘'
    a['details'] = '1. ' + a['details'].replace('\n', '\n2. ', 1) + '\n그중 3곳을 고르면 됩니다.'
    assert verify(a, c).passed, verify(a, c).errors


# ---------------------------------------------------------------- ② 금지 표현
@pytest.mark.parametrize('bad', ['4026_7935', 'classify', 'r2', 'housing_thr', 'n_긴급방문형', '칸', '위축 신호', 'SGIS'])
def test_banned_in_display(ctx, bad):
    a = _good(ctx)
    a['details'] += f'\n참고: {bad} 기준입니다.'
    assert any(f'"{bad}"' in e for e in verify(a, ctx).errors), bad


def test_floating_population_allowed(ctx):
    a = _good(ctx)
    a['caution'] = '통신 유동인구는 사는 사람과 다를 수 있어 현장에서 확인해야 합니다.'
    assert verify(a, ctx).passed


@pytest.mark.parametrize('ref, metric', [('r3', 'oat_housing_thr_100_긴급방문형'), ('r2', 'params.far_social_m')])
def test_process_numbers(ctx, ref, metric):
    """두 번째 실제 출력의 "주택 수 기준을 높이면 N곳" 같은 과정 수치는 막는다."""
    v = ctx.citable[ref][metric]
    a = _good(ctx)
    a['caution'] += f' 기준을 바꾸면 {v}곳이 됩니다.'
    a['citations'].append({'text': f'{v}곳', 'op': 'value', 'sources': [{'ref': ref, 'metric': metric}]})
    assert any('과정 수치' in e for e in verify(a, ctx).errors)


# ---------------------------------------------------------------- ③ 필수 caveat
def test_required_caveats_match_engine_text():
    """필수 caveat 핵심 구절이 실제 엔진 caveat 에 있다 (엔진 문구가 바뀌면 여기서 실패)."""
    texts = {c for p in FIXTURE_DIR.glob('*.json') for c in json.loads(p.read_text(encoding='utf-8'))['caveats']}
    for _, phrase, _ in REQUIRED_CAVEATS:
        assert any(phrase in t for t in texts), phrase


def test_missing_required_caveat(ctx):
    a = _good(ctx)
    a['caveats_reflected'].remove(_cid(ctx, '두 층'))
    assert any('반드시 반영할 한계' in e for e in verify(a, ctx).errors)


def test_gangnam_health_caveat():
    c = _ctx('강남')
    a = _good(c)
    assert verify(a, c).passed
    a['caveats_reflected'].remove(_cid(c, '공공 보건기관'))
    assert any('공공 보건기관만' in e for e in verify(a, c).errors)


def test_unknown_caveat_and_empty_caution(ctx):
    a = _good(ctx)
    a['caveats_reflected'].append('c99')
    a['caution'] = ' '
    errs = verify(a, ctx).errors
    assert any('없는 caveat 번호: c99' in e for e in errs) and any('caution' in e for e in errs)


# ---------------------------------------------------------------- ④ 분량·가독성
def test_too_short_and_few_paragraphs(ctx):
    a = _good(ctx)
    a['details'] = a['details'].split('\n')[0]
    errs = verify(a, ctx).errors
    assert any('너무 짧음' in e for e in errs) and any('문단' in e for e in errs)


def test_long_sentence_is_warning_only(ctx):
    a = _good(ctx)
    a['details'] += '\n' + '방문 안부와 프로그램 연결을 함께 진행하면서 ' * 4 + '효과를 살핍니다.'
    r = verify(a, ctx)
    assert r.passed and any('긴 문장' in w for w in r.warnings)


def test_map_ref(ctx):
    a = _good(ctx)
    a['map_ref'] = 'r3'
    assert any('지도로 그릴 수 없는' in e for e in verify(a, ctx).errors)
    a['map_ref'] = 'r9'
    assert any('없는 지도 참조' in e for e in verify(a, ctx).errors)


# ---------------------------------------------------------------- ⑤ 신뢰도
def test_grade_from_robustness(ctx):
    r = verify(_good(ctx), ctx)
    rows = [o for o in ctx.store.get('r3').data['result']['one_at_a_time']
            if not o['is_default'] and o['urgent_jaccard'] is not None]
    expected = '높음' if all(o['urgent_jaccard'] >= 0.7 for o in rows) else '보통'
    assert r.grade == expected and r.grade_note == GRADE_NOTE[expected]
    assert r.grade_basis['ref'] == 'r3'


def test_grade_without_robustness_or_failed():
    c = _ctx(tools=('find_candidates', 'classify'))
    assert verify(_good(c), c).grade == '낮음'
    assert grade(_ctx().store, passed=False)[0] == '낮음'


def test_grade_high_when_stable(ctx):
    st = ResultStore()
    rob = copy.deepcopy(ctx.store.get('r3').data)
    for o in rob['result']['one_at_a_time']:
        o['urgent_jaccard'] = 0.9
    st.put('robustness', {}, rob)
    assert grade(st, passed=True)[0] == '높음'


def test_feedback_lists_errors(ctx):
    a = _good(ctx)
    a['details'] += '\n참고: 칸 기준입니다.'
    text = feedback(verify(a, ctx))
    assert text.startswith('답변 검증에서 고칠 점') and '"칸"' in text


def test_place_name_numbers_allowed():
    """개포2동처럼 결과에 나온 이름 속 숫자는 출처 없이 써도 된다 (이름을 '개포이동'으로 바꾸지 않게)."""
    c = _ctx('강남')
    named = [e for e in c.store.get('r2').data['result']['by_emd_withdrawn'] if any(ch.isdigit() for ch in e)]
    assert named
    a = _good(c)
    a['headline'] = f'{named[0]}을 먼저 확인하세요.'
    assert verify(a, c).passed, verify(a, c).errors
    a['headline'] = f'{named[0]} 주변 7곳을 먼저 확인하세요.'          # 이름 밖의 숫자는 그대로 검사
    assert any('출처 없는 숫자: "7"' in e for e in verify(a, c).errors)
