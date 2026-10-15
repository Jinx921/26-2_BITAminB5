import type { LatLngBoundsExpression } from 'leaflet'
import { REGIONS, type RegionKey } from '@/config'

export function boundsOfPoints(points: { lat: number; lon: number }[]): LatLngBoundsExpression | null {
  const valid = points.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon))
  if (valid.length === 0) return null
  let s = Infinity, n = -Infinity, w = Infinity, e = -Infinity
  for (const p of valid) {
    s = Math.min(s, p.lat); n = Math.max(n, p.lat); w = Math.min(w, p.lon); e = Math.max(e, p.lon)
  }
  // 점이 하나면 살짝 넓힌다
  if (s === n) { s -= 0.005; n += 0.005 }
  if (w === e) { w -= 0.005; e += 0.005 }
  return [[s, w], [n, e]]
}

export function regionBounds(region: RegionKey): LatLngBoundsExpression {
  return REGIONS[region].bbox
}
