/** engine/지도_규격.md 및 지도 API GeoJSON properties (WGS84) */
import type { Feature, FeatureCollection, Point, Polygon } from 'geojson'
import type { GapTag, IsolationType } from './display'

export type FieldStatus = 'excluded' | 'downgraded'

export interface GridProps {
  cell_id: string
  emd_name: string
  // 유형 지도
  type?: IsolationType
  priority?: 1 | 2 | 3 | 4
  gap_tag?: GapTag
  // 후보 지도
  persistent_months?: number
  res_status?: string
  // 배치 지도
  covered?: 0 | 1
  // 현장 확인 반영 결과. 서버가 원본 engine 값과 함께 반환한다.
  field_status?: FieldStatus
  engine_type?: IsolationType
  engine_priority?: 1 | 2 | 3 | 4
  field_checked_at?: string
}

export interface FacilityProps {
  fac_id: string
  name: string
  addr: string
  kind: string
  group: 'social' | 'health'
}

export type GridFeature = Feature<Polygon, GridProps>
export type GridCollection = FeatureCollection<Polygon, GridProps>
export type FacilityFeature = Feature<Point, FacilityProps>
export type FacilityCollection = FeatureCollection<Point, FacilityProps>
