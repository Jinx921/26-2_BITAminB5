# BITAmin B5 — 2026 빅콘테스트

SK 통신 유동인구 + 신한카드 소비 데이터 기반 분석 프로젝트.

## 구조

```
data/raw/sk_flow_pop/         # SK 유동인구 CSV 18개 ('|' 구분, UTF-8 BOM)
data/raw/shinhan_card/        # 신한카드 txt 2개 (탭 구분, CP949)
data/_zip/                    # 원본 배포 zip 보관 (git 제외)
src/config.py                 # 경로 · 인코딩 · 구분자 상수
src/loaders.py                # 원천 데이터 로더 (202512 중복 자동 제거)
src/eda.py                    # EDA 표 27개 계산 로직
notebooks/run_eda.py          # 실행 → 터미널 출력 + outputs/ 갱신
notebooks/build_report.py     # 템플릿 + manifest → HTML 리포트
notebooks/report_template.html
docs/                         # 해석 가이드 · 결과 요약
outputs/                      # EDA 산출물 (표 CSV · HTML 리포트) — 커밋된다
preprocessed/                 # 전처리 결과 parquet — 커밋된다
```

`preprocessed/` 내용:

| 파일 | 크기 | 내용 |
| --- | --- | --- |
| `card_clean.parquet` | 983,413행 × 13열 | 카드 데이터1 정제 (법인 제외, `age`·`ticket`·`is_social` 파생) |
| `flow_cell.parquet` | 48,546행 × 50열 | 격자 단위 집계 (`peer` 그룹, `dev_*` 이탈 지표, `trend`) |

`data/` 와 `submissions/` 는 git에 올라가지 않는다 (원천 데이터 ~350MB).

`interim` / `processed` / `external` 경로는 `config.py` 에 상수로만 정의돼 있고 실제로 쓰는 시점에 생긴다
(`loaders.cache()` 는 저장할 때 알아서 만든다). 빈 폴더를 미리 두지 않는다.

## 문서

| 문서 | 내용 |
| --- | --- |
| `docs/team_eda_merged.md` | **팀 5인 EDA 통합본** — 제공/외부 데이터, 충돌 정리 |
| `docs/data_interpretation.md` | 분석 전 합의할 해석 규칙 — **먼저 읽을 것** |
| `docs/EDA_summary.md` | 원천 데이터 관측 결과 |
| `docs/external_data.md` | 외부 데이터 수집·판정·전처리·EDA |
| `docs/data_integration.md` | 데이터 간 연결 전략과 그 한계 |
| `outputs/eda_report.html` | 표 35개 + 차트 24개. `open outputs/eda_report.html` |
| [같은 페이지 온라인 링크](https://claude.ai/artifact/QtLETb7adVcx7M9HWCgSNj) | Claude Artifact. 기본 비공개이므로 공유 설정 필요 |

표 원본은 `outputs/tables/*.csv` (UTF-8 BOM, 엑셀에서 바로 열림).

```bash
python3 notebooks/build_grid_access.py  # 250m 격자 × 자원 접근성
python3 notebooks/eda_external.py       # 외부 데이터 EDA
python3 notebooks/run_eda.py            # 표 35개 + manifest 재생성
python3 notebooks/build_report.py       # manifest → HTML 리포트
```

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

age = load_sk("flow_age_pop", months=["202507"])   # 중복 제거된 상태로 반환
mct = load_shinhan("mct")   # 데이터1 — 시간대(TIME_GB) 있음, 법인 포함
cln = load_shinhan("cln")   # 데이터2 — 고객 거주지(CLN_SGG_CD) 있음, 법인 제외
```

인코딩/구분자는 `src/config.py` 에만 둔다. 직접 `pd.read_csv` 하지 말 것.
(`src/loaders.py` 의 이름은 표준 라이브러리 `io` 와 충돌하지 않도록 고른 것 — `src/io.py` 로 두면 `import pandas` 가 깨진다.)

## 데이터 메모

- 기간은 2025-07 ~ 2025-12, 대상은 서울 강남구와 강원 춘천시 두 곳뿐이다.
- 공간 키가 다름: SK 원본은 **50m 격자**(`BLOCK_CD`, `X_COORD`/`Y_COORD`), 신한카드는 **시군구**(2개).
  직접 결합은 불가능하므로 각 데이터가 답할 수 있는 범위에서 따로 분석한다.
- **격자 분석의 팀 표준은 250m** (`preprocessed/flow_cell.parquet`, `cell_id = floor(X/250)_floor(Y/250)`).
  50m는 춘천에서 칸당 1명 미만이라 쓸 수 없다. 거리 계산의 기준점은 격자 중심이다.
- SK 좌표계는 **UTM-K(EPSG:5179)** — 테이블 정의서에 명시돼 있다.
- SK 값은 일별 시계열이 아니라 **월별 "일평균"** 이다. 격자당 관측 시점이 6개뿐이다.
- **신한카드 데이터2는 2026-09 재배포본**(`데이터2_수정.txt`)을 쓴다. 최초 배포본은
  `TA_YMD` · `MCT_SGG_CD` · `MCT_RY_CD` 가 누락된 5컬럼이었고, 재배포로 8컬럼이 복구됐다.
  행 수와 결제액 합계는 동일하다.
- 두 카드 파일의 역할이 다르다. **데이터1**은 시간대(`TIME_GB`)가 있고 법인카드를 포함한다.
  **데이터2**는 고객 거주지(`CLN_SGG_CD`)가 있고 법인카드가 빠져 있다 — 우리 부문용 파일이다.
- **`flow_time_pop_202512` 와 `flow_wkdy_pop_202512` 에는 중복 행이 있다.** 전체 행이 정확히
  2번씩 들어 있다 (185,090→92,545 / 242,534→121,267). `load_sk()` 가 자동 제거하지만
  원천 CSV를 직접 읽을 때는 직접 걷어내야 한다.

해석상 주의사항은 `docs/data_interpretation.md` 에 정리돼 있다. 분석 전에 먼저 읽을 것.
