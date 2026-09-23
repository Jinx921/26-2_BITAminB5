"""공공데이터포털 OpenAPI 수집 — 체육시설 / 사회복지시설.

키는 저장소에 넣지 않는다. 루트의 .env 에 아래처럼 둔다 (.env 는 git 제외).
공공데이터포털 계정의 일반 인증키는 보통 하나이므로 아래 한 줄이면 된다.
데이터별로 키가 다르면 DATA_GO_KR_KEY_SPORTS / DATA_GO_KR_KEY_WELFARE 로 따로 둔다.

    DATA_GO_KR_KEY=디코딩된_일반인증키

사용
    python3 notebooks/fetch_api_external.py --probe sports    # 응답 필드만 확인
    python3 notebooks/fetch_api_external.py sports            # 수집 → CSV
    python3 notebooks/fetch_api_external.py welfare
    python3 notebooks/fetch_api_external.py all
"""
from __future__ import annotations

import argparse, json, pathlib, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
import config as C

ENDPOINTS = {
    'sports': {
        'name': '전국체육시설표준데이터',
        'base': 'https://apis.data.go.kr/B551014/SRVC_API_SFMS_FACI',
        'ops': ['TODZ_API_SFMS_FACI'],
        'extra': {'resultType': 'json'},     # 없으면 INVALID_REQUEST_PARAMETER_ERROR
        'regions': [{'cp_nm': '서울특별시', 'cpb_nm': '강남구'},
                    {'cp_nm': '강원특별자치도', 'cpb_nm': '춘천시'},
                    {'cp_nm': '강원도', 'cpb_nm': '춘천시'}],   # 개편 전 명칭 대비
        'out': '전국체육시설표준데이터_api.csv',
        'env': 'DATA_GO_KR_KEY_SPORTS',
    },
    'welfare': {
        'name': '전국사회복지시설표준데이터',
        # 활용가이드 v2.5 는 Service1 + 접미사 없는 op 로 적혀 있으나 현행은 Service2 + op 뒤에 '2'.
        'base': 'https://apis.data.go.kr/B554287/sclWlfrFcltInfoInqirService2',
        'ops': ['getFcltListInfoInqire2',      # 시설 목록정보 조회
                'getFcltByBassInfoInqire2',    # 시설별 기본정보 (주소 포함)
                'getNFcltBizInqire2', 'getFcltKindCodeInfoInqire2',
                'getFcltByEvntInfo2', 'getFcltByJoInfo2'],
        # jrsdSggCd = 행정표준 법정동코드(시군구)
        # 2023년 강원특별자치도 전환으로 시도코드가 42 → 51 로 바뀌었다.
        'regions': [{'jrsdSggCd': '1168000000'},   # 서울 강남구
                    {'jrsdSggCd': '5111000000'},   # 강원특별자치도 춘천시
                    {'jrsdSggCd': '4211000000'}],  # 구 강원도 코드 (혹시 남아 있으면)
        'xml_only': True,     # 교환 데이터 표준이 XML 뿐이다
        'out': '전국사회복지시설표준데이터_api.csv',
        'env': 'DATA_GO_KR_KEY_WELFARE',
    },
}


def _env() -> dict[str, str]:
    f = C.ROOT / '.env'
    out = {}
    if f.exists():
        for line in f.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _key(spec: dict) -> str:
    e = _env()
    for name in (spec['env'], 'DATA_GO_KR_KEY'):
        if e.get(name):
            return e[name]
    sys.exit(f".env 에 {spec['env']}=... 를 넣어야 한다 (디코딩된 일반 인증키). "
             f"한 키를 공용으로 쓰려면 DATA_GO_KR_KEY 도 가능하다.")


