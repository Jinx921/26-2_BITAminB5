/** divIcon·시설 아이콘 등 지도 마커 도우미 (컴포넌트가 아닌 함수는 여기에) */
import L from 'leaflet'
import { regionOf } from '@/config'
import { FACILITY_GROUP_COLOR, HIGHLIGHT_STROKE, SELECTED_STROKE } from './colors'

export function divIcon(html: string, size: number, extraClass = '') {
  return L.divIcon({ html, className: `bitamin-marker ${extraClass}`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] })
}

export function badgeHtml(text: string, bg: string, border: string, size: number, fontSize = 12) {
  return `<div style="width:${size}px;height:${size}px;border-radius:9999px;background:${bg};border:2.5px solid ${border};color:#fff;font-weight:700;font-size:${fontSize}px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,.35)">${text}</div>`
}

export function facilityIcon(kind: string, group: 'social' | 'health' | undefined, highlight: boolean, selected: boolean) {
  const color = group ? FACILITY_GROUP_COLOR[group] : '#334155'
  const border = selected ? SELECTED_STROKE : highlight ? HIGHLIGHT_STROKE : '#fff'
  const size = highlight || selected ? 20 : 16
  const letter = kind === '보건' ? '+' : ''
  return divIcon(
    `<div title="${kind}" style="width:${size}px;height:${size}px;border-radius:9999px;background:${color};border:2.5px solid ${border};display:flex;align-items:center;justify-content:center;color:#fff;font-size:${size * 0.7}px;font-weight:700;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,.35)">${letter}</div>`,
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


/** 번호 마커 색: 1 초록, 2 파랑, 3 주황, 그 뒤는 남색 */
export const NUMBER_COLORS = ['#2f855a', '#1d4ed8', '#c05621']
export function numberColor(n: number): string {
  return NUMBER_COLORS[n - 1] ?? '#111827'
}

export function numberIcon(n: number, opts: { selected?: boolean; size?: number } = {}) {
  const size = opts.size ?? (opts.selected ? 36 : 30)
  const border = opts.selected ? '#111827' : '#ffffff'
  return divIcon(
    `<div style="width:${size}px;height:${size}px;border-radius:9999px;background:${numberColor(n)};border:2.5px solid ${border};color:#fff;font-weight:700;font-size:${Math.round(size * 0.45)}px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,.3)">${n}</div>`,
    size,
  )
}

/** "우리 집" 마커: 파란 점 + 라벨 */
export function homeIcon(label = '우리 집') {
  return L.divIcon({
    html: `<div style="display:flex;flex-direction:column;align-items:center;gap:2px"><div style="width:22px;height:22px;border-radius:9999px;background:#1d4ed8;border:3px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35)"></div><span style="font-size:12px;font-weight:700;color:#1d4ed8;white-space:nowrap;text-shadow:0 0 3px #fff,0 0 3px #fff">${label}</span></div>`,
    className: 'bitamin-marker',
    iconSize: [60, 40],
    iconAnchor: [30, 11],
  })
}

/** 거점 마커: ★ 배지 옆에 '닿는 N곳' 작은 라벨 */
export function siteIcon(covers: number | null | undefined, border = '#fff') {
  const label = covers !== null && covers !== undefined ? `<span style="margin-left:4px;padding:2px 6px;border-radius:9999px;background:#fff;border:1px solid #c7d7fe;color:#1d4ed8;font-size:11px;font-weight:700;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.15)">닿는 ${covers}곳</span>` : ''
  return L.divIcon({
    html: `<div style="display:flex;align-items:center">${badgeHtml('★', '#1d4ed8', border, 30, 14)}${label}</div>`,
    className: 'bitamin-marker',
    iconSize: [110, 30],
    iconAnchor: [15, 15],
  })
}
