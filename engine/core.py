"""분석 엔진 도구 (에이전트가 호출하는 계산 전부).

모든 도구는 같은 형식의 dict(JSON 직렬화 가능)를 반환한다.
  tool, region, result, evidence, caveats, figures, geojson, params
evidence 에 들어간 숫자만 에이전트가 답변에 쓸 수 있다 (검증 에이전트가 대조).
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.spatial import cKDTree

import config as C
import render as R

TO_UTMK = Transformer.from_crs('EPSG:4326', 'EPSG:5179', always_xy=True)
TO_WGS = Transformer.from_crs('EPSG:5179', 'EPSG:4326', always_xy=True)


# ---------------------------------------------------------------- 공통
@lru_cache(maxsize=1)
def _cells() -> pd.DataFrame:
    cm = pd.read_parquet(C.DATA / 'cell_master.parquet')
    names = pd.read_parquet(C.DATA / 'emd_names.parquet')
    # SGIS 1km 격자 값 (같은 1km 안 250m 칸은 같은 값을 공유)
    sg = pd.read_parquet(C.DATA / 'sgis_grid.parquet')[['GRID_CD', 'total_housing', 'senior65_share', 'hh_1p_share',
                                                        'apt_share', 'detached_share', 'reliable_senior65', 'reliable_hh_1p']]
    gm = pd.read_parquet(C.DATA / 'cell_grid_map.parquet')
    cm = cm.drop(columns=['GRID_CD'], errors='ignore').merge(gm, on=['region', 'cell_id'], how='left')
    return cm.merge(names, on='emd8', how='left').merge(sg, on='GRID_CD', how='left')


@lru_cache(maxsize=1)
def _cell_month() -> pd.DataFrame:
    return pd.read_parquet(C.DATA / 'cell_month.parquet')


@lru_cache(maxsize=64)
def _detect(region: str, night_thr: float, housing_thr: float, senior_q: float = 0.75) -> pd.DataFrame:
    """사랑 후보 로직 (src/eda_srh.py) 을 기준값을 바꿔 다시 계산.
    반환: 칸별 resident_any(한 달이라도 거주 조건 통과), persistent_months(거주 & 고령상위 & 낮활동 z<0 인 달 수)"""
    w = _cell_month()
    w = w[w.region == region]
    res = (w.night_share >= night_thr) & (w.total_housing >= housing_thr)
    thr = w.loc[res, 'senior_ratio'].quantile(senior_q)
    hit = res & (w.senior_ratio >= thr) & (w.dev_day_share < 0)
    out = pd.DataFrame({'resident_any': res.groupby(w.cell_id).any()})
    out['persistent_months'] = w[hit].groupby('cell_id').STD_YM.nunique()
    out['persistent_months'] = out.persistent_months.fillna(0).astype(int)
    return out


@lru_cache(maxsize=1)
def _fac() -> pd.DataFrame:
    return pd.read_parquet(C.DATA / 'facility.parquet')


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else round(float(o), 4)
    if isinstance(o, float):
        return None if np.isnan(o) else round(o, 4)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _pack(tool, region, result, evidence, params, caveats=(), figures=(), geojson=None):
    cav = list(C.CAVEATS) + list(caveats)
    uses_universe = ('find_candidates', 'classify', 'simulate_placement', 'robustness', 'facility_change', 'region_context')
    if region == '강남' and tool in uses_universe + ('lookup_resources',):
        cav.append(C.CAVEAT_GANGNAM_HEALTH)
    if tool in uses_universe:
        cav += [C.CAVEAT_RESID, C.CAVEAT_SGIS]
    if tool in ('classify', 'robustness', 'facility_change', 'region_context'):
        cav.append(C.CAVEAT_LAYERS)
    cav = list(dict.fromkeys(cav))
    return _clean({'tool': tool, 'region': region, 'result': result, 'evidence': evidence,
                   'caveats': cav, 'figures': list(figures), 'geojson': geojson, 'params': params})


def _check_region(region):
    if region not in C.REGIONS:
        raise ValueError(f'region은 {C.REGIONS} 중 하나: {region}')


def _attach_detection(df: pd.DataFrame, region: str, night_thr=None, housing_thr=None) -> pd.DataFrame:
    det = _detect(region, C.NIGHT_THR[region] if night_thr is None else night_thr,
                  C.HOUSING_THR[region] if housing_thr is None else housing_thr, C.SENIOR_Q)
    df = df.drop(columns=['persistent_months', 'resident_any'], errors='ignore')
    df = df.merge(det, left_on='cell_id', right_index=True, how='left')
    df['resident_any'] = df.resident_any.eq(True)
    df['persistent_months'] = df.persistent_months.fillna(0).astype(int)
    return df


def _residential_mask(df: pd.DataFrame, residential_filter: bool = True) -> pd.Series:
    """거주 칸 = 팀 거주셀(야간 비중 기준 AND SGIS 주택 수 기준, 한 달이라도) AND GIS 주거·용도미상 건물 ≥ 1."""
    if not residential_filter:
        return df.resident_any
    return df.resident_any & df.res_status.isin(C.RESID_OK)


def _withdrawn(df: pd.DataFrame, persist_min: int) -> pd.Series:
    return df.persistent_months >= persist_min


def _types(df, far_social_m, far_health_m, withdrawn, senior_top=None):
    """senior_top: 어르신 비중 상위 칸 여부. 예방인프라형은 위축 없음 + 공백 + 어르신 상위 칸만."""
    far_s = df.dist_social > far_social_m
    far_h = df.dist_health > far_health_m
    gap = far_s | far_h
    if senior_top is None:
        senior_top = pd.Series(True, index=df.index)
    t = np.select([withdrawn & ~gap, withdrawn & gap, ~withdrawn & gap & senior_top],
                  ['연계형', '긴급방문형', '예방인프라형'], '관찰형')
    tag = np.select([far_s & far_h, far_s, far_h], ['둘다', '교류', '보건'], '')
    return pd.Series(t, index=df.index), pd.Series(tag, index=df.index)


def _universe(region, persist_min=C.PERSIST_MIN, residential_filter=True,
              far_social_m=C.FAR_SOCIAL_M, far_health_m=C.FAR_HEALTH_M, night_thr=None, housing_thr=None):
    df = _cells()
    df = _attach_detection(df[df.region == region], region, night_thr, housing_thr)
    df = df[_residential_mask(df, residential_filter)].copy()
    df['withdrawn'] = _withdrawn(df, persist_min)
    df['senior_top'] = df.senior_ratio >= df.senior_ratio.quantile(C.PREVENT_SENIOR_Q)
    df['type'], df['gap_tag'] = _types(df, far_social_m, far_health_m, df.withdrawn, df.senior_top)
    df['priority'] = df.type.map({k: v['priority'] for k, v in C.TYPES.items()})
    df['lon'], df['lat'] = TO_WGS.transform(df.x.to_numpy(), df.y.to_numpy())   # 칸 중심 (지도 API용)
    return df


# ---------------------------------------------------------------- 1. 후보 찾기
def find_candidates(region: str, persist_min: int = C.PERSIST_MIN, residential_filter: bool = True,
                    night_thr: float | None = None, housing_thr: float | None = None, render: bool = True) -> dict:
    """낮 활동이 지속적으로 낮은 고령 거주 칸. 사랑 로직을 엔진이 직접 계산 + GIS 주거건물 필터."""
    _check_region(region)
    all_c = _cells()
    reg_c = _attach_detection(all_c[all_c.region == region], region, night_thr, housing_thr)
    base = reg_c[reg_c.resident_any & _withdrawn(reg_c, persist_min)]      # 팀 기준 후보 (GIS 필터 전)
    u = _universe(region, persist_min, residential_filter, night_thr=night_thr, housing_thr=housing_thr)
    cand = u[u.withdrawn].sort_values(['persistent_months', 'senior_ratio'], ascending=False)
    dropped = base[~base.cell_id.isin(cand.cell_id)]
    by_emd = cand.groupby('emd_name').size().sort_values(ascending=False)
    cells = cand[['cell_id', 'emd_name', 'lat', 'lon', 'persistent_months', 'senior_ratio', 'day_share', 'res_status',
                  'senior65_share', 'hh_1p_share']].to_dict('records')
    figs, gj = [], None
    if render:
        name = f'candidates_{region}'
        figs = [R.map_cells(all_c[all_c.region == region], cand, 'persistent_months', region,
                            f'{region} 활동위축 후보 칸 ({len(cand)}개)', name, cmap='Reds')]
        gj = R.geojson(cand, ['cell_id', 'emd_name', 'persistent_months', 'res_status'], name)
    return _pack('find_candidates', region,
                 {'n_candidates': len(cand), 'by_emd': by_emd.to_dict(), 'cells': cells,
                  'n_dropped_nonresidential': len(dropped),
                  'dropped_status': dropped.res_status.value_counts().to_dict()},
                 [{'metric': 'n_candidates', 'value': len(cand)},
                  {'metric': 'team_candidates_before_filter', 'value': len(base)},
                  {'metric': 'n_dropped_nonresidential', 'value': len(dropped)},
                  {'metric': 'rule', 'value': f'거주(야간·SGIS 주택) & 고령 상위 25% & 낮활동 z<0 >= {persist_min}개월 & 주거건물 필터={residential_filter}'}],
                 {'persist_min': persist_min, 'residential_filter': residential_filter,
                  'night_thr': C.NIGHT_THR[region] if night_thr is None else night_thr,
                  'housing_thr': C.HOUSING_THR[region] if housing_thr is None else housing_thr},
                 figures=figs, geojson=gj)


# ---------------------------------------------------------------- 2. 거주 확인
def check_residential(cell_ids: list[str]) -> dict:
    df = _cells()
    d = df[df.cell_id.isin(cell_ids)][['cell_id', 'region', 'emd_name', 'res_status', 'n_bldg', 'n_res',
                                       'n_apt', 'n_na', 'n_semi', 'old_share', 'night_share']]
    missing = sorted(set(cell_ids) - set(d.cell_id))
    region = d.region.iloc[0] if len(d) and d.region.nunique() == 1 else None
    return _pack('check_residential', region,
                 {'cells': d.to_dict('records'), 'status_counts': d.res_status.value_counts().to_dict(),
                  'not_found': missing},
                 [{'metric': 'n_checked', 'value': len(d)}] +
                 [{'metric': f'status_{k}', 'value': v} for k, v in d.res_status.value_counts().items()],
                 {'rule': '주거=GIS 용도 01·02 건물 1채 이상, 용도미상=용도 결측만(아파트 가능), 비주거=그 외 건물만'},
                 caveats=['GIS 건물 용도 결측이 강남 21%·춘천 45%라 용도미상 칸은 현장 확인 필요'])


# ---------------------------------------------------------------- 3. 자원 조회
def lookup_resources(region: str, cell_id: str | None = None, lat: float | None = None, lon: float | None = None,
                     radius_m: int = 1000, top: int = 5) -> dict:
    """칸 또는 위경도(시민 모드) 기준 가까운 교류·보건 시설."""
    _check_region(region)
    if cell_id is not None:
        hit = _cells().loc[lambda d: (d.region == region) & (d.cell_id == cell_id)]
        if hit.empty:
            return _pack('lookup_resources', region, {'error': f'{region}에 없는 칸: {cell_id}'}, [],
                         {'cell_id': cell_id, 'radius_m': radius_m})
        x, y = hit.iloc[0].x, hit.iloc[0].y
    elif lat is not None and lon is not None:
        x, y = TO_UTMK.transform(lon, lat)
    else:
        raise ValueError('cell_id 또는 lat/lon 필요')
    f = _fac()
    f = f[(f.region == region) & f.group.isin(['social', 'health'])].copy()
    f['dist_m'] = np.hypot(f.x - x, f.y - y).round()          # m 정수 (result·evidence 같은 값)
    near = f.sort_values('dist_m')
    within = near[near.dist_m <= radius_m]
    nearest_by_kind = near.groupby('kind').head(1)[['kind', 'name', 'dist_m', 'addr', 'lat', 'lon']]
    lst = within.head(top * 3)[['fac_id', 'kind', 'group', 'name', 'addr', 'dist_m', 'lat', 'lon']]
    return _pack('lookup_resources', region,
                 {'nearest_by_kind': nearest_by_kind.to_dict('records'), 'within_radius': lst.to_dict('records'),
                  'count_within_radius': within.groupby('kind').size().to_dict()},
                 [{'metric': f'nearest_{r.kind}_m', 'value': int(r.dist_m)} for r in nearest_by_kind.itertuples()] +
                 [{'metric': f'count_{k}_within_{radius_m}m', 'value': v} for k, v in within.groupby('kind').size().items()],
                 {'cell_id': cell_id, 'lat': lat, 'lon': lon, 'radius_m': radius_m},
                 caveats=['보건진료소·보건지소 대부분은 위치·연락처만 확인됨. 세부 프로그램은 기관 확인 필요'])


# ---------------------------------------------------------------- 4. 유형 분류 (+ 원인·추천 표)
def _recommend(r) -> str:
    if r.type == '연계형':
        return f"가까운 {r.near_social_name}({r.dist_social:.0f}m) 프로그램 연결·동행"
    if r.type == '긴급방문형':
        parts = []
        if r.gap_tag in ('교류', '둘다'):
            parts.append(f'교류시설이 {r.dist_social:.0f}m로 멂 → 이동형 모임·안부 방문')
        if r.gap_tag in ('보건', '둘다'):
            parts.append(f'보건기관이 {r.dist_health/1000:.1f}km로 멂 → 방문 건강관리·이동형 상담')
        return ' / '.join(parts)
    if r.type == '예방인프라형':
        return f'현재 위축 신호 없음. 어르신 비중 높고 {r.gap_tag} 공백 → 이동형 서비스·공공시설 개방 검토'
    return '정기 모니터링'


def classify(region: str, far_social_m: int = C.FAR_SOCIAL_M, far_health_m: int = C.FAR_HEALTH_M,
             persist_min: int = C.PERSIST_MIN, residential_filter: bool = True, render: bool = True,
             table_top: int = 50) -> dict:
    """2x2 고립 유형 (활동위축 O/X x 자원 가까움/멂) + 공백 태그 + 원인·추천 표."""
    _check_region(region)
    u = _universe(region, persist_min, residential_filter, far_social_m, far_health_m)
    f = _fac()
    for grp, col in [('social', 'near_social_name'), ('health', 'near_health_name')]:
        ff = f[(f.region == region) & (f.group == grp)]
        _, idx = cKDTree(ff[['x', 'y']].to_numpy()).query(u[['x', 'y']].to_numpy())
        u[col] = ff.name.to_numpy()[idx]
    counts = u.type.value_counts().reindex(list(C.TYPES)).fillna(0).astype(int)
    tags = pd.crosstab(u.type, u.gap_tag)
    tags = tags.drop(columns=[''], errors='ignore')
    wd = u[u.withdrawn].copy()
    wd['recommendation'] = wd.apply(_recommend, axis=1)
    wd['cause'] = wd.apply(lambda r: f"낮 활동 저하 {int(r.persistent_months)}개월 / 60대+ 비중 {r.senior_ratio:.0%}"
                                     f" / 교류 {r.dist_social:.0f}m / 보건 {r.dist_health/1000:.1f}km", axis=1)
    table = (wd.sort_values(['priority', 'persistent_months'], ascending=[True, False])
               [['cell_id', 'emd_name', 'lat', 'lon', 'type', 'gap_tag', 'priority', 'cause', 'recommendation',
                 'near_social_name', 'dist_social', 'near_health_name', 'dist_health', 'res_status']]
               .head(table_top))
    by_emd = (u[u.type.isin(['긴급방문형', '연계형'])].groupby(['emd_name', 'type']).size()
                .unstack(fill_value=0))
    figs, gj = [], None
    if render:
        name = f'types_{region}'
        figs = [R.map_types(_cells()[_cells().region == region], u, region,
                            f'{region} 고립 유형 (교류>{far_social_m}m 또는 보건>{far_health_m/1000:g}km = 멂)', name)]
        gj = R.geojson(u, ['cell_id', 'emd_name', 'type', 'gap_tag', 'priority'], name)
    ev = [{'metric': f'n_{k}', 'value': v} for k, v in counts.items()]
    ev += [{'metric': f'{t}_gap_{g}', 'value': int(tags.loc[t, g])} for t in tags.index for g in tags.columns if tags.loc[t, g]]
    ev.append({'metric': 'n_universe_cells', 'value': len(u)})
    return _pack('classify', region,
                 {'type_counts': counts.to_dict(), 'gap_tags': {t: tags.loc[t].to_dict() for t in tags.index},
                  'n_universe_cells': len(u), 'by_emd_withdrawn': {e: r.to_dict() for e, r in by_emd.iterrows()},
                  'table': table.to_dict('records'), 'type_actions': C.TYPES,
                  'layers': {'위축 신호 층 (정책 우선 대상)': {t: int(counts[t]) for t in ('긴급방문형', '연계형')},
                             '자원 구조 층 (위축 신호 없음)': {t: int(counts[t]) for t in ('예방인프라형', '관찰형')}}},
                 ev,
                 {'far_social_m': far_social_m, 'far_health_m': far_health_m, 'persist_min': persist_min,
                  'residential_filter': residential_filter},
                 figures=figs, geojson=gj)


# ---------------------------------------------------------------- 5. 배치 시뮬레이션 (MCLP)
def _mclp(demand_xy, weight, site_xy, k, radius):
    """최대 커버링 입지: k곳을 골라 반경 안 수요 가중합 최대화 (scipy milp, HiGHS)."""
    tree = cKDTree(site_xy)
    cover = tree.query_ball_point(demand_xy, radius)
    useful = sorted({j for lst in cover for j in lst})
    if not useful:
        _mclp.last_status = {'status': 0, 'optimal': True, 'message': 'no coverable demand'}
        return [], np.zeros(len(demand_xy), bool)
    pos = {j: p for p, j in enumerate(useful)}
    nS, nD = len(useful), len(demand_xy)
    k = min(k, nS)                               # 수요를 덮는 거점보다 많이 고를 수 없음 (더 골라도 커버 불변)
    # 동점 깨기: 커버가 같으면 덮는 수요까지 평균 거리가 짧은 거점, 그래도 같으면 번호 작은 거점.
    # 벌점 총합이 최소 가중치보다 훨씬 작게 잡아 커버 최대화 결과는 바뀌지 않는다 (scipy 버전 간 결과 고정)
    weight = np.asarray(weight, float)
    sxy = np.asarray(site_xy)[useful]
    cov_by_site = [[] for _ in range(nS)]
    for i, lst in enumerate(cover):
        for j in lst:
            cov_by_site[pos[j]].append(i)
    mean_d = np.array([np.hypot(*(np.asarray(demand_xy)[ii] - sxy[p]).T).mean() / radius
                       for p, ii in enumerate(cov_by_site)])
    eps = weight.min() * 1e-3 / max(k, 1)
    tie = eps * (mean_d + np.arange(nS) / (10 * nS))
    c = np.concatenate([tie, -weight])
    rows, cols, vals = [], [], []
    for i, lst in enumerate(cover):              # y_i - sum_j a_ij x_j <= 0
        rows.append(i); cols.append(nS + i); vals.append(1.0)
        for j in lst:
            rows.append(i); cols.append(pos[j]); vals.append(-1.0)
    A = np.zeros((nD + 1, nS + nD))
    A[rows, cols] = vals
    A[nD, :nS] = 1.0                            # sum x_j = k
    lb = np.r_[np.full(nD, -np.inf), k]
    ub = np.r_[np.zeros(nD), k]
    res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=np.ones(nS + nD),
               bounds=Bounds(0, 1), options={'time_limit': 60})
    if res.x is None:
        raise RuntimeError(f'MCLP 풀이 실패: {res.message}')
    x = res.x[:nS] > 0.5
    chosen = [useful[p] for p in np.flatnonzero(x)]
    covered = res.x[nS:] > 0.5
    # status 0 = 최적해 증명. 1 = 시간 초과(부분해) → optimal False 로 표시
    _mclp.last_status = {'status': int(res.status), 'optimal': res.status == 0, 'message': str(res.message),
                         'mip_gap': getattr(res, 'mip_gap', None)}
    return chosen, covered


def simulate_placement(region: str, k: int = C.SIM_K, radius_m: int = C.SIM_RADIUS_M,
                       target_types: tuple = ('긴급방문형',), k_max: int = 5, render: bool = True) -> dict:
    """이동형 거점 k곳을 거주 칸 중심 중 어디에 두면 대상 칸의 60대+ 유동을 가장 많이 덮는가."""
    _check_region(region)
    u = _universe(region)
    dem = u[u.type.isin(target_types)].copy()
    if dem.empty:
        return _pack('simulate_placement', region, {'message': '대상 칸 없음'}, [], {'k': k})
    if not isinstance(k, (int, np.integer)) or isinstance(k, bool) or k < 1:
        return _pack('simulate_placement', region, {'error': f'k는 1 이상 정수: {k}'}, [], {'k': k})
    w = dem.senior_mean.fillna(0).clip(lower=0.01).to_numpy()
    sites = u[['cell_id', 'emd_name', 'x', 'y', 'lat', 'lon']].reset_index(drop=True)
    cav = []
    if k > len(sites):                                   # 후보지보다 많이 고를 수 없음 (sum x = k 제약)
        cav.append(f'k={k}가 후보지 수({len(sites)})보다 커서 {len(sites)}로 줄였다.')
        k = len(sites)
    k_max = max(1, min(int(k_max), len(sites)))
    curve = []
    best = None
    for kk in range(1, max(k, k_max) + 1):
        chosen, covered = _mclp(dem[['x', 'y']].to_numpy(), w, sites[['x', 'y']].to_numpy(), kk, radius_m)
        curve.append({'k': kk, 'covered_cells': int(covered.sum()), 'covered_cells_share': covered.mean(),
                      'covered_senior_share': w[covered].sum() / w.sum(), 'optimal': _mclp.last_status['optimal']})
        if kk == k:
            best = (chosen, covered)
    chosen, covered = best
    ch = sites.iloc[chosen].copy()
    dem['covered'] = covered
    ch['covers'] = [int((np.hypot(dem.x - r.x, dem.y - r.y) <= radius_m).sum()) for r in ch.itertuples()]
    after = dem.type.where(~dem.covered, '연계형(이동형 도달)')
    figs, gj = [], None
    if render:
        name = f'sim_{region}_k{k}_r{radius_m}'
        figs = [R.map_sim(_cells()[_cells().region == region], dem, ch, radius_m, region,
                          f'{region} 이동형 거점 {k}곳 (반경 {radius_m}m) 커버 {covered.sum()}/{len(dem)}칸', name),
                R.curve(curve, region, f'{region} 거점 수별 커버 비율 (반경 {radius_m}m)', f'curve_{region}_r{radius_m}')]
        gj = R.geojson(dem.assign(covered=dem.covered.astype(int)), ['cell_id', 'emd_name', 'type', 'covered'], name)
    return _pack('simulate_placement', region,
                 {'chosen_sites': ch.to_dict('records'), 'n_target_cells': len(dem),
                  'covered_cells': int(covered.sum()), 'covered_senior_share': curve[k - 1]['covered_senior_share'],
                  'k_curve': curve, 'type_after': after.value_counts().to_dict()},
                 [{'metric': 'n_target_cells', 'value': len(dem)},
                  {'metric': f'covered_cells_k{k}', 'value': int(covered.sum())},
                  {'metric': f'covered_senior_share_k{k}', 'value': curve[k - 1]['covered_senior_share']}] +
                 [{'metric': f'covered_senior_share_k{c["k"]}', 'value': c['covered_senior_share']} for c in curve],
                 {'k': k, 'radius_m': radius_m, 'target_types': list(target_types), 'weight': '60대+ 일평균 유동',
                  'sites': '거주 칸 중심', 'solver': 'scipy.milp (HiGHS)',
                  'all_optimal': all(c['optimal'] for c in curve)},
                 caveats=['수요 가중치는 60대 이상 유동인구(체류)이며 거주 고령 인구가 아니다.',
                          '커버는 반경 안 도달 가능성만 뜻하며 고립 감소 효과를 뜻하지 않는다.'] + cav,
                 figures=figs, geojson=gj)


# ---------------------------------------------------------------- 6. 강건성 점검
def robustness(region: str, persist_list=(4, 5, 6), social_list=(300, 500, 1000),
               health_list=(2000, 3000, 5000), residential_list=(True, False), night_scale=(0.7, 1.0, 1.3),
               housing_list=None) -> dict:
    """기준값을 바꿔 다시 계산 → 유형 수와 기본값 대비 긴급방문형 판정의 겹침.
    urgent_retained  = 기본 긴급 중 남은 비율 (놓침 확인)
    urgent_precision = 새 긴급 중 기본에도 있던 비율 (새로 끼어든 칸 확인)
    urgent_jaccard   = 두 집합 겹침 (둘 다 반영한 요약)"""
    _check_region(region)
    if housing_list is None:
        housing_list = {'강남': (100, 200, 400), '춘천': (0, 30, 100, 200)}[region]   # 팀 민감도 표(srh_08)와 같은 춘천 값
    # 기본값은 항상 포함 (기본 행·하나씩 바꾸기 비교의 기준)
    add = lambda lst, v: tuple(sorted(set(lst) | {v}))
    persist_list, social_list = add(persist_list, C.PERSIST_MIN), add(social_list, C.FAR_SOCIAL_M)
    health_list, residential_list = add(health_list, C.FAR_HEALTH_M), add(residential_list, True)
    night_scale, housing_list = add(night_scale, 1.0), add(housing_list, C.HOUSING_THR[region])
    base = _universe(region)
    base_urgent = set(base.cell_id[base.type == '긴급방문형'])
    base_wd = set(base.cell_id[base.withdrawn])
    rows = []
    for p in persist_list:
        for s in social_list:
            for h in health_list:
                for rf in residential_list:
                    for ns in night_scale:
                      for ht in housing_list:
                        if ns != 1.0 and ht != C.HOUSING_THR[region]:
                            continue                      # 야간·주택은 하나씩만 (조합 폭발 방지)
                        u = _universe(region, p, rf, s, h, C.NIGHT_THR[region] * ns, ht)
                        urg = set(u.cell_id[u.type == '긴급방문형'])
                        inter = len(urg & base_urgent)
                        union = len(urg | base_urgent)
                        rows.append({'persist_min': p, 'far_social_m': s, 'far_health_m': h, 'residential_filter': rf,
                                     'night_scale': ns, 'housing_thr': ht,
                                     **u.type.value_counts().reindex(list(C.TYPES)).fillna(0).astype(int).to_dict(),
                                     'urgent_retained': inter / len(base_urgent) if base_urgent else np.nan,
                                     'urgent_precision': inter / len(urg) if urg else np.nan,
                                     'urgent_jaccard': inter / union if union else np.nan,
                                     'withdrawn_retained': len(set(u.cell_id[u.withdrawn]) & base_wd) / len(base_wd) if base_wd else np.nan})
    t = pd.DataFrame(rows)
    is_default = ((t.persist_min == C.PERSIST_MIN) & (t.far_social_m == C.FAR_SOCIAL_M) &
                  (t.far_health_m == C.FAR_HEALTH_M) & t.residential_filter & (t.night_scale == 1.0) &
                  (t.housing_thr == C.HOUSING_THR[region]))
    rng = {k: [int(t[k].min()), int(t[k].max())] for k in C.TYPES}
    # 하나씩만 바꾸기 (나머지는 기본값)
    dflt = {'persist_min': C.PERSIST_MIN, 'far_social_m': C.FAR_SOCIAL_M, 'far_health_m': C.FAR_HEALTH_M,
            'residential_filter': True, 'night_scale': 1.0, 'housing_thr': C.HOUSING_THR[region]}
    oat = []
    for par in dflt:
        m = pd.Series(True, index=t.index)
        for other, v in dflt.items():
            if other != par:
                m &= t[other] == v
        for r in t[m].itertuples():
            oat.append({'param': par, 'value': getattr(r, par), '연계형': r.연계형, '긴급방문형': r.긴급방문형,
                        '예방인프라형': r.예방인프라형, '관찰형': r.관찰형, 'urgent_retained': r.urgent_retained,
                        'urgent_precision': r.urgent_precision, 'urgent_jaccard': r.urgent_jaccard,
                        'is_default': getattr(r, par) == dflt[par]})
    return _pack('robustness', region,
                 {'one_at_a_time': oat, 'type_range_all_combos': rng,
                  'urgent_jaccard_median_all_combos': t.urgent_jaccard.median(),
                  'default_row': t[is_default].iloc[0].to_dict(), 'grid': t.to_dict('records')},
                 [{'metric': f'{k}_min', 'value': v[0]} for k, v in rng.items()] +
                 [{'metric': f'{k}_max', 'value': v[1]} for k, v in rng.items()] +
                 [{'metric': 'urgent_jaccard_median_all_combos', 'value': t.urgent_jaccard.median()}] +
                 [{'metric': f"oat_{o['param']}_{o['value']}_긴급방문형", 'value': o['긴급방문형']} for o in oat],
                 {'persist_list': persist_list, 'social_list': social_list, 'health_list': health_list,
                  'residential_list': residential_list, 'night_scale': night_scale, 'housing_list': housing_list},
                 caveats=['후보는 기준값마다 엔진이 다시 계산한다 (사랑 로직 이식, 군집은 고정).'])


# ---------------------------------------------------------------- 7. 시설 변화 가정 (2차)
def facility_change(region: str, remove_ids: list[str] = (), add_points: list[dict] = (), render: bool = True) -> dict:
    """시설을 빼거나(fac_id) 더했을 때(lat/lon/kind) 유형이 어떻게 바뀌나."""
    _check_region(region)
    before = _universe(region)
    f = _fac()
    f = f[(f.region == region) & f.group.isin(['social', 'health']) & ~f.fac_id.isin(remove_ids)].copy()
    fr = _fac()[(_fac().region == region) & _fac().group.isin(['social', 'health'])]
    removed = fr[fr.fac_id.isin(remove_ids)][['fac_id', 'kind', 'name']]
    not_found = sorted(set(remove_ids) - set(removed.fac_id))     # 다른 지역·없는 ID는 반영 안 됨
    for p in add_points:
        x, y = TO_UTMK.transform(p['lon'], p['lat'])
        grp = 'health' if p.get('kind') == '보건' else 'social'
        f = pd.concat([f, pd.DataFrame([{'kind': p.get('kind', '경로당'), 'group': grp, 'x': x, 'y': y,
                                         'name': p.get('name', '신규 시설'), 'fac_id': 'NEW'}])])
    after = before.copy()
    for grp, col in [('social', 'dist_social'), ('health', 'dist_health')]:
        ff = f[f.group == grp]
        d, _ = cKDTree(ff[['x', 'y']].to_numpy()).query(after[['x', 'y']].to_numpy())
        after[col] = d
    after['type'], after['gap_tag'] = _types(after, C.FAR_SOCIAL_M, C.FAR_HEALTH_M, after.withdrawn, after.senior_top)
    trans = pd.crosstab(before.type, after.type)
    changed = after[before.type != after.type][['cell_id', 'emd_name']].assign(
        before=before.type[before.type != after.type], after=after.type[before.type != after.type])
    figs = []
    if render and len(changed):
        figs = [R.map_change(_cells()[_cells().region == region], changed, region,
                             f'{region} 시설 변화 후 유형이 바뀐 칸 ({len(changed)}개)', f'change_{region}')]
    return _pack('facility_change', region,
                 {'removed': removed.to_dict('records'), 'not_found': not_found, 'added': list(add_points),
                  'n_changed_cells': len(changed), 'transitions': {i: r[r > 0].to_dict() for i, r in trans.iterrows()},
                  'changed_cells': changed.to_dict('records')},
                 [{'metric': 'n_changed_cells', 'value': len(changed)}] +
                 [{'metric': f'{b}->{a}', 'value': int(trans.loc[b, a])} for b in trans.index for a in trans.columns
                  if b != a and trans.loc[b, a] > 0],
                 {'remove_ids': list(remove_ids), 'add_points': list(add_points)}, figures=figs)


# ---------------------------------------------------------------- 8. 지역 맥락 (2차)
def region_context(region: str) -> dict:
    _check_region(region)
    T = C.DATA / 'team'
    age_local = pd.read_parquet(T / '21_연령별_로컬_결제_비율.parquet').set_index('AGE_CCD')[region]
    tb = pd.read_parquet(T / '15_시간대_6시간__건수_비중.parquet').set_index('TIME_GB')
    time60 = tb[f'{region} 60대+']
    local = {'강남': 39.9, '춘천': 82.2}[region]          # 03 EDA·팀 표 20 (데이터2, 개인)
    pop = {'강남': {'pop': 556000, 'p65': 0.171, 'p85': 0.015, 'solo65': 15540, 'solo_mid_male': 12633,
                   'solo_top_age': '25~34세'},
           '춘천': {'pop': 285000, 'p65': 0.226, 'p85': 0.029, 'solo65': 15291, 'solo_mid_male': 9136,
                   'solo_top_age': '65세 이상'}}[region]        # 07 EDA (KOSIS 2025)
    u = _universe(region)
    return _pack('region_context', region,
                 {'local_payment_pct': local, 'local_payment_by_age_pct': age_local.to_dict(),
                  'senior60_card_time_pct': time60.to_dict(), 'population': pop,
                  'lens': '활동 위축형(고령·통신)' if region == '춘천' else '관계 부재형 비중 큼(청년·중장년 1인가구·카드)',
                  'type_counts': u.type.value_counts().to_dict()},
                 [{'metric': 'local_payment_pct', 'value': local},
                  {'metric': 'pop_65plus_share', 'value': pop['p65']},
                  {'metric': 'solo_65plus_households', 'value': pop['solo65']}] +
                 [{'metric': f'senior60_card_time_{k}', 'value': v} for k, v in time60.items()],
                 {}, caveats=['카드·인구는 시군구 단위라 칸에 내리지 않고 해석 맥락으로만 쓴다.'])


TOOLS = {f.__name__: f for f in [find_candidates, check_residential, lookup_resources, classify,
                                 simulate_placement, robustness, facility_change, region_context]}


def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
