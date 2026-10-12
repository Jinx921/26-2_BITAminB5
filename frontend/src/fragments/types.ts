import type { ComponentType } from 'react'
import type { RegionKey } from '@/config'
import type { Fragment, FragmentType, MapPoint } from '@/types/display'

export type Mode = 'admin' | 'citizen'

/** 조각 컴포넌트가 공통으로 받는 주변 정보 */
export interface FragmentContext {
  region: RegionKey | null
  selectedPointId?: string | null
  onSelectPoint?: (p: MapPoint) => void
  /** 지도 조각 높이 클래스 */
  mapClassName?: string
}

export interface FragmentProps<T = unknown> {
  fragment: Fragment<T>
  mode: Mode
  context: FragmentContext
}

export type FragmentComponent<T = unknown> = ComponentType<FragmentProps<T>>
export type { Fragment, FragmentType }
