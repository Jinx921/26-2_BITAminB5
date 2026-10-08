"""남은 일 5번: 문서 생성 (사업 제안서 · 현황 보고 · 주민 안내문)."""
import copy

from agent.documents import DOC_SPECS, SUBMIT_DOC, to_markdown
from agent.screen import build_screen
from agent.tests.test_verifier import QUESTION, _ctx, _required
from agent.tools import tools_for
from agent.verifier import verify_document

FILL = ' 담당 부서는 이 내용을 바탕으로 세부 계획을 정하고, 관계 기관과 함께 일정을 조율한다. 주민 의견도 함께 듣는다.'


def _proposal(ctx):
    ev = ctx.citable['r2']
    urgent, social = ev['n_긴급방문형'], ctx.citable['r2']['params.far_social_m']
    body = {
        '추진 배경': '어르신의 낮 외출이 몇 달째 줄어든 동네가 있다. 이런 동네는 가까운 시설과 이어지지 않으면 혼자 지내는 시간이 길어진다.' + FILL,
        '대상 지역': f'가장 먼저 방문이 필요한 동네(긴급방문형) {urgent}곳을 대상으로 한다. 사북면과 서면에 많다.' + FILL,
        '근거 데이터': f'통신 유동인구와 시설 위치를 함께 보았다. 교류시설이 {social}m보다 멀면 공백으로 보았다.' + FILL,
        '운영안': '이동형 건강상담을 사북면과 서면에서 순회 운영한다. 경로당과 마을회관을 거점으로 쓴다.' + FILL,
        '기대 효과': '대상 동네 어르신이 상담 서비스에 닿을 수 있는 범위가 넓어진다. 이는 접근성 개선이며 고립 감소를 뜻하지 않는다.' + FILL,
        '한계와 확인 사항': '이 결과는 머무는 사람 기준이라 실제 사는 사람과 다를 수 있다. 방문 전 현장 확인이 필요하다.' + FILL,
    }
    return {'doc_type': 'proposal', 'title': '춘천 외곽 이동형 건강상담 운영(안)',
            'sections': [{'heading': h, 'body': body[h]} for h in DOC_SPECS['proposal']['sections']],
            'caveats_reflected': _required(ctx), 'map_ref': 'r2',
            'citations': [{'text': f'{urgent}곳', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'n_긴급방문형'}]},
                          {'text': f'{social}m', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'params.far_social_m'}]}]}


def _notice(ctx):
    return {'doc_type': 'notice', 'title': '찾아가는 건강상담 안내', 'map_ref': '', 'citations': [],
            'caveats_reflected': _required(ctx),
            'sections': [
                {'heading': '방송 문구', 'body': '주민 여러분께 알려 드립니다. [날짜]부터 [장소]에서 찾아가는 건강상담이 열립니다. 많은 참여 바랍니다.'},
                {'heading': '문자 문구', 'body': '[날짜] [장소]에서 찾아가는 건강상담이 열려요. 문의 [연락처]'},
                {'heading': '게시물 문구', 'body': '찾아가는 건강상담 안내. 일시: [날짜] [시간]. 장소: [장소]. 혈압 측정과 건강 상담을 해 드려요. 문의: [연락처]'}]}


def test_good_proposal_and_notice_pass():
    ctx = _ctx()
    for doc in (_proposal(ctx), _notice(ctx)):
        r = verify_document(doc, ctx)
        assert r.passed, (doc['doc_type'], r.errors)


def test_params_only_in_evidence_section():
    ctx = _ctx()
    doc = _proposal(ctx)
    social = ctx.citable['r2']['params.far_social_m']
    doc['sections'][3]['body'] += f' 교류시설 {social}m 기준으로 거점을 정한다.'          # 운영안에 기준값
    assert any('근거 데이터 목차에만' in e for e in verify_document(doc, ctx).errors)


def test_robustness_numbers_still_banned():
    ctx = _ctx()
    doc = _proposal(ctx)
    v = ctx.citable['r3']['oat_housing_thr_100_긴급방문형']
    doc['sections'][2]['body'] += f' 기준을 바꾸면 {v}곳이 된다.'
    doc['citations'].append({'text': f'{v}곳', 'op': 'value',
                             'sources': [{'ref': 'r3', 'metric': 'oat_housing_thr_100_긴급방문형'}]})
    assert any('과정 수치' in e for e in verify_document(doc, ctx).errors)


