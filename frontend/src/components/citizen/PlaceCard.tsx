import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { useSchedule } from '@/features/citizen/schedule'
import { directionsUrl } from '@/features/citizen/share'
import { FACILITY_KIND_ICON } from '@/map/colors'
import { formatDistance } from '@/map/markers'
import type { FacilitiesPoint } from '@/types/display'

function defaultWhen(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(14, 0, 0, 0)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

/**
 * 시설 카드. id 는 보여주지 않고 링크·요청 키로만 쓴다.
 * 시설 전화번호는 데이터에 없어 카드에는 전화 버튼이 없다 (주민센터 전화는 화면 하단에 따로).
 */
export function PlaceCard({ place, selected, onSelect }: { place: FacilitiesPoint; selected?: boolean; onSelect?: () => void }) {
  const { add } = useSchedule()
  const [open, setOpen] = useState(false)
  const [when, setWhen] = useState(defaultWhen)
  const [saved, setSaved] = useState(false)

  function save() {
    add({ facilityId: place.id, name: place.name, kind: place.kind, lat: place.lat, lon: place.lon, when: new Date(when).toISOString() })
    setSaved(true)
    setOpen(false)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <article
      className={`rounded-2xl border bg-white p-4 shadow-sm ${selected ? 'border-sky-500 ring-2 ring-sky-200' : place.highlight ? 'border-slate-800' : 'border-slate-200'}`}
      onClick={onSelect}
    >
      <div className="flex items-start gap-3">
        <span className="text-3xl" aria-hidden>
          {FACILITY_KIND_ICON[place.kind] ?? '📍'}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-xl font-bold leading-tight">{place.name}</h3>
          <p className="mt-1 text-lg text-slate-600">
            {place.kind}
            {place.dist_m !== null && <> · 약 {formatDistance(place.dist_m)}</>}
          </p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <a
          href={directionsUrl(place.name, place.lat, place.lon)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-14 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 text-lg font-semibold text-slate-900 hover:bg-slate-100"
        >
          길찾기
        </a>
        <Button size="lg" variant="secondary" onClick={(e) => { e.stopPropagation(); setOpen((v) => !v) }}>
          {saved ? '저장됐어요' : '일정 저장'}
        </Button>
        <Link
          to={`/citizen/help/${encodeURIComponent(place.id)}?type=companion`}
          className="inline-flex min-h-14 items-center justify-center rounded-xl bg-blue-700 px-4 text-lg font-semibold text-white hover:bg-blue-800"
        >
          함께 갈 이웃 찾기
        </Link>
        <Link
          to={`/citizen/help/${encodeURIComponent(place.id)}?type=mobility`}
          className="inline-flex min-h-14 items-center justify-center rounded-xl bg-blue-700 px-4 text-lg font-semibold text-white hover:bg-blue-800"
        >
          이동 도움 요청
        </Link>
      </div>
      {open && (
        <div className="mt-3 flex flex-wrap items-end gap-2 rounded-xl bg-slate-50 p-3" onClick={(e) => e.stopPropagation()}>
          <label className="flex-1">
            <span className="mb-1 block text-base font-medium">언제 가실래요?</span>
            <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-3 text-lg" />
          </label>
          <Button size="lg" onClick={save}>
            이번 주 일정에 넣기
          </Button>
        </div>
      )}
    </article>
  )
}
