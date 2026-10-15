import { CircleMarker, Marker, Polyline, Popup, Tooltip } from 'react-leaflet'
import type { FacilityCollection } from '@/types/geo'
import type { FacilitiesPoint, MapFragmentData, MapPoint } from '@/types/display'
import { CHECK_LEVEL_COLOR, HIGHLIGHT_STROKE, MONTHS_COLOR, OPTION_COLORS, SELECTED_STROKE, TYPE_COLOR } from './colors'
import { badgeHtml, divIcon, facilityIcon, formatDistance, groupOfKind, homeIcon, inServiceArea, numberIcon, siteIcon } from './markers'

export interface PointsLayerProps {
  map: MapFragmentData
  selectedId?: string | null
  onSelect?: (p: MapPoint) => void
}

/** 질문 응답 display.map.points 를 레이어 종류에 맞게 그린다. id 는 화면에 쓰지 않는다 */
export function PointsLayer({ map, selectedId, onSelect }: PointsLayerProps) {
  const click = (p: MapPoint) => ({ click: () => onSelect?.(p) })
  const stroke = (p: MapPoint) => (selectedId === p.id ? SELECTED_STROKE : p.highlight ? HIGHLIGHT_STROKE : '#fff')
  const weight = (p: MapPoint) => (selectedId === p.id || p.highlight ? 3 : 1.5)

  switch (map.layer) {
    case 'types':
      return (
        <>
          {map.points.map((p) => (
            <CircleMarker
              key={p.id}
              center={[p.lat, p.lon]}
              radius={p.highlight ? 9 : 6}
              pathOptions={{ fillColor: TYPE_COLOR[p.type] ?? '#64748b', fillOpacity: 0.9, color: stroke(p), weight: weight(p) }}
              eventHandlers={click(p)}
            >
              <Tooltip direction="top">
                <b>{p.emd_name}</b> · {p.type}
                {p.gap && <> · {p.gap} 시설이 먼 동네</>}
              </Tooltip>
            </CircleMarker>
          ))}
        </>
      )
    case 'candidates':
      return (
        <>
          {map.points.map((p) => (
            <CircleMarker
              key={p.id}
              center={[p.lat, p.lon]}
              radius={p.highlight ? 9 : 6}
              pathOptions={{ fillColor: MONTHS_COLOR[p.months] ?? '#f97316', fillOpacity: 0.9, color: stroke(p), weight: weight(p) }}
              eventHandlers={click(p)}
            >
              <Tooltip direction="top">
                <b>{p.emd_name}</b> · 6개월 중 {p.months}개월 활동 감소
              </Tooltip>
            </CircleMarker>
          ))}
        </>
      )
    case 'sites':
      return (
        <>
          {map.points.map((p) => (
            <Marker key={p.id} position={[p.lat, p.lon]} icon={siteIcon(p.covers, stroke(p))} eventHandlers={click(p)} zIndexOffset={400}>
              <Tooltip direction="top" offset={[0, -14]}>
                <b>{p.emd_name}</b> 거점 · 닿는 동네 {p.covers}곳
              </Tooltip>
              <Popup closeButton={false}>
                <div className="text-[13px]">
                  <p className="font-bold">{p.emd_name} 거점</p>
                  <p>닿는 동네 {p.covers}곳</p>
                </div>
              </Popup>
            </Marker>
          ))}
        </>
      )
    case 'interventions': {
      const options = [...new Set(map.points.map((p) => p.option))]
      return (
        <>
          {map.points.map((p) => {
            const color = OPTION_COLORS[options.indexOf(p.option)] ?? '#334155'
            return (
              <CircleMarker
                key={`${p.option}-${p.id}`}
                center={[p.lat, p.lon]}
                radius={p.highlight ? 10 : 8}
                pathOptions={{ fillColor: color, fillOpacity: 0.9, color: stroke(p), weight: weight(p) }}
                eventHandlers={click(p)}
              >
                <Tooltip direction="top">
                  <b>{p.name}</b> · {p.option}
                </Tooltip>
                <Popup closeButton={false}>
                  <div className="text-[13px]">
                    <p className="font-bold">{p.name}</p>
                    <p>{p.option}</p>
                    <p className="text-ink-3">{p.emd_name}</p>
                    {p.facility_name && <p>기존 시설: {p.facility_name}</p>}
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </>
      )
    }
    case 'checks':
      return (
        <>
          {map.points.map((p) => (
            <Marker
              key={p.id}
              position={[p.lat, p.lon]}
              icon={divIcon(badgeHtml(String(p.order), CHECK_LEVEL_COLOR[p.level] ?? '#334155', stroke(p), 28), 28)}
              eventHandlers={click(p)}
            >
              <Tooltip direction="top">
                <b>
                  {p.order}. {p.emd_name}
                </b>{' '}
                · {p.level}
                <br />
                확인 질문 {p.questions.length}개
              </Tooltip>
            </Marker>
          ))}
        </>
      )
    case 'facilities':
      return (
        <>
          {map.points.filter(inServiceArea).map((p: FacilitiesPoint) => (
            <Marker
              key={p.id}
              position={[p.lat, p.lon]}
              icon={facilityIcon(p.kind, groupOfKind(p.kind), p.highlight, selectedId === p.id)}
              eventHandlers={click(p)}
              zIndexOffset={p.highlight ? 500 : 0}
            >
              <Tooltip direction="top">
                <b>{p.name}</b> · {p.kind}
                {p.dist_m !== null && <> · {formatDistance(p.dist_m)}</>}
              </Tooltip>
            </Marker>
          ))}
        </>
      )
    default:
      return null
  }
}

/** 시설 지도(facilities_*.geojson) 전체를 그린다. 시민 화면 배경용 */
export function FacilitiesGeoLayer({
  data,
  kinds,
  selectedId,
  onSelect,
}: {
  data: FacilityCollection
  /** 보여줄 종류. 비어 있으면 전체 */
  kinds?: ReadonlySet<string>
  selectedId?: string | null
  onSelect?: (f: FacilityCollection['features'][number]['properties'] & { lat: number; lon: number }) => void
}) {
  return (
    <>
      {data.features
        .filter((f) => {
          const [lon, lat] = f.geometry.coordinates
          return inServiceArea({ lat, lon }) && (!kinds || kinds.size === 0 || kinds.has(f.properties.kind))
        })
        .map((f) => {
          const [lon, lat] = f.geometry.coordinates
          const p = f.properties
          return (
            <Marker
              key={p.fac_id}
              position={[lat, lon]}
              icon={facilityIcon(p.kind, p.group, false, selectedId === p.fac_id)}
              eventHandlers={{ click: () => onSelect?.({ ...p, lat, lon }) }}
            >
              <Tooltip direction="top">
                <b>{p.name}</b> · {p.kind}
                <br />
                {p.addr}
              </Tooltip>
            </Marker>
          )
        })}
    </>
  )
}

/** 번호 마커 + 우리 집 + 선택한 곳까지 점선 (시민 화면) */
export function NumberedPointsLayer({
  points,
  home,
  selectedId,
  onSelect,
}: {
  points: { id: string; lat: number; lon: number; name?: string }[]
  home?: { lat: number; lon: number; label?: string } | null
  selectedId?: string | null
  onSelect?: (id: string) => void
}) {
  const target = points.find((p) => p.id === selectedId) ?? points[0]
  return (
    <>
      {home && target && (
        <Polyline positions={[[home.lat, home.lon], [target.lat, target.lon]]} pathOptions={{ color: '#2f855a', weight: 2.5, dashArray: '6 6', opacity: 0.9 }} />
      )}
      {points.map((p, i) => (
        <Marker key={p.id} position={[p.lat, p.lon]} icon={numberIcon(i + 1, { selected: selectedId === p.id })} eventHandlers={{ click: () => onSelect?.(p.id) }} zIndexOffset={selectedId === p.id ? 500 : 0}>
          {p.name && <Tooltip direction="top">{p.name}</Tooltip>}
        </Marker>
      ))}
      {home && <Marker position={[home.lat, home.lon]} icon={homeIcon(home.label)} zIndexOffset={600} interactive={false} />}
    </>
  )
}
