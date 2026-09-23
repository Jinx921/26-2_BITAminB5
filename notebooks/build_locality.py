"""생활 반경 가중 접근성 (2-A) — 카드 로컬 결제 비율을 격자 연령 구성에 결합.

  locality(격자)    = Σ_연령 [격자 연령비중 × 로컬결제비율(지역, 연령)]
                      그 격자에 있는 사람들이 평균적으로 얼마나 지역에 묶여 있는가
  felt_access(격자) = 자원 접근성 × locality
                      같은 자원이라도 지역 의존도가 높은 집단에게 더 큰 의미를 갖는다

카드 연령(10~90대)과 통신 연령(10대~60대이상)의 구간이 달라 60대 이상은 건수 가중 평균한다.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import config as C
from loaders import load_sk, load_shinhan

pd.set_option('display.width', 200)
BANDS = ['10대', '20대', '30대', '40대', '50대', '60대+']
SK_COLS = {b: [f'{p}_FLOW_POP_CNT_{g}' for p in ('MAN', 'WMAN')]
           for b, g in zip(BANDS, ['10G', '20G', '30G', '40G', '50G', '60GU'])}


def local_ratio_by_band() -> pd.DataFrame:
    """카드 데이터2 → 지역 × 연령대 로컬 결제 비율(0~1)."""
    d = load_shinhan('cln')
    d['AGE_CCD'] = d.AGE_CCD.str.replace(' ', '', regex=False)
    d['region'] = d.MCT_SGG_CD.map({'서울 강남구': '강남', '강원 춘천시': '춘천'})
    d['local'] = d.region.map({'강남': '서울', '춘천': '강원'}) == d.CLN_SGG_CD
    # 60대 이상은 하나로 묶는다 (통신 데이터의 60GU 와 맞추기 위해)
    d['band'] = np.where(d.AGE_CCD.isin(['60대', '70대', '80대', '90대']), '60대+', d.AGE_CCD)
    g = d[d.band.isin(BANDS)].groupby(['region', 'band'])
    r = (g.apply(lambda x: x[x.local].USE_CNT.sum() / x.USE_CNT.sum(), include_groups=False)
           .unstack('band')[BANDS])
    return r


def main():
    print("[1] 카드 데이터2 — 지역×연령 로컬 결제 비율")
    lr = local_ratio_by_band()
    print((lr * 100).round(1).to_string())

    print("\n[2] 격자 연령 구성 (SK 유동인구 6개월 합계)")
    a = load_sk('flow_age_pop')
    a['cell_id'] = a.X_COORD.astype('int64').astype(str) + '_' + a.Y_COORD.astype('int64').astype(str)
    for b, cols in SK_COLS.items():
        a[b] = a[cols].sum(axis=1)
    comp = a.groupby('cell_id')[BANDS].sum()
    comp = comp.div(comp.sum(axis=1), axis=0)          # 연령 비중
    print(f"  격자 {len(comp):,}개 / 연령 비중 합계 검증: {comp.sum(axis=1).round(6).nunique()} 종류")

    print("\n[3] locality 계산")
    g = pd.read_parquet('preprocessed/grid_access_senior.parquet').merge(
        comp.reset_index(), on='cell_id', how='left')
    g['locality'] = 0.0
    for reg in ['강남', '춘천']:
        m = g.region == reg
        g.loc[m, 'locality'] = sum(g.loc[m, b] * lr.loc[reg, b] for b in BANDS)
    g['felt_access'] = (g.opp_n300 * g.locality).round(3)
    g['locality'] = g.locality.round(4)
    print(g.groupby('region')[['locality', 'felt_access']]
           .describe(percentiles=[.1, .5, .9]).T.round(3).to_string())

    print("\n[4] 고령 비율의 단순 재탕인지 검증")
    for reg, s in g.groupby('region'):
        rho, _ = spearmanr(s.senior_ratio, s.locality)
        rho2, _ = spearmanr(s.opp_n300, s.felt_access)
        print(f"  [{reg}] locality × 고령비율 rho={rho:+.3f}   "
              f"felt_access × opp_n300 rho={rho2:+.3f}")

    print("\n[5] 순위가 얼마나 바뀌는가 — opp_n300 기준 vs felt_access 기준 하위 25%")
    for reg, s in g.groupby('region'):
        a1 = set(s.nsmallest(int(len(s) * .25), 'opp_n300').cell_id)
        a2 = set(s.nsmallest(int(len(s) * .25), 'felt_access').cell_id)
        jac = len(a1 & a2) / len(a1 | a2)
        print(f"  [{reg}] 겹치는 격자 {len(a1 & a2):,} / 합집합 {len(a1 | a2):,}  (Jaccard {jac:.3f})"
              f"  → {len(a2 - a1):,}개 격자가 새로 편입")

    out = pathlib.Path('preprocessed/grid_locality.parquet')
    g.to_parquet(out, index=False)
    print(f"\n저장 → {out}  ({len(g):,}행 × {g.shape[1]}열)")


if __name__ == '__main__':
    main()
