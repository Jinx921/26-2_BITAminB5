import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { CitizenHeader } from '@/components/citizen/CitizenHeader'
import { HelpPanel } from '@/components/citizen/HelpPanel'
import { PlaceCard } from '@/components/citizen/PlaceCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { regionOf } from '@/config'
import { useCitizenSession } from '@/features/citizen/useCitizenSession'
import { BaseMap, NumberedPointsLayer, boundsOfPoints, inServiceArea } from '@/map'
import { useViewMode } from '@/features/viewMode'

/** 마지막 답변의 시설 전체. 종류 필터 + 번호 지도 + 카드 */
export function CitizenPlacesPage() {
  const s = useCitizenSession()
  const [kind, setKind] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [view] = useViewMode()
  const desktop = view === 'desktop'

  const all = useMemo(() => s.places.filter(inServiceArea).slice().sort((a, b) => Number(b.highlight) - Number(a.highlight) || (a.dist_m ?? 1e9) - (b.dist_m ?? 1e9)), [s.places])
  const kinds = useMemo(() => [...new Set(all.map((p) => p.kind))], [all])
  const shown = useMemo(() => (kind ? all.filter((p) => p.kind === kind) : all), [all, kind])
  const home = useMemo(() => (s.location ? { lat: s.location.lat, lon: s.location.lon, label: '우리 집' } : null), [s.location])
  const bounds = useMemo(() => boundsOfPoints([...shown, ...(home ? [home] : [])]), [shown, home])
  const region = home ? regionOf(home.lat, home.lon) : shown[0] ? regionOf(shown[0].lat, shown[0].lon) : null
  const selected = shown.find((p) => p.id === selectedId) ?? shown[0] ?? null

  return (
    <div className="space-y-5">
      <CitizenHeader textToRead={shown.map((p) => `${p.name}, ${p.kind}`).join('. ') || undefined} subtitle={<Link to="/citizen" className="inline-flex min-h-11 items-center gap-1 text-base text-ink-2"><ChevronLeft className="size-4" aria-hidden />물어보기로</Link>} />
      {all.length === 0 ? (
        <EmptyState title="아직 찾은 곳이 없어요" description="먼저 위치를 고르고 질문해 주세요." action={<Link to="/citizen" className="font-semibold text-primary">물어보기로 가기</Link>} />
      ) : (
        <>
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="시설 종류">
            {[null, ...kinds].map((k) => (
              <button key={k ?? 'all'} type="button" role="tab" aria-selected={kind === k} onClick={() => { setKind(k); setSelectedId(null) }} className={`min-h-11 rounded-full border px-4 text-base font-semibold ${kind === k ? 'border-primary bg-primary text-white' : 'border-line-strong bg-surface text-ink-2'}`}>
                {k ?? `전체 ${all.length}`}
              </button>
            ))}
          </div>
          <div className={desktop ? 'grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]' : 'space-y-5'}>
            <div className={desktop ? 'md:sticky md:top-4 md:self-start' : ''}>
              <BaseMap bounds={bounds} region={region} className={desktop ? 'h-[32rem]' : 'h-64'} scrollWheelZoom={desktop}>
                <NumberedPointsLayer points={shown} home={home} selectedId={selected?.id} onSelect={setSelectedId} />
              </BaseMap>
            </div>
            <div className="space-y-5">
              <div className="space-y-2">
                {shown.map((p, i) => (
                  <PlaceCard key={p.id} place={p} number={i + 1} selected={selected?.id === p.id} onSelect={() => setSelectedId(p.id)} />
                ))}
              </div>
              <HelpPanel facilityId={selected?.id ?? null} facilityName={selected?.name} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
