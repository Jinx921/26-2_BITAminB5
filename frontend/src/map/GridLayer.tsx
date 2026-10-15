import { useMemo } from 'react'
import L, { type Layer, type PathOptions } from 'leaflet'
import { GeoJSON } from 'react-leaflet'
import type { GridCollection, GridFeature, GridProps } from '@/types/geo'
import { HIGHLIGHT_STROKE, MONTHS_COLOR, SELECTED_STROKE, SIM_COLOR, TYPE_COLOR, TYPE_FILL_OPACITY } from './colors'

export type GridVariant = 'types' | 'candidates' | 'sim'

export interface GridLayerProps {
  data: GridCollection
  /** 'types' 유형 색 / 'candidates' 위축 개월 색 / 'sim' 닿는 칸 색 */
  variant?: GridVariant
  /** 답변에서 언급된 칸 (굵은 테두리) */
  highlightIds?: ReadonlySet<string>
  /** 답변 결과에 포함된 칸 (중간 테두리). 후보 응답의 격자 강조에 쓴다 */
  secondaryIds?: ReadonlySet<string>
  /** 그리지 않을 칸 */
  hiddenIds?: ReadonlySet<string>
  /** 이 유형만 그린다. 비어 있으면 전체 */
  visibleTypes?: ReadonlySet<string>
  selectedId?: string | null
  onSelect?: (props: GridProps) => void
}

function fillFor(p: GridProps, variant: GridVariant): { color: string; opacity: number } {
  if (variant === 'candidates') return { color: MONTHS_COLOR[p.persistent_months ?? 4] ?? MONTHS_COLOR[4], opacity: 0.7 }
  if (variant === 'sim') return p.covered === 1 ? { color: SIM_COLOR.covered, opacity: 0.65 } : { color: SIM_COLOR.gap, opacity: 0.65 }
  const t = p.type ?? '관찰형'
  return { color: TYPE_COLOR[t] ?? '#cbd5e1', opacity: TYPE_FILL_OPACITY[t] ?? 0.3 }
}

function tooltipFor(p: GridProps, variant: GridVariant): string {
  const parts = [`<b>${p.emd_name}</b>`]
  if (variant === 'candidates') parts.push(`6개월 중 ${p.persistent_months}개월 활동 감소`, p.res_status ?? '')
  else if (variant === 'sim') parts.push(p.covered === 1 ? '이동형 거점이 닿는 동네' : '거점이 닿지 않는 동네 (공백)')
  else {
    parts.push(p.type ?? '')
    if (p.gap_tag) parts.push(`${p.gap_tag} 시설이 먼 동네`)
  }
  if (p.field_status === 'downgraded') parts.push(`현장 확인으로 변경 (원래 ${p.engine_type ?? ''}, 우선순위 ${p.engine_priority ?? ''})`)
  if (p.field_status === 'excluded') parts.push('현장 확인으로 제외')
  return parts.filter(Boolean).join('<br/>')
}

/** 누르면 뜨는 작은 팝업. cell_id 는 쓰지 않는다 */
function popupFor(p: GridProps, variant: GridVariant): string {
  const row = (k: string, v: string) => `<div style="display:flex;justify-content:space-between;gap:12px"><span style="color:#6b7280">${k}</span><b>${v}</b></div>`
  const rows = [`<div style="font-weight:700;font-size:14px;margin-bottom:4px">${p.emd_name}</div>`]
  if (variant === 'candidates') {
    rows.push(row('지속 개월', `${p.persistent_months ?? '-'}개월 / 6`), row('거주 상태', p.res_status ?? '-'))
  } else if (variant === 'sim') {
    rows.push(row('거점 도달', p.covered === 1 ? '닿음' : '공백'), row('유형', p.type ?? '-'))
  } else {
    rows.push(row('유형', p.type ?? '-'))
    if (p.gap_tag) rows.push(row('먼 시설', p.gap_tag))
    if (p.field_status) rows.push(row('현장 확인', p.field_status === 'excluded' ? '제외' : '관찰형으로 변경'))
  }
  return `<div style="font-size:13px;min-width:150px">${rows.join('')}</div>`
}

/**
 * 250m 격자 폴리곤 레이어. react-leaflet 의 GeoJSON 은 data 가 바뀌어도 다시 그리지 않으므로 key 로 강제한다.
 * 후보 지도의 '용도미상' 칸은 점선 테두리로 구분한다.
 */
export function GridLayer({ data, variant = 'types', highlightIds, secondaryIds, hiddenIds, visibleTypes, selectedId, onSelect }: GridLayerProps) {
  const key = useMemo(
    () =>
      [
        data.features.length,
        variant,
        [...(highlightIds ?? [])].join(','),
        [...(secondaryIds ?? [])].join(','),
        [...(hiddenIds ?? [])].join(','),
        [...(visibleTypes ?? [])].join(','),
        selectedId ?? '',
      ].join('|'),
    [data, variant, highlightIds, secondaryIds, hiddenIds, visibleTypes, selectedId],
  )

  const style = (feature?: GridFeature): PathOptions => {
    const p = feature?.properties ?? ({} as GridProps)
    const { color, opacity } = fillFor(p, variant)
    const hl = highlightIds?.has(p.cell_id)
    const sec = secondaryIds?.has(p.cell_id)
    const sel = selectedId === p.cell_id
    const unknownUse = variant === 'candidates' && p.res_status === '용도미상'
    return {
      fillColor: color,
      fillOpacity: opacity,
      color: sel ? SELECTED_STROKE : hl || sec ? HIGHLIGHT_STROKE : unknownUse ? '#7c2d12' : color,
      weight: sel ? 3 : hl ? 2.5 : sec ? 1.5 : unknownUse ? 1.2 : 0.6,
      opacity: sel || hl || sec ? 1 : 0.9,
      dashArray: unknownUse ? '3 3' : undefined,
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
    layer.bindPopup(popupFor(feature.properties, variant), { closeButton: false, maxWidth: 240 })
    if (onSelect) layer.on('click', () => onSelect(feature.properties))
    if (layer instanceof L.Path) {
      layer.on('mouseover', () => layer.setStyle({ weight: 2.5, opacity: 1 }))
      layer.on('mouseout', () => layer.setStyle(style(feature)))
    }
  }

  return <GeoJSON key={key} data={data} style={style as never} filter={filter as never} onEachFeature={onEach as never} />
}
