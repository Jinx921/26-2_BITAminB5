/** divIcon·시설 아이콘 등 지도 마커 도우미 (컴포넌트가 아닌 함수는 여기에) */
import L from 'leaflet'
import { regionOf } from '@/config'
import { FACILITY_GROUP_COLOR, FACILITY_KIND_ICON, HIGHLIGHT_STROKE, SELECTED_STROKE } from './colors'

export function divIcon(html: string, size: number, extraClass = '') {
  return L.divIcon({ html, className: `bitamin-marker ${extraClass}`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] })
}

export function badgeHtml(text: string, bg: string, border: string, size: number, fontSize = 12) {
  return `<div style="width:${size}px;height:${size}px;border-radius:9999px;background:${bg};border:2.5px solid ${border};color:#fff;font-weight:700;font-size:${fontSize}px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,.35)">${text}</div>`
}

export function facilityIcon(kind: string, group: 'social' | 'health' | undefined, highlight: boolean, selected: boolean) {
  const color = group ? FACILITY_GROUP_COLOR[group] : '#334155'
  const border = selected ? SELECTED_STROKE : highlight ? HIGHLIGHT_STROKE : '#fff'
  const size = highlight || selected ? 34 : 28
  const emoji = FACILITY_KIND_ICON[kind] ?? '📍'
  return divIcon(
    `<div style="width:${size}px;height:${size}px;border-radius:9999px;background:${color};border:2.5px solid ${border};display:flex;align-items:center;justify-content:center;font-size:${size * 0.5}px;box-shadow:0 1px 3px rgba(0,0,0,.35)">${emoji}</div>`,
    size,
  )
}

export function groupOfKind(kind: string): 'social' | 'health' {
  return kind === '보건' ? 'health' : 'social'
}

export function formatDistance(m: number | null | undefined): string {
  if (m === null || m === undefined || !Number.isFinite(m)) return ''
  return m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${Math.round(m)}m`
}

/** 강남·춘천 범위를 벗어난 점은 그리지 않는다 (시설 원천 데이터 이상치 대응) */
export function inServiceArea(p: { lat: number; lon: number }): boolean {
  return regionOf(p.lat, p.lon) !== null
}

