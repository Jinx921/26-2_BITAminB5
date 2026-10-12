/**
 * 에이전트 화면 조각(agent/screen.py 의 display). 백엔드 POST /api/v1/questions 는 이 객체만 돌려준다.
 * 프론트는 이 객체를 조각 배열로 바꿔(fragments/toFragments) 순서대로 그린다.
 */

export type IsolationType = '긴급방문형' | '연계형' | '예방인프라형' | '관찰형'
export type GapTag = '교류' | '보건' | '둘다' | ''

export type MapLayer = 'types' | 'candidates' | 'sites' | 'interventions' | 'checks' | 'facilities'

interface BasePoint {
  /** 칸 ID 또는 시설 ID. 화면에 글자로 보여주지 않고 조회 키로만 쓴다 */
  id: string
  lat: number
  lon: number
  /** 답변 문장에서 언급한 곳. 지도에서 강조한다 */
  highlight: boolean
}

export interface TypesPoint extends BasePoint {
  emd_name: string
  type: IsolationType
  gap: GapTag
}
export interface CandidatesPoint extends BasePoint {
  emd_name: string
  months: number
}
export interface SitesPoint extends BasePoint {
  emd_name: string
  covers: number
}
export interface InterventionsPoint extends BasePoint {
  emd_name: string
  option: string
  name: string
  facility_name: string | null
}
export interface ChecksPoint extends BasePoint {
  emd_name: string
  level: string
  questions: string[]
  order: number
}
export interface FacilitiesPoint extends BasePoint {
  name: string
  kind: string
  dist_m: number | null
}

export type MapPoint =
  | TypesPoint
  | CandidatesPoint
  | SitesPoint
  | InterventionsPoint
  | ChecksPoint
  | FacilitiesPoint

export type MapFragmentData =
  | { layer: 'types'; ref: string; geojson: string | null; points: TypesPoint[] }
  | { layer: 'candidates'; ref: string; geojson: string | null; points: CandidatesPoint[] }
  | { layer: 'sites'; ref: string; geojson: string | null; points: SitesPoint[] }
  | { layer: 'interventions'; ref: string; geojson: string | null; points: InterventionsPoint[] }
  | { layer: 'checks'; ref: string; geojson: string | null; points: ChecksPoint[] }
  | { layer: 'facilities'; ref: string; geojson: string | null; points: FacilitiesPoint[] }

export interface BarChartData {
  type: 'bar'
  title: string
  unit: string
  total: number
  items: { label: string; value: number; remaining: number }[]
}

export type DocumentType = 'proposal' | 'status_report' | 'resident_notice'

export interface DocumentData {
  type: DocumentType | string
  type_name: string
  title: string
  sections: { heading: string; body: string }[]
  markdown: string
}

export interface Confidence {
  label: string
  note: string
}

export interface Display {
  headline: string
  details: string[]
  caution: string
  confidence: Confidence | null
  map: MapFragmentData | null
  chart: BarChartData | null
  document: DocumentData | null
}

/** 조각 렌더러가 쓰는 조각 종류. display 의 키와 같고, 모르는 키는 unknown 으로 간다 */
export type FragmentType =
  | 'headline'
  | 'details'
  | 'caution'
  | 'confidence'
  | 'map'
  | 'chart'
  | 'document'
  | 'unknown'

export interface Fragment<T = unknown> {
  type: FragmentType
  key: string
  data: T
}
