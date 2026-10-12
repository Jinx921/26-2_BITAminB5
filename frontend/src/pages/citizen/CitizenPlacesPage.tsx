import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PlaceCard } from '@/components/citizen/PlaceCard'
import { A11yBar } from '@/components/citizen/A11yBar'
import { EmptyState } from '@/components/ui/EmptyState'
import { regionOf } from '@/config'
import { useCitizenSession } from '@/features/citizen/useCitizenSession'
import { BaseMap, PointsLayer, boundsOfPoints, inServiceArea } from '@/map'
import { FACILITY_KIND_ICON } from '@/map/colors'

/** 마지막 답변의 시설을 지도와 카드로. 종류 필터와 지도-카드 연동 */
export function CitizenPlacesPage() {
  const s = useCitizenSession()
  const [kind, setKind] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  const all = useMemo(() => s.places.filter(inServiceArea), [s.places])
  const kinds = useMemo(() => [...new Set(all.map((p) => p.kind))], [all])
  const shown = useMemo(() => (kind ? all.filter((p) => p.kind === kind) : all).slice().sort((a, b) => (a.dist_m ?? 1e9) - (b.dist_m ?? 1e9)), [all, kind])
  const bounds = useMemo(() => boundsOfPoints(shown), [shown])
  const region = s.location ? regionOf(s.location.lat, s.location.lon) : shown[0] ? regionOf(shown[0].lat, shown[0].lon) : null

  if (all.length === 0) {
    return (
      <div className="space-y-4">
        <A11yBar />
        <EmptyState
          title="아직 찾은 곳이 없어요"
          description="먼저 물어보기에서 위치를 고르고 질문해 주세요."
          action={
            <Link to="/citizen" className="text-lg font-semibold text-blue-700 underline">
              물어보기로 가기
            </Link>
          }
        />
      </div>
    )
  }

  const mapData = s.answer?.map?.layer === 'facilities' ? { ...s.answer.map, points: shown } : null

  return (
    <div className="space-y-4">
      <A11yBar textToRead={shown.map((p) => `${p.name}, ${p.kind}`).join('. ')} />
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="시설 종류">
        <button type="button" role="tab" aria-selected={kind === null} onClick={() => setKind(null)} className={`rounded-full border px-4 py-2 text-lg ${kind === null ? 'border-blue-700 bg-blue-700 text-white' : 'border-slate-300 bg-white'}`}>
          전체 {all.length}
        </button>
        {kinds.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={kind === k} onClick={() => setKind(k)} className={`rounded-full border px-4 py-2 text-lg ${kind === k ? 'border-blue-700 bg-blue-700 text-white' : 'border-slate-300 bg-white'}`}>
            {FACILITY_KIND_ICON[k] ?? ''} {k}
          </button>
        ))}
      </div>
      {mapData && (
        <BaseMap bounds={bounds} region={region} className="h-72" scrollWheelZoom={false}>
          <PointsLayer map={mapData} selectedId={selected} onSelect={(p) => setSelected(p.id)} />
        </BaseMap>
      )}
      <div className="space-y-3">
        {shown.map((p) => (
          <PlaceCard key={p.id} place={p} selected={selected === p.id} onSelect={() => setSelected(p.id)} />
        ))}
      </div>
    </div>
  )
}
