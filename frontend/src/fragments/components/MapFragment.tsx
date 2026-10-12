import { useMemo } from 'react'
import { BaseMap, PointsLayer, boundsOfPoints, inServiceArea } from '@/map'
import type { MapFragmentData } from '@/types/display'
import type { FragmentProps } from '../types'

const LAYER_LABEL: Record<MapFragmentData['layer'], string> = {
  types: '먼저 살펴볼 동네',
  candidates: '활동이 줄어든 동네',
  sites: '제안한 거점',
  interventions: '개입안별 거점',
  checks: '현장 확인 동네',
  facilities: '가까운 시설',
}

/** 응답 지도. 점만 그리고 범위는 점에 맞춘다 (전체 격자 색칠은 관리자 메인 지도가 한다) */
export function MapFragment({ fragment, mode, context }: FragmentProps<MapFragmentData>) {
  const map = fragment.data
  const points = useMemo(() => (map.layer === 'facilities' ? map.points.filter(inServiceArea) : map.points), [map])
  const bounds = useMemo(() => boundsOfPoints(points), [points])
  // 시민 화면에는 시설 레이어만 보여준다 (유형·후보·배치는 낙인 방지로 내보내지 않음)
  if (mode === 'citizen' && map.layer !== 'facilities') return null
  if (points.length === 0) return null
  return (
    <div data-fragment="map">
      <p className="mb-2 text-sm font-semibold text-slate-600">
        {LAYER_LABEL[map.layer]} · {points.length}곳
      </p>
      <BaseMap bounds={bounds} region={context.region} className={context.mapClassName ?? 'h-72 md:h-80'} scrollWheelZoom={mode === 'admin'}>
        <PointsLayer map={map} selectedId={context.selectedPointId} onSelect={context.onSelectPoint} />
      </BaseMap>
    </div>
  )
}
