import 'leaflet/dist/leaflet.css'
import { useEffect, type ReactNode } from 'react'
import type { LatLngBoundsExpression } from 'leaflet'
import { MapContainer, TileLayer, ZoomControl, useMap } from 'react-leaflet'
import { REGIONS, type RegionKey } from '@/config'

/** bounds 가 바뀌면 지도를 맞춘다 */
function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap()
  const key = JSON.stringify(bounds)
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 16 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, map])
  return null
}

export interface BaseMapProps {
  /** 처음에 맞출 범위. 없으면 region 중심 */
  bounds?: LatLngBoundsExpression | null
  region?: RegionKey | null
  className?: string
  children?: ReactNode
  /** 모바일에서 스크롤 중 지도가 잡히지 않게 */
  scrollWheelZoom?: boolean
  /** 줌 버튼 위치. 지도 위에 다른 컨트롤을 올릴 때 옮긴다 */
  zoomPosition?: 'topleft' | 'topright' | 'bottomright' | 'bottomleft'
}

export function BaseMap({ bounds, region, className = 'h-80', children, scrollWheelZoom = true, zoomPosition = 'topleft' }: BaseMapProps) {
  const r = REGIONS[region ?? '춘천']
  return (
    <div className={`relative overflow-hidden rounded-2xl border border-slate-200 ${className}`}>
      <MapContainer center={r.center} zoom={11} scrollWheelZoom={scrollWheelZoom} className="h-full w-full" attributionControl zoomControl={false}>
        <ZoomControl position={zoomPosition} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <FitBounds bounds={bounds ?? (region ? r.bbox : null)} />
        {children}
      </MapContainer>
    </div>
  )
}
