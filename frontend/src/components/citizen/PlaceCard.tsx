import { useState } from 'react'
import { CalendarPlus, Navigation, Phone } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useSchedule } from '@/features/citizen/schedule'
import { directionsUrl } from '@/features/citizen/share'
import { formatDistance, numberColor } from '@/map/markers'
import { placeDescription, walkMinutes } from '@/features/citizen/places'
import type { FacilitiesPoint } from '@/types/display'

function defaultWhen(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(14, 0, 0, 0)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

export interface PlaceCardProps {
  place: FacilitiesPoint
  number: number
  selected: boolean
  onSelect: () => void
  /** 시설 전화번호 (데이터에 없으면 비활성) */
  phone?: string | null
}

/**
 * 번호 장소 카드. 이름·거리·한 줄 설명만 보이고, 선택된 카드에만 길찾기(채움)·전화·일정 저장(외곽선)이 펼쳐진다.
 * id 는 보여주지 않는다.
 */
export function PlaceCard({ place, number, selected, onSelect, phone }: PlaceCardProps) {
  const { add } = useSchedule()
  const [when, setWhen] = useState(defaultWhen)
  const [scheduling, setScheduling] = useState(false)
  const [saved, setSaved] = useState(false)
  const min = walkMinutes(place.dist_m)

  function save() {
    add({ facilityId: place.id, name: place.name, kind: place.kind, lat: place.lat, lon: place.lon, when: new Date(when).toISOString() })
    setSaved(true)
    setScheduling(false)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <article className={`rounded-card border bg-surface transition-colors ${selected ? 'border-primary' : 'border-line'}`} data-testid="place-card">
      <button type="button" onClick={onSelect} aria-expanded={selected} className="flex w-full items-start gap-3 p-4 text-left">
        <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: numberColor(number) }} aria-hidden>
          {number}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="truncate text-lg font-bold leading-tight text-ink">{place.name}</h3>
            {place.dist_m !== null && (
              <span className="shrink-0 text-sm text-ink-3">
                {formatDistance(place.dist_m)}
                {min && ` · 걸어서 ${min}분`}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-ink-2">{placeDescription(place)}</p>
        </div>
      </button>

      {selected && (
        <div className="px-4 pb-4">
          <div className="grid grid-cols-3 gap-2">
            <a href={directionsUrl(place.name, place.lat, place.lon)} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center justify-center gap-1.5 whitespace-nowrap rounded-btn bg-green px-1 text-[15px] font-semibold text-white hover:brightness-95">
              <Navigation className="big-hide size-4" aria-hidden />
              길찾기
            </a>
            {phone ? (
              <a href={`tel:${phone.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-11 items-center justify-center gap-1.5 whitespace-nowrap rounded-btn border border-green px-1 text-[15px] font-semibold text-green">
                <Phone className="big-hide size-4" aria-hidden />
                전화
              </a>
            ) : (
              <button type="button" disabled title="전화번호 정보가 아직 없어요" className="inline-flex min-h-11 cursor-not-allowed items-center justify-center gap-1.5 whitespace-nowrap rounded-btn border border-line px-1 text-[15px] font-semibold text-ink-3">
                <Phone className="big-hide size-4" aria-hidden />
                전화
              </button>
            )}
            <button type="button" onClick={() => setScheduling((v) => !v)} className="inline-flex min-h-11 items-center justify-center gap-1.5 whitespace-nowrap rounded-btn border border-green px-1 text-[15px] font-semibold text-green">
              <CalendarPlus className="big-hide size-4" aria-hidden />
              {saved ? '저장됨' : '일정 저장'}
            </button>
          </div>
          {scheduling && (
            <div className="mt-3 flex items-end gap-2">
              <label className="min-w-0 flex-1">
                <span className="mb-1 block text-sm font-semibold text-ink-2">언제 가실래요?</span>
                <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="w-full rounded-btn border border-line-strong px-3 py-2.5 text-base" />
              </label>
              <Button onClick={save}>넣기</Button>
            </div>
          )}
        </div>
      )}
    </article>
  )
}
