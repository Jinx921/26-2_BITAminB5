# BITAmin B5 — 2026 빅콘테스트

SK 통신 유동인구 + 신한카드 소비 데이터 기반 분석 프로젝트.

## 구조

```
data/raw/sk_flow_pop/   # SK 유동인구 CSV 18개 ('|' 구분, UTF-8 BOM)
data/raw/shinhan_card/  # 신한카드 txt 2개 (탭 구분, CP949)
notebooks/              # 탐색용 노트북
src/config.py           # 경로 · 인코딩 · 구분자 상수
src/loaders.py          # 원천 데이터 로더
```

`data/`, `outputs/`, `submissions/` 는 git에 올라가지 않는다 (원천 ~350MB).

`interim` / `processed` / `external` / `outputs` / `submissions` 경로는 `config.py` 에 상수로만 정의돼 있고,
실제로 쓰는 시점에 생긴다 (`loaders.cache()` 는 저장할 때 알아서 만든다). 빈 폴더를 미리 두지 않는다.

## 세팅

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

주피터에서는 커널 **Python (BITAmin B5)** 를 고른다 (`python -m ipykernel install --user --name bitamin-b5`).

현재 환경: Python 3.12.5 / pandas 3.0.5 / numpy 2.5.3 / geopandas 1.1.4 / lightgbm 4.7.0

## 데이터 읽기

노트북 첫 셀에서 `src` 를 경로에 추가한다.

```python
import sys; sys.path.insert(0, "../src")

from loaders import load_sk, load_shinhan

age = load_sk("flow_age_pop", months=["202507"])
mct = load_shinhan("mct")
```

인코딩/구분자는 `src/config.py` 에만 둔다. 직접 `pd.read_csv` 하지 말 것.
(`src/loaders.py` 의 이름은 표준 라이브러리 `io` 와 충돌하지 않도록 고른 것 — `src/io.py` 로 두면 `import pandas` 가 깨진다.)

## 데이터 메모

- 공통 공간 키가 다름: SK는 **50m 격자**(`BLOCK_CD`, `X_COORD`/`Y_COORD`), 신한카드는 **시군구 코드**.
  결합하려면 격자 → 시군구 매핑이 선행돼야 함 (행정구역 shapefile을 `data/external/` 에).
- SK 좌표계는 EPSG:5179 추정 — 아직 검증 안 됨.
- 기간: 2025-07 ~ 2025-12.