def _call(url: str, params: dict, timeout: int = 40) -> tuple[str, str]:
    """(본문, 컨텐츠타입). serviceKey 는 이미 인코딩된 값일 수 있어 직접 이어붙인다."""
    sk = params.pop('serviceKey')
    qs = urllib.parse.urlencode(params, encoding='utf-8')
    # 포털이 주는 '인코딩' 키에는 이미 %XX 가 들어 있다. 다시 인코딩하면 인증이 깨진다.
    if not re.search(r'%[0-9A-Fa-f]{2}', sk):
        sk = urllib.parse.quote(sk, safe='')
    full = f"{url}?serviceKey={sk}&{qs}"
    req = urllib.request.Request(full, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace'), r.headers.get('Content-Type', '')


def _rows(body: str) -> tuple[list[dict], int | None, str | None]:
    """JSON/XML 어느 쪽이든 (행목록, 전체건수, 에러메시지) 로 정규화."""
    s = body.lstrip()
    if s.startswith('{') or s.startswith('['):
        j = json.loads(s)
        def dig(o):
            if isinstance(o, list):
                return [x for x in o if isinstance(x, dict)]
            if isinstance(o, dict):
                for k in ('item', 'items', 'row', 'body', 'response', 'data', 'result'):
                    if k in o:
                        r = dig(o[k])
                        if r:
                            return r
                for v in o.values():
                    r = dig(v)
                    if r:
                        return r
            return []
        total = None
        def findtot(o):
            nonlocal total
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.lower() in ('totalcount', 'total_count', 'totcnt') and str(v).isdigit():
                        total = int(v)
                    findtot(v)
            elif isinstance(o, list):
                for v in o: findtot(v)
        findtot(j)
        return dig(j), total, None
    try:
        root = ET.fromstring(s)
    except ET.ParseError:
        return [], None, body[:300]
    msg = root.findtext('.//returnAuthMsg') or root.findtext('.//errMsg') or root.findtext('.//resultMsg')
    code = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
    if msg and code not in ('00', '0', None):
        return [], None, f'{code}: {msg}'
    items = root.findall('.//item') or root.findall('.//row')
    rows = [{c.tag: (c.text or '').strip() for c in it} for it in items]
    tot = root.findtext('.//totalCount')
    return rows, int(tot) if tot and tot.isdigit() else None, None


def discover(kind: str) -> None:
    """오퍼레이션 경로 후보를 하나씩 호출해 어느 것이 응답하는지 확인한다."""
    spec = ENDPOINTS[kind]
    key = _key(spec)
    print(f"  base: {spec['base']}")
    for op in spec['ops']:
        url = f"{spec['base']}/{op}"
        try:
            q = {'serviceKey': key, 'pageNo': 1, 'numOfRows': 1, **spec.get('extra', {})}
            if not spec.get('xml_only'):
                q.setdefault('type', 'json')
            q |= (spec.get('regions') or [{}])[0]
            body, _ = _call(url, q)
        except Exception as e:
            print(f"  [{op:<22}] 예외 {type(e).__name__}: {str(e)[:60]}")
            continue
        rows, total, err = _rows(body)
        if err:
            print(f"  [{op:<22}] 오류 {err[:70]}")
        elif rows:
            print(f"  [{op:<22}] ✓ 응답 {len(rows)}행 / 전체 {total} / 필드 {len(rows[0])}개")
            print(f"       {', '.join(list(rows[0])[:14])}")
        else:
            print(f"  [{op:<22}] 빈 응답 — {body[:90].replace(chr(10),' ')}")
        time.sleep(0.2)


def fetch(kind: str, probe: bool = False, page_size: int = 500,
          op: str | None = None) -> pd.DataFrame | None:
    spec = ENDPOINTS[kind]
    url = f"{spec['base']}/{op or spec['ops'][0]}"
    key, all_rows = _key(spec), []
    for region in spec['regions']:
        page, seen = 1, 0
        while True:
            p = {'serviceKey': key, 'pageNo': page, 'numOfRows': page_size,
                 **spec.get('extra', {}), **region}
            if not spec.get('xml_only'):
                p.setdefault('type', 'json')
            body = None
            for u in (url, url.replace(spec['base'], spec['fallback_base'])
                      if spec.get('fallback_base') else None):
                if not u:
                    continue
                try:
                    body, ctype = _call(u, dict(p))
                except Exception as e:
                    print(f"  [실패] {u.rsplit('/',2)[-2]} {region or '전체'} p{page}: {type(e).__name__} {e}")
                    continue
                if _rows(body)[0] or not _rows(body)[2]:
                    url = u
                    break
            if body is None:
                break
            rows, total, err = _rows(body)
            if err:
                print(f"  [응답오류] {region or '전체'}: {err}")
                break
            if probe:
                print(f"  요청: {region or '전체'} / Content-Type: {ctype}")
                print(f"  전체건수: {total} / 이번 페이지 {len(rows)}행")
                if rows:
                    print("  필드:")
                    for k, v in rows[0].items():
                        print(f"    {k:<24} = {str(v)[:44]}")
                else:
                    print("  본문 앞부분:", body[:300].replace('\n', ' '))
                return None
            if not rows:
                break
            all_rows += [{**r, '_region_param': str(region)} for r in rows]
            seen += len(rows)
            print(f"  {region or '전체'} p{page}: +{len(rows)} (누적 {seen:,}"
                  + (f" / {total:,})" if total else ")"))
            if total:
                if seen >= total:
                    break
            elif len(rows) < page_size:
                break
            page += 1
            time.sleep(0.2)
    if not all_rows:
        print("  수집된 행이 없다.")
        return None
    df = pd.DataFrame(all_rows)
    C.EXTERNAL.mkdir(parents=True, exist_ok=True)
    out = C.EXTERNAL / spec['out']
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"  저장 → {out}  ({len(df):,}행 × {df.shape[1]}열)")
    return df


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=[*ENDPOINTS, 'all'])
    ap.add_argument('--probe', action='store_true', help='첫 응답의 필드만 출력하고 종료')
    ap.add_argument('--discover', action='store_true', help='오퍼레이션 경로 후보를 탐색')
    ap.add_argument('--op', help='오퍼레이션 경로를 직접 지정')
    a = ap.parse_args()
    for k in ([*ENDPOINTS] if a.kind == 'all' else [a.kind]):
        print(f"\n=== {ENDPOINTS[k]['name']} ===")
        if a.discover:
            discover(k)
        else:
            fetch(k, probe=a.probe, op=a.op)
