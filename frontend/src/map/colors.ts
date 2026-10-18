/**
 * 지도·차트 색. 유형 3종은 dataviz 검증기(CVD·일반 시각 분리, 대비)를 통과한 조합이고,
 * 관찰형은 "해당 없음" 성격이라 채도 낮은 회색으로 깔아 둔다 (색만으로 구분하지 않도록 툴팁·범례에 이름을 함께 쓴다).
 */
import type { IsolationType } from '@/types/display'

export const TYPE_COLOR: Record<IsolationType, string> = {
  긴급방문형: '#b91c1c',
  연계형: '#d97706',
  예방인프라형: '#1d4ed8',
  관찰형: '#cbd5e1',
}
export const TYPE_ORDER: IsolationType[] = ['긴급방문형', '연계형', '예방인프라형', '관찰형']
export const TYPE_FILL_OPACITY: Record<IsolationType, number> = {
  긴급방문형: 0.7,
  연계형: 0.65,
  예방인프라형: 0.55,
  관찰형: 0.25,
}

/** 유형별 한 줄 설명 (범례용). engine classify.type_actions 요약 */
export const TYPE_DESCRIPTION: Record<IsolationType, string> = {
  긴급방문형: '낮 활동이 줄었고 가까운 시설도 멀어 가장 먼저 방문이 필요한 동네',
  연계형: '낮 활동이 줄었지만 가까운 시설은 있어 연결이 필요한 동네',
  예방인프라형: '활동은 유지되지만 시설이 멀어 미리 채워둘 동네',
  관찰형: '지금은 특별한 신호가 없는 동네',
}

export const FACILITY_GROUP_COLOR = { social: '#15803d', health: '#7e22ce' } as const
export const FACILITY_GROUP_LABEL = { social: '교류', health: '보건' } as const

export const FACILITY_KIND_ICON: Record<string, string> = {
  경로당: '🏠',
  도서관: '📚',
  문화시설: '🎭',
  '체육시설(공공)': '🏃',
  보건: '🏥',
}

/** 후보 지도 persistent_months 4/5/6 → 연한→진한 (주황 한 색 순차) */
export const MONTHS_COLOR: Record<number, string> = { 4: '#fdba74', 5: '#f97316', 6: '#c05621' }
export const MONTHS_ORDER = [4, 5, 6]

/** 배치 지도: 거점이 닿는 칸(파랑) / 공백(주황) */
export const SIM_COLOR = { covered: '#1d4ed8', gap: '#c05621' } as const

/** 현장 확인 level */
export const CHECK_LEVEL_COLOR: Record<string, string> = { '꼭 확인': '#b91c1c', '확인 필요': '#d97706' }

/** 개입안 비교: 옵션 등장 순서대로 고정 배정 (순환하지 않음). 유형 색·배치 지도 색과 겹치지 않는 색을 쓴다 */
export const OPTION_COLORS = ['#7c3aed', '#0f766e', '#be185d']

export const SITE_COLOR = '#1d4ed8'
export const HIGHLIGHT_STROKE = '#111827'
export const SELECTED_STROKE = '#0ea5e9'
