import { useMemo } from 'react'
import L, { type Layer, type PathOptions } from 'leaflet'
import { GeoJSON } from 'react-leaflet'
import type { GridCollection, GridFeature, GridProps } from '@/types/geo'
import { HIGHLIGHT_STROKE, MONTHS_COLOR, SELECTED_STROKE, TYPE_COLOR, TYPE_FILL_OPACITY } from './colors'

export interface GridLayerProps {
  data: GridCollection
  /** 'types' 유형 색 / 'candidates' 위축 개월 색 / 'sim' 닿는 칸 색 */
  variant?: 'types' | 'candidates' | 'sim'
  /** 답변에서 언급된 칸 (굵은 테두리) */
  highlightIds?: ReadonlySet<string>
  /** 그리지 않을 칸 (현장 확인으로 제외된 곳 등) */
  hiddenIds?: ReadonlySet<string>
  /** 이 유형만 그린다. 비어 있으면 전체 */
  visibleTypes?: ReadonlySet<string>
  selectedId?: string | null
  onSelect?: (props: GridProps) => void
}

function fillFor(p: GridProps, variant: GridLayerProps['variant']): { color: string; opacity: number } {
  if (variant === 'candidates') return { color: MONTHS_COLOR[p.persistent_months ?? 4] ?? '#f97316', opacity: 0.6 }
  if (variant === 'sim') return p.covered === 1 ? { color: '#1d4ed8', opacity: 0.6 } : { color: '#b91c1c', opacity: 0.5 }
  const t = p.type ?? '관찰형'
  return { color: TYPE_COLOR[t] ?? '#cbd5e1', opacity: TYPE_FILL_OPACITY[t] ?? 0.3 }
}

function tooltipFor(p: GridProps, variant: GridLayerProps['variant']): string {
  const parts = [`<b>${p.emd_name}</b>`]
  if (variant === 'candidates') parts.push(`최근 6개월 중 ${p.persistent_months}개월 활동 감소`, p.res_status ?? '')
  else if (variant === 'sim') parts.push(p.covered === 1 ? '이동형 거점이 닿는 동네' : '거점이 닿지 않는 동네')
  else {
    parts.push(p.type ?? '')
    if (p.gap_tag) parts.push(`${p.gap_tag} 시설이 먼 동네`)
  }
  if (p.field_status === 'downgraded') {
    parts.push(`현장 확인으로 변경 (원래 ${p.engine_type ?? ''}, 우선순위 ${p.engine_priority ?? ''})`)
  }
  if (p.field_status === 'excluded') {
    parts.push('현장 확인으로 제외')
    if (p.engine_type) parts.push(`엔진 원래 유형: ${p.engine_type}`)
    if (p.engine_priority !== undefined) parts.push(`엔진 원래 우선순위: ${p.engine_priority}`)
  }
  if (p.field_checked_at) parts.push(`현장 확인: ${p.field_checked_at}`)
  return parts.filter(Boolean).join('<br/>')
}

/**
 * 250m 격자 폴리곤 레이어. react-leaflet 의 GeoJSON 은 data 가 바뀌어도 다시 그리지 않으므로 key 로 강제한다.
 * cell_id 는 툴팁에 쓰지 않는다 (지도_규격 4절).
 */
export function GridLayer({ data, variant = 'types', highlightIds, hiddenIds, visibleTypes, selectedId, onSelect }: GridLayerProps) {
  const key = useMemo(
    () =>
      [
        data.features.length,
        variant,
        [...(highlightIds ?? [])].join(','),
        [...(hiddenIds ?? [])].join(','),
        [...(visibleTypes ?? [])].join(','),
        selectedId ?? '',
      ].join('|'),
    [data, variant, highlightIds, hiddenIds, visibleTypes, selectedId],
  )

  const style = (feature?: GridFeature): PathOptions => {
    const p = feature?.properties ?? ({} as GridProps)
    const { color, opacity } = fillFor(p, variant)
    const hl = highlightIds?.has(p.cell_id)
    const sel = selectedId === p.cell_id
    return {
      fillColor: color,
      fillOpacity: opacity,
      color: sel ? SELECTED_STROKE : hl ? HIGHLIGHT_STROKE : color,
      weight: sel ? 3 : hl ? 2.5 : 0.6,
      opacity: sel || hl ? 1 : 0.8,
    }
  }

  const filter = (feature: GridFeature) => {
    const p = feature.properties
    if (hiddenIds?.has(p.cell_id)) return false
    if (visibleTypes && visibleTypes.size > 0 && variant === 'types' && !visibleTypes.has(p.type ?? '관찰형')) return false
    return true
  }

  const onEach = (feature: GridFeature, layer: Layer) => {
    layer.bindTooltip(tooltipFor(feature.properties, variant), { sticky: true, direction: 'top' })
    if (onSelect) layer.on('click', () => onSelect(feature.properties))
    if (layer instanceof L.Path) {
      layer.on('mouseover', () => layer.setStyle({ weight: 2.5, opacity: 1 }))
      layer.on('mouseout', () => layer.setStyle(style(feature)))
    }
  }

  return <GeoJSON key={key} data={data} style={style as never} filter={filter as never} onEachFeature={onEach as never} />
}