def test_sections_and_length():
    ctx = _ctx()
    doc = _proposal(ctx)
    doc['sections'] = doc['sections'][:-1]                                        # 목차 하나 빠짐
    assert any('목차가 다름' in e for e in verify_document(doc, ctx).errors)
    rep = {'doc_type': 'report', 'title': '현황 보고', 'map_ref': '', 'citations': [], 'caveats_reflected': _required(ctx),
           'sections': [{'heading': h, 'body': '짧다.'} for h in DOC_SPECS['report']['sections']]}
    assert any('너무 짧음' in e for e in verify_document(rep, ctx).errors)


def test_notice_uses_citizen_rules():
    ctx = _ctx()
    doc = _notice(ctx)
    doc['sections'][2]['body'] += ' 고립 위험이 있는 동네를 위한 서비스입니다.'
    errs = verify_document(doc, ctx).errors
    assert any('"고립"' in e for e in errs)                                         # 관리자 모드에서 만들어도 시민 금지어
    doc = _notice(ctx)
    doc['sections'][1]['body'] = '가' * (DOC_SPECS['notice']['max_chars']['문자 문구'] + 1)
    assert any('이내로 쓴다' in e for e in verify_document(doc, ctx).errors)
    doc = _notice(ctx)
    doc['sections'][0]['body'] = doc['sections'][0]['body'].replace('[날짜]', '10월 15일')   # 지어낸 날짜
    assert any('출처 없는 숫자' in e for e in verify_document(doc, ctx).errors)


def test_screen_document_and_markdown():
    ctx = _ctx()
    doc = _proposal(ctx)
    s = build_screen(QUESTION, 'admin', doc, verify_document(doc, ctx), ctx)
    d = s['display']
    assert d['headline'].startswith('사업 제안서 초안을 만들었습니다')
    assert [x['heading'] for x in d['document']['sections']] == list(DOC_SPECS['proposal']['sections'])
    assert d['document']['markdown'] == to_markdown(doc) and '## 근거 데이터' in d['document']['markdown']
    bad = copy.deepcopy(doc)
    bad['sections'][0]['body'] += ' 칸 기준입니다.'
    assert build_screen(QUESTION, 'admin', bad, verify_document(bad, ctx), ctx)['display']['document'] is None


def test_document_tool_admin_only_and_orchestrator(tmp_path, monkeypatch):
    assert SUBMIT_DOC in {t['name'] for t in tools_for('admin')}
    assert SUBMIT_DOC not in {t['name'] for t in tools_for('citizen')}
    import agent.store as store_mod
    from agent.orchestrator import Orchestrator, save_run
    from agent.tests.test_orchestrator import SCENARIO, FakeClient, SpyEngine, _resp, _use
    monkeypatch.setattr(store_mod, 'RUNS_DIR', tmp_path)
    doc = _proposal(_ctx())
    client = FakeClient(SCENARIO + [_resp(_use(SUBMIT_DOC, doc, 9))])
    screen, turn = Orchestrator(SpyEngine(), client=client).ask('춘천 이동형 상담 제안서 써줘')
    assert turn.end == 'passed' and screen['display']['document']['type'] == 'proposal'
    run = save_run(screen, turn)
    assert (run / 'document.md').read_text(encoding='utf-8') == to_markdown(doc)


def test_same_number_two_sources():
    """보건 기준 3km(근거 데이터)와 이동형 반경 3km(운영안)처럼 같은 숫자가 다른 출처로 쓰이면 막지 않는다."""
    from agent.store import ResultStore
    from agent.digest import Digester
    from agent.engine_client import FixtureEngine
    from agent.verifier import Context
    eng, st, dg, cit = FixtureEngine(), ResultStore(), Digester(), {}
    for tool, args in [('find_candidates', {'region': '춘천'}), ('classify', {'region': '춘천'}),
                       ('simulate_placement', {'region': '춘천', 'k': 3, 'radius_m': 3000})]:
        ref = st.put(tool, args, eng.call(tool, args))
        cit[ref] = dg(st.get(ref)).citable
    ctx = Context(st, cit, dict(dg.caveat_ids), '제안서 써줘', 'admin')
    doc = _proposal(ctx)
    doc['sections'][2]['body'] += ' 보건기관이 3km보다 멀면 공백으로 보았다.'
    doc['sections'][3]['body'] += ' 차량으로 반경 3km 안을 순회한다.'
    doc['citations'] += [{'text': '3km', 'op': 'value', 'sources': [{'ref': 'r2', 'metric': 'params.far_health_m'}]},
                         {'text': '3km', 'op': 'value', 'sources': [{'ref': 'r3', 'metric': 'params.radius_m'}]}]
    assert not any('근거 데이터 목차에만' in e for e in verify_document(doc, ctx).errors)
    doc['citations'] = doc['citations'][:-1]                                      # 반경 출처가 없으면 막는다
    assert any('근거 데이터 목차에만' in e for e in verify_document(doc, ctx).errors)
