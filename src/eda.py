"""EDA 계산 로직. 각 함수는 (제목, DataFrame, 설명) 목록을 반환한다."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from loaders import load_sk, load_shinhan

AGE_M = [f'MAN_FLOW_POP_CNT_{g}' for g in ['10G', '20G', '30G', '40G', '50G', '60GU']]
AGE_W = [f'WMAN_FLOW_POP_CNT_{g}' for g in ['10G', '20G', '30G', '40G', '50G', '60GU']]
AGES = ['10대', '20대', '30대', '40대', '50대', '60대+']
TMST = [f'TMST_{h:02d}' for h in range(24)]
WKDY = ['MON', 'TUS', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
WCOL = [f'FLOW_POP_CNT_{d}' for d in WKDY]
KOR_DOW = ['월', '화', '수', '목', '금', '토', '일']
OLD = ['60대', '70대', '80대', '90대']


def _tag(df):
    df = df.copy()
    df['region'] = np.where(df.X_COORD < 1_000_000, '강남', '춘천')
    df['cell'] = df.X_COORD.astype('int64').astype(str) + '_' + df.Y_COORD.astype('int64').astype(str)
    return df


def _card():
    d = load_shinhan('mct')
    d['AGE_CCD'] = d.AGE_CCD.str.replace(' ', '', regex=False)
    d['date'] = pd.to_datetime(d.TA_YMD, format='%Y%m%d')
    d['month'] = d.date.dt.to_period('M').astype(str)
    d['region'] = d.MCT_SGG_CD.map({'서울 강남구': '강남', '강원 춘천시': '춘천'})
    return d


def sk_tables() -> list[tuple[str, pd.DataFrame, str]]:
    age, tim, wkd = _tag(load_sk('flow_age_pop')), _tag(load_sk('flow_time_pop')), _tag(load_sk('flow_wkdy_pop'))
    age['total'] = age[AGE_M + AGE_W].sum(axis=1)
    out = []

    piv = age.pivot_table(index=['region', 'cell'], columns='STD_YM', values='total')
    nobs = piv.notna().sum(axis=1)
    t = pd.crosstab(nobs.index.get_level_values('region'), nobs)
    t.columns = [f'{c}개월' for c in t.columns]
    out.append(('패널 균형: 관측 월 수별 격자 수', t.reset_index().rename(columns={'row_0': 'region'}),
                '결측이 소규모 격자에 몰려 있어 6개월 완전관측 격자만 써도 인구의 99%가 남는다.'))

    d = pd.DataFrame({'mean': piv[nobs == 6].mean(axis=1),
                      'cv': piv[nobs == 6].std(axis=1) / piv[nobs == 6].mean(axis=1)}).reset_index()
    d = d[d['mean'] > 0]
    lab = ['~1', '1-5', '5-10', '10-30', '30-100', '100-300', '300-1k', '1k+']
    d['규모구간'] = pd.cut(d['mean'], [0, 1, 5, 10, 30, 100, 300, 1000, np.inf], labels=lab)
    t = (d.groupby(['region', '규모구간'], observed=True)
           .agg(격자수=('cv', 'size'), CV중앙값=('cv', 'median')).round(3).reset_index())
    out.append(('규모 구간별 변동계수(CV)', t,
                'CV가 규모에 단조 반비례한다. 작은 격자의 큰 변동은 고립 신호가 아니라 표본 노이즈다.'))

    rows = []
    totpop = age.groupby('region').total.sum() / 6
    for thr in [0, 1, 5, 10, 30, 50, 100]:
        s = d[d['mean'] >= thr].groupby('region').agg(n=('cv', 'size'), pop=('mean', 'sum'))
        r = {'임계(일평균)': f'{thr}명 이상'}
        for reg in ['강남', '춘천']:
            r[f'{reg} 격자수'] = int(s.loc[reg, 'n'])
            r[f'{reg} 인구커버'] = round(s.loc[reg, 'pop'] / totpop[reg] * 100, 1)
        rows.append(r)
    out.append(('규모 임계별 유효 격자 커버리지', pd.DataFrame(rows),
                '일평균 30명 기준이면 강남 10,865 / 춘천 8,364로 양쪽 표본 규모가 비슷해진다.'))

    t = age.groupby(['region', 'STD_YM']).total.sum().unstack(0).round(0)
    t['춘천/강남'] = (t['춘천'] / t['강남']).round(3)
    out.append(('월별 총 유동인구 (일평균 합계)', t.reset_index(), '6개월간 두 지역 모두 규모가 안정적이다.'))

    t = age.groupby('region').total.describe(percentiles=[.1, .25, .5, .75, .9, .99]).round(1)
    out.append(('격자당 일평균 유동인구 분포', t.reset_index(),
                '춘천 격자의 중앙값은 1.2명. 격자 대부분이 사실상 비어 있다.'))

    comp = []
    for r, g in age.groupby('region'):
        m, w = g[AGE_M].sum(), g[AGE_W].sum()
        tot = m.sum() + w.sum()
        comp.append(pd.Series(list(m / tot * 100) + list(w / tot * 100),
                    index=[f'남 {a}' for a in AGES] + [f'여 {a}' for a in AGES], name=r))
    t = pd.concat(comp, axis=1).round(2).rename_axis('연령·성별').reset_index()
    out.append(('연령·성별 구성비 (%)', t, '춘천은 60대+가 24.7%, 강남은 18.9%.'))

    g60 = ((age[['MAN_FLOW_POP_CNT_60GU', 'WMAN_FLOW_POP_CNT_60GU']].sum(axis=1) / age.total * 100)
           .groupby([age.region, age.cell]).mean())
    t = g60.groupby(level=0).describe(percentiles=[.05, .25, .5, .75, .95]).round(1)
    out.append(('격자별 60대+ 비율 분포 (%)', t.reset_index(),
                '춘천의 격자 간 편차가 강남의 3.5배. 사회참여 격차(A안) 변별력이 가장 큰 곳.'))

    tp = tim.groupby('region')[TMST].sum()
    tp = ((tp.T / tp.sum(axis=1)).T * 100).round(2)
    tp.columns = [c[-2:] + '시' for c in tp.columns]
    out.append(('시간대 프로파일 (%)', tp.reset_index(),
                '두 지역 프로파일이 거의 같다. 차이는 야간(00~05시) 비중뿐 — 강남 5.0% vs 춘천 2.8%.'))

    wp = wkd.groupby('region')[WCOL].sum()
    wp = ((wp.T / wp.sum(axis=1)).T * 100).round(2)
    wp.columns = KOR_DOW
    out.append(('요일 패턴 (%)', wp.reset_index(),
                '강남은 일요일에 급감(10.2%)하는 업무지구, 춘천은 평탄한 생활권(13.0%).'))
    return out


def card_tables() -> list[tuple[str, pd.DataFrame, str]]:
    d = _card()
    p = d[d.SEX_CCD != '법인'].copy()
    out = []

    t = p.groupby('region').agg(결제액=('TS_AT', 'sum'), 건수=('USE_CNT', 'sum'))
    t['객단가'] = (t.결제액 / t.건수).round(0)
    법인 = d[d.SEX_CCD == '법인']
    t['법인비중%'] = [round(법인[법인.region == r].TS_AT.sum() /
                          d[d.region == r].TS_AT.sum() * 100, 1) for r in t.index]
    out.append(('지역별 카드 규모 (개인카드)', t.reset_index(),
                '강남 결제액이 춘천의 13.6배. 객단가도 33% 높다.'))

    tot = p.groupby('region').USE_CNT.sum()
    ry = (p.groupby(['region', 'MCT_RY_CD']).USE_CNT.sum().unstack(0).fillna(0) / tot * 100)
    ry['차이'] = (ry['춘천'] - ry['강남']).round(2)
    t = pd.concat([ry.nlargest(10, '차이'), ry.nsmallest(10, '차이')]).round(2).reset_index()
    out.append(('업종별 건수 비중 차이 (춘천-강남, %p)', t,
                '춘천은 편의점·한식·주유소, 강남은 컴퓨터/SW·쇼핑몰. 생활권 구조가 다르다.'))

    for reg in ['강남', '춘천']:
        s = p[p.region == reg]
        t = s.groupby('MCT_RY_CD').agg(건수=('USE_CNT', 'sum'), 결제액=('TS_AT', 'sum'))
        t['건수%'] = (t.건수 / t.건수.sum() * 100).round(2)
        t['결제액%'] = (t.결제액 / t.결제액.sum() * 100).round(2)
        t['객단가'] = (t.결제액 / t.건수).round(0)
        note = ('결제액의 30.1%가 세금공과금이다. 강남 카드 데이터는 생활 소비가 아니라 '
                '본사·기관 납부가 대량 섞여 있어 필터링 없이 쓰면 안 된다.') if reg == '강남' else \
               '할인점·한식·주유소·편의점이 상위. 전형적인 생활 소비 구조다.'
        out.append((f'[{reg}] 결제액 상위 12 업종', t.nlargest(12, '결제액')[['건수%', '결제액%', '객단가']].reset_index(), note))

    ap = p.pivot_table(index='AGE_CCD', columns='region', values=['TS_AT', 'USE_CNT'], aggfunc='sum')
    t = (ap['TS_AT'] / ap['USE_CNT']).round(0)
    out.append(('연령별 객단가 (원)', t.reset_index(),
                '60대 객단가가 강남 106,168원 vs 춘천 51,628원으로 2배 차이.'))

    tg = p.pivot_table(index='TIME_GB', columns='region', values='USE_CNT', aggfunc='sum')
    old = p[p.AGE_CCD.isin(OLD)]
    tg2 = old.pivot_table(index='TIME_GB', columns='region', values='USE_CNT', aggfunc='sum')
    t = pd.concat([(tg / tg.sum() * 100).round(2).add_suffix(' 전체'),
                   (tg2 / tg2.sum() * 100).round(2).add_suffix(' 60대+')], axis=1)
    out.append(('시간대(6시간) 건수 비중 (%)', t.reset_index(),
                '고령층은 야간 결제가 거의 없고 낮 시간(12~17시)에 집중된다.'))

    daily = p.pivot_table(index='date', columns='region', values='USE_CNT', aggfunc='sum')
    dow = daily.groupby(daily.index.dayofweek).mean()
    t = (dow / dow.iloc[:5].mean() * 100).round(1)
    t.index = KOR_DOW
    out.append(('요일별 결제건수 지수 (평일 평균=100)', t.rename_axis('요일').reset_index(),
                '춘천은 토요일에 소비가 늘고(114.9) 강남은 일요일에 준다(80.9).'))

    def ent(s):
        q = s / s.sum(); q = q[q > 0]
        return float(-(q * np.log(q)).sum())
    H = (p.groupby(['region', 'AGE_CCD', 'month', 'MCT_RY_CD']).USE_CNT.sum()
           .groupby(level=[0, 1, 2]).apply(ent).unstack('month'))
    H['추세(12월-7월)'] = (H['2025-12'] - H['2025-07']).round(3)
    out.append(('소비 다양성 Shannon entropy (연령×지역×월)', H.round(3).reset_index(),
                '춘천 30~70대는 오히려 다양성이 증가한다. 축소가 실제로 관측되는 집단은 '
                '춘천 10대·80대·90대와 강남 90대·50대뿐. 최대치는 log(91)=4.511.'))

    d['old'] = d.AGE_CCD.isin(OLD)
    g = d.groupby(['region', 'MCT_RY_CD']).apply(
        lambda x: pd.Series({'60대+비중%': x[x.old].USE_CNT.sum() / x.USE_CNT.sum() * 100,
                             '건수': x.USE_CNT.sum()}), include_groups=False)
    for reg in ['강남', '춘천']:
        s = g.loc[reg]
        s = s[s.건수 > s.건수.sum() * 0.002]
        note = ('춘천 LPG가스의 57.1%가 60대+. 도시가스 미보급 지역의 고령 가구라는 뜻으로, '
                '주거 취약성의 직접적인 프록시가 된다.') if reg == '춘천' else \
               '종합병원·약국·통신요금이 상위. 의료와 고정비 중심이다.'
        out.append((f'[{reg}] 60대+ 비중 상위 10 업종', s.nlargest(10, '60대+비중%').round(2).reset_index(), note))
    return out


def card2_tables() -> list[tuple[str, pd.DataFrame, str]]:
    """데이터2(2026-09 재배포본). 일별 × 가맹점지역 × 업종 × 고객거주지 × 성 × 연령."""
    d = load_shinhan('cln')
    d['AGE_CCD'] = d.AGE_CCD.str.replace(' ', '', regex=False)
    d['date'] = pd.to_datetime(d.TA_YMD, format='%Y%m%d')
    d['month'] = d.date.dt.to_period('M').astype(str)
    d['region'] = d.MCT_SGG_CD.map({'서울 강남구': '강남', '강원 춘천시': '춘천'})
    home = {'강남': '서울', '춘천': '강원'}
    d['local'] = d.region.map(home) == d.CLN_SGG_CD
    out = []

    def local_rate(g):
        return g[g.local].USE_CNT.sum() / g.USE_CNT.sum() * 100

    t = d.pivot_table(index='CLN_SGG_CD', columns='region', values='USE_CNT', aggfunc='sum')
    t = (t / t.sum() * 100).round(2).sort_values('춘천', ascending=False)
    out.append(('가맹점 지역별 고객 거주지 분포 (%)', t.reset_index(),
                '춘천 가맹점 결제의 82.1%가 강원 거주자인 반면, 강남은 39.9%만 서울 거주자다. '
                '춘천은 닫힌 생활권, 강남은 외지 유입이 60%인 상업 중심지다.'))

    t = (d.groupby(['region', 'AGE_CCD'], observed=True).apply(local_rate, include_groups=False)
           .unstack('region').round(2))
    out.append(('연령별 로컬 결제 비율 (%)', t.reset_index(),
                '거주지와 가맹점 지역이 일치하는 결제의 비중. 고령일수록 생활 반경이 좁아지는지 본다.'))

    t = (d.groupby(['region', 'month'], observed=True).apply(local_rate, include_groups=False)
           .unstack('region').round(2))
    out.append(('월별 로컬 결제 비율 (%)', t.reset_index(),
                '6개월간 생활 반경이 좁아지는 추세가 있는지 확인한다.'))

    for reg in ['춘천', '강남']:
        s_ = d[d.region == reg]
        g = s_.groupby('MCT_RY_CD', observed=True).apply(
            lambda x: pd.Series({'로컬비율%': local_rate(x), '건수': x.USE_CNT.sum()}),
            include_groups=False)
        g = g[g.건수 > g.건수.sum() * 0.003]
        t = pd.concat([g.nlargest(8, '로컬비율%'), g.nsmallest(8, '로컬비율%')]).round(2)
        note = ('로컬 비율이 높은 업종이 생활 밀착 업종이다. 낮은 쪽은 관광·통과 수요다.'
                if reg == '춘천' else
                '강남은 대부분의 업종에서 외지인 비중이 높다. 로컬 비율이 높은 업종이 주거 생활권 신호다.')
        out.append((f'[{reg}] 업종별 로컬 결제 비율 (%, 상·하위 8)', t.reset_index(), note))

    t = d.pivot_table(index='AGE_CCD', columns='region', values='USE_CNT', aggfunc='sum')
    t = (t / t.sum() * 100).round(2)
    out.append(('연령별 건수 비중 (%, 법인 제외)', t.reset_index(),
                '데이터2는 법인카드가 제외돼 있어 개인 소비 구조를 그대로 보여준다.'))

    dow = d.pivot_table(index=d.date.dt.dayofweek, columns='region', values='USE_CNT', aggfunc='sum')
    t = (dow / dow.iloc[:5].mean() * 100).round(1)
    t.index = KOR_DOW
    out.append(('요일별 결제건수 지수 (평일 평균=100, 데이터2)', t.rename_axis('요일').reset_index(),
                '데이터1과 같은 방향이다. 춘천은 주말에 늘고 강남은 준다.'))

    out.append(('데이터2 재배포 전후 비교', pd.DataFrame([
        {'항목': '컬럼 수', '구(결함본)': '5', '신(재배포본)': '8'},
        {'항목': '누락 컬럼', '구(결함본)': 'TA_YMD, MCT_SGG_CD, MCT_RY_CD', '신(재배포본)': '없음'},
        {'항목': '행 수', '구(결함본)': '1,806,800', '신(재배포본)': '1,806,800'},
        {'항목': '고유 키 조합', '구(결함본)': '305', '신(재배포본)': f'{d.groupby(["TA_YMD","MCT_SGG_CD","MCT_RY_CD","CLN_SGG_CD","SEX_CCD","AGE_CCD"]).ngroups:,}'},
        {'항목': '결제액 합계', '구(결함본)': '30,151,084,828,052', '신(재배포본)': f'{d.TS_AT.sum():,}'},
    ]), '행 수와 결제액이 그대로이고 컬럼만 복구됐다. 진단대로 파일 생성 오류였고 정의서가 옳았다.'))
    return out


def all_tables():
    return [('SK 유동인구', sk_tables()), ('신한카드 데이터1', card_tables()), ('신한카드 데이터2', card2_tables())]
