"""분석 엔진 기준값. 바꾸면 모든 도구 결과가 같이 바뀐다 (재현성: params로 반환)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'preprocessed'
# flow_cell: 팀 레포에 있으면 레포 루트 preprocessed/ 것을 쓰고, 없으면 엔진 사본
FLOW = next(p for p in [ROOT.parent / 'preprocessed' / 'flow_cell.parquet', DATA / 'team' / 'flow_cell.parquet'] if p.exists())
OUT = ROOT / 'out'

REGIONS = ('강남', '춘천')

# 활동 위축 (사랑 src/eda_srh.py 를 엔진이 직접 계산, prep/06): 거주 + 고령 상위 25% + day_share robust z 음수 지속
PERSIST_MIN = 4                     # 6개월 중 낮 활동 저하 개월 수 하한
SENIOR_Q = 0.75                     # 고령 상위 분위 (거주 행 기준)

# 거주 칸: 팀 기준(월별 야간 비중 AND SGIS 1km 주택 수, 한 달이라도 통과) AND GIS 주거·용도미상 건물 ≥ 1 (9/30)
NIGHT_THR = {'강남': 0.07, '춘천': 0.03}
HOUSING_THR = {'강남': 200, '춘천': 30}
RESID_OK = ('주거', '용도미상')

# 자원 "멂" (9/30 확정): 절대 거리
FAR_SOCIAL_M = 500                  # 교류: 경로당·마을회관·도서관·공공체육·문화 (어르신 도보 약 10분)
FAR_HEALTH_M = 3000                 # 보건: 보건소·지소·분소·진료소 (버스·차량 거리)

# 예방인프라형은 어르신 비중 상위 동네만 (9/30 결정). 위축 후보(사랑)도 고령 상위 25% 조건이라 같은 대상끼리 비교
PREVENT_SENIOR_Q = 0.75             # 지역 거주 칸 senior_ratio 분위. 미달 칸은 공백이어도 관찰형

# 고립 유형 2x2 (5차 회의)
TYPES = {
    '연계형':      {'priority': 2, 'action': '동행·프로그램 연결'},
    '긴급방문형':   {'priority': 1, 'action': '방문 안부·이동형 상담'},
    '예방인프라형': {'priority': 3, 'action': '이동형 서비스·공공시설 개방 검토'},
    '관찰형':      {'priority': 4, 'action': '정기 모니터링'},
}

# 배치 시뮬레이션 기본값
SIM_RADIUS_M = 1000
SIM_K = 3

CAVEATS = [
    '통신 유동인구는 머무는 사람 기준이며 거주자와 같지 않다. 거주 여부는 현장 확인이 필요하다.',
    '개인이 아니라 250m 칸 단위 집계 결과다.',
    '거리는 칸 중심에서 시설까지 직선거리다. 실제 이동 시간·경사·교통편은 반영하지 않는다.',
]
CAVEAT_GANGNAM_HEALTH = '강남 보건 거리는 공공 보건기관(3곳)만 반영해 민간 의원 접근성은 빠져 있다.'
CAVEAT_LAYERS = ('긴급방문형·연계형은 활동 위축 신호가 있는 칸(정책 우선 대상)이고, 예방인프라형·관찰형은 위축 신호가 없는 '
                 '일반 거주 칸의 자원 구조 지도다. 두 층을 같은 무게의 위험 숫자로 합쳐 말하지 않는다.')
CAVEAT_SGIS = 'SGIS 값(주택 수·고령·1인가구)은 1km 격자 단위라 같은 1km 안의 250m 칸이 같은 값을 공유한다. 춘천은 신뢰 격자가 적다.'
CAVEAT_RESID = '거주 칸 = 팀 기준(야간 비중 + SGIS 1km 주택 수) 통과 칸 중 GIS 주거·용도미상 건물이 있는 칸.'
