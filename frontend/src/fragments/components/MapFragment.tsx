import { useMemo } from 'react'
import { BaseMap, NumberedPointsLayer, PointsLayer, boundsOfPoints, inServiceArea } from '@/map'
import type { MapFragmentData } from '@/types/display'
import type { FragmentProps } from '../types'

/**
 * 응답 지도. 관리자는 레이어별 점, 시민은 번호 마커 + 우리 집 + 점선.
 * 관리자 메인처럼 큰 지도가 따로 있으면 context.hideMap 으로 숨긴다.
 */
export function MapFragment({ fragment, mode, context }: FragmentProps<MapFragmentData>) {
  const map = fragment.data
  const points = useMemo(() => (map.layer === 'facilities' ? map.points.filter(inServiceArea) : map.points), [map])
  const ordered = useMemo(() => {
    if (!context.orderedIds) return points
    const byId = new Map(points.map((p) => [p.id, p]))
    return context.orderedIds.map((id) => byId.get(id)).filter((p): p is (typeof points)[number] => !!p)
  }, [points, context.orderedIds])
  const bounds = useMemo(() => boundsOfPoints([...ordered, ...(context.home ? [context.home] : [])]), [ordered, context.home])

  if (context.hideMap) return null
  if (mode === 'citizen' && map.layer !== 'facilities') return null
  if (points.length === 0) return null

  return (
    <div data-fragment="map">
      <BaseMap bounds={bounds} region={context.region} className={context.mapClassName ?? 'h-64'} scrollWheelZoom={mode === 'admin'}>
        {mode === 'citizen' ? (
          <NumberedPointsLayer
            points={ordered.map((p) => ({ id: p.id, lat: p.lat, lon: p.lon, name: 'name' in p ? p.name : undefined }))}
            home={context.home}
            selectedId={context.selectedPointId}
            onSelect={(id) => {
              const p = ordered.find((x) => x.id === id)
              if (p) context.onSelectPoint?.(p)
            }}
          />
        ) : (
          <PointsLayer map={map} selectedId={context.selectedPointId} onSelect={context.onSelectPoint} />
        )}
      </BaseMap>
    </div>
  )
}
