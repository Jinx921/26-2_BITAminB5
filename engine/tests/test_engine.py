"""엔진 검증: 재현 · 결정성 · 규격. 실행: python -m pytest tests -q (engine 폴더에서)"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core  # noqa: E402

KEYS = {'tool', 'region', 'result', 'evidence', 'caveats', 'figures', 'geojson', 'params'}


def test_team_candidates_reproduced():
    cm = core._cells()
    assert cm[cm.region == '강남'].is_candidate.sum() == 65
    assert cm[cm.region == '춘천'].is_candidate.sum() == 192


def test_engine_detection_matches_team():
    team = pd.read_parquet(core.C.DATA / 'team' / 'srh_07_candidate_cells.parquet')
    teams = set(zip(team.region, team.cell_id))
    mine = set()
    for reg in core.C.REGIONS:
        d = core._detect(reg, core.C.NIGHT_THR[reg], core.C.HOUSING_THR[reg])
        mine |= {(reg, c) for c in d.index[d.persistent_months >= core.C.PERSIST_MIN]}
    assert mine == teams


def test_housing_sensitivity_matches_team():
    n = {h: int((core._detect('춘천', 0.03, h).persistent_months >= 4).sum()) for h in (0, 30, 100, 200)}
    assert n == {0: 466, 30: 192, 100: 92, 200: 63}


def test_cell_counts():
    cm = core._cells()
    assert (cm.region == '강남').sum() == 698
    assert (cm.region == '춘천').sum() == 7393
    assert cm.emd_name.notna().all()


def test_residential_filter_drops():
    g = core.find_candidates('강남', render=False)['result']
    c = core.find_candidates('춘천', render=False)['result']
    assert g['n_candidates'] == 51 and g['dropped_status'] == {'건물없음': 14}
    assert c['n_candidates'] == 153 and c['dropped_status'] == {'건물없음': 34, '비주거': 5}


def test_old_abcd_reproduced():
    """채원 A~D(경로당·보건, 도시 내 상위 25%)를 엔진 시설 테이블로 재현.
    채원 코드는 칸 중심이 아니라 flow_cell 좌표에서 거리를 재므로 같은 좌표로 계산한다.
    (엔진 기본은 팀 원칙대로 칸 중심 → 강남 경계 1칸 차이 393/130/130/45)"""
    from scipy.spatial import cKDTree
    f = pd.read_parquet(core.C.FLOW).drop_duplicates('cell_id')
    f['region'] = f.sgg_nm.map({'강남구': '강남', '춘천시': '춘천'})
    fac = core._fac()
    exp = {'강남': [394, 129, 129, 46], '춘천': [4544, 1000, 1000, 849]}
    for reg, e in exp.items():
        d = f[f.region == reg]
        ds = cKDTree(fac[(fac.region == reg) & (fac.kind == '경로당')][['x', 'y']]).query(d[['x', 'y']])[0]
        dh = cKDTree(fac[(fac.region == reg) & (fac.kind == '보건')][['x', 'y']]).query(d[['x', 'y']])[0]
        fs = ds >= np.quantile(ds, .75)
        fh = dh >= np.quantile(dh, .75)
        got = [(~fs & ~fh).sum(), (fs & ~fh).sum(), (~fs & fh).sum(), (fs & fh).sum()]
        assert got == e, (reg, got)


@pytest.mark.parametrize('region', ['강남', '춘천'])
def test_contract_and_determinism(region):
    for fn, kw in [(core.find_candidates, {}), (core.classify, {}), (core.simulate_placement, {'k': 2, 'k_max': 2}),
                   (core.robustness, {}), (core.region_context, {})]:
        if 'render' in fn.__code__.co_varnames:
            kw = {**kw, 'render': False}
        a, b = fn(region, **kw), fn(region, **kw)
        assert KEYS <= set(a), fn.__name__
        json.dumps(a, ensure_ascii=False)                 # 직렬화 가능
        assert a == b, f'{fn.__name__} 결과가 호출마다 다름'
        for e in a['evidence']:
            assert {'metric', 'value'} <= set(e)


def test_type_counts_default():
    t = core.classify('춘천', render=False)['result']['type_counts']
    assert t == {'연계형': 98, '긴급방문형': 55, '예방인프라형': 101, '관찰형': 1361}


def test_simulation_monotonic():
    curve = core.simulate_placement('춘천', k=3, k_max=5, render=False)['result']['k_curve']
    s = [c['covered_senior_share'] for c in curve]
    assert all(np.diff(s) >= -1e-9)


def test_mclp_optimal_vs_bruteforce():
    """작은 문제에서 MCLP 해가 전수 탐색 최적값과 같은지."""
    from itertools import combinations
    rng = np.random.default_rng(0)
    dem = rng.uniform(0, 3000, (25, 2)); w = rng.uniform(1, 10, 25)
    sites = rng.uniform(0, 3000, (12, 2)); rad = 700
    chosen, covered = core._mclp(dem, w, sites, 3, rad)
    got = w[covered].sum()
    best = 0
    for comb in combinations(range(12), 3):
        cov = np.zeros(25, bool)
        for j in comb:
            cov |= np.hypot(*(dem - sites[j]).T) <= rad
        best = max(best, w[cov].sum())
    assert abs(got - best) < 1e-6 and core._mclp.last_status['optimal']


def test_simulation_reports_optimal():
    r = core.simulate_placement('춘천', k=3, k_max=3, render=False)
    assert r['params']['all_optimal'] is True


def test_check_residential_and_lookup_cell():
    r = core.check_residential(['3853_7769', 'NOPE'])
    assert r['result']['not_found'] == ['NOPE'] and len(r['result']['cells']) == 1
    cid = core.find_candidates('춘천', render=False)['result']['cells'][0]['cell_id']
    lk = core.lookup_resources('춘천', cell_id=cid)
    assert lk['result']['nearest_by_kind'] and KEYS <= set(lk)


def test_facility_change_consistency():
    r = core.facility_change('춘천', remove_ids=['CC_00225'], render=False)
    assert r['result']['n_changed_cells'] == 9          # 연계→긴급 7 + 관찰→예방 2 (예방 분위 재계산)
    assert r['result']['transitions']['연계형'].get('긴급방문형') == 7
    none = core.facility_change('춘천', render=False)          # 아무것도 안 바꾸면 변화 0
    assert none['result']['n_changed_cells'] == 0


def test_caveats_consistent():
    for fn in (core.robustness, core.facility_change):
        cav = fn('강남')['caveats'] if fn is core.robustness else fn('강남', render=False)['caveats']
        assert core.C.CAVEAT_GANGNAM_HEALTH in cav and core.C.CAVEAT_RESID in cav


def test_lookup_citizen():
    r = core.lookup_resources('춘천', lat=37.8813, lon=127.7298, radius_m=1000)
    assert r['result']['count_within_radius'].get('경로당', 0) > 0
    fb = r['result']['fallback_nearby']
    assert fb and not any(a['beyond_radius'] for a in fb if a['kind'] == '경로당')


def test_lookup_rural_fallback():                   # 10/18 외곽: 반경 안이 비어도 종류별 가까운 곳(5km 안)은 나온다
    r = core.lookup_resources('춘천', lat=37.9747, lon=127.9069, radius_m=1000)['result']   # 북산면
    fb = r['fallback_nearby']
    assert r['within_radius'] == [] and fb and all(a['beyond_radius'] for a in fb)
    assert len({a['kind'] for a in fb}) == len(fb)                       # 종류마다 1곳
    assert all(a['dist_m'] <= core.C.FALLBACK_MAX_M for a in fb)
    assert {a['kind'] for a in r['nearest_by_kind']} - {a['kind'] for a in fb}   # 5km 밖 종류는 대체 목록에서만 빠짐


def test_bad_inputs_return_json():                  # Codex 교차검토 10/1
    for r in [core.simulate_placement('강남', k=0, k_max=0, render=False),
              core.lookup_resources('춘천', cell_id='3826_7789')]:
        assert KEYS <= set(r) and 'error' in r['result']
    big = core.simulate_placement('강남', k=100000, k_max=1, render=False)
    assert KEYS <= set(big) and big['params']['k'] < 100000 and big['result']['covered_cells'] == big['result']['n_target_cells']
    rb = core.robustness('강남', persist_list=(5,), social_list=(300,), health_list=(3000,),
                         residential_list=(True,), night_scale=(1.0,), housing_list=(100,))
    assert rb['result']['default_row']['persist_min'] == 4
    fc = core.facility_change('춘천', remove_ids=['GN_00000'], render=False)['result']
    assert fc['removed'] == [] and fc['not_found'] == ['GN_00000'] and fc['n_changed_cells'] == 0


def test_evidence_matches_result():
    s = core.simulate_placement('춘천', render=False)
    ev = {e['metric']: e['value'] for e in s['evidence']}
    assert ev['covered_senior_share_k3'] == s['result']['covered_senior_share']
