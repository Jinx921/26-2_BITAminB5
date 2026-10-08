"""남은 일 6번: 카드 근거를 운영안에 반영 (어르신 생활 업종)."""
import pytest

from agent.agent_tools import INDUSTRY_NOTE, INDUSTRY_TABLES, SENIOR_INDUSTRIES, TABLE_DIR, call_tool
from agent.digest import Digester
from agent.store import ResultStore
from agent.tools import tools_for
from agent.verifier import REQUIRED_CAVEATS, place_names

has_tables = pytest.mark.skipif(not all((TABLE_DIR / f).exists() for fs in INDUSTRY_TABLES.values() for f in fs),
                                reason='팀 EDA 결과표 없음')


@has_tables
@pytest.mark.parametrize('region', ['춘천', '강남'])
def test_reads_team_tables(region):
    r = call_tool(None, SENIOR_INDUSTRIES, {'region': region})
    res = r['result']
    assert res['senior_top'] and res['local_top'] and not any(x['industry'].startswith('ZZ_') for x in res['senior_top'])
    pct = [x['senior_pct'] for x in res['senior_top']]
    assert pct == sorted(pct, reverse=True)                                     # 표 순서 그대로 (비중 높은 순)
    assert set(res['everyday_senior']) <= {x['industry'] for x in res['local_top']}
    assert {e['metric'] for e in r['evidence']} == ({f"senior_pct_{x['industry']}" for x in res['senior_top']} |
                                                    {f"local_pct_{x['industry']}" for x in res['local_top']})
    assert INDUSTRY_NOTE in r['caveats']


@has_tables
def test_digest_names_and_required_caveat():
    st = ResultStore()
    ref = st.put(SENIOR_INDUSTRIES, {'region': '강남'}, call_tool(None, SENIOR_INDUSTRIES, {'region': '강남'}))
    text = Digester()(st.get(ref)).text
    assert '60대 이상 비중이 높은 업종 순' in text and '가게 위치는 알 수 없으니' in text
    assert '통신요금(이동,시내전화)' in place_names(st)                       # 업종 이름 속 기호·글자는 이름으로 처리
    assert any(r[0] == SENIOR_INDUSTRIES for r in REQUIRED_CAVEATS['admin'])


def test_admin_only_and_unknown_region():
    assert SENIOR_INDUSTRIES in {t['name'] for t in tools_for('admin')}
    assert SENIOR_INDUSTRIES not in {t['name'] for t in tools_for('citizen')}
    assert 'error' in call_tool(None, SENIOR_INDUSTRIES, {'region': '부산'})['result']
