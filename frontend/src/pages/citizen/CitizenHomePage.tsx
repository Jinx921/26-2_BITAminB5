import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, MapPin, Phone, Share2 } from 'lucide-react'
import { SAMPLE_QUESTIONS } from '@/api/mock/questions'
import { AskBar } from '@/components/citizen/AskBar'
import { CitizenHeader } from '@/components/citizen/CitizenHeader'
import { HelpPanel } from '@/components/citizen/HelpPanel'
import { LocationSheet } from '@/components/citizen/LocationSheet'
import { PlaceCard } from '@/components/citizen/PlaceCard'
import { WeekStrip } from '@/components/citizen/WeekStrip'
import { Button } from '@/components/ui/Button'
import { buttonClass } from '@/components/ui/buttonClass'
import { ErrorState } from '@/components/ui/ErrorState'
import { REGIONS, regionOf } from '@/config'
import { useCitizenSession } from '@/features/citizen/useCitizenSession'
import { answerToShareText, shareText } from '@/features/citizen/share'
import { FragmentRenderer } from '@/fragments'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { useViewMode } from '@/features/viewMode'
import type { FacilitiesPoint, MapPoint } from '@/types/display'

/** 시민 첫 화면. 시안의 순서: 제목 → 위치 한 줄 → 내 질문 말풍선 → 답 → 지도 → 번호 카드 → 이번 주 → 도움 패널 → 공유·전화 */
export function CitizenHomePage() {
  const s = useCitizenSession()
  const ask = useAskQuestion()
  const [sheet, setSheet] = useState(false)
  const [asked, setAsked] = useState<{ text: string; voice: boolean } | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [view] = useViewMode()
  const desktop = view === 'desktop'

  const submit = useCallback(
    (question: string, viaVoice: boolean) => {
      setAsked({ text: question, voice: viaVoice })
      setSelectedId(null)
      ask.mutate(
        { mode: 'citizen', question, location: s.location ? { lat: s.location.lat, lon: s.location.lon } : undefined },
        { onSuccess: (d) => { s.setAnswer(d); s.setQuestion('') } },
      )
    },
    [ask, s],
  )

  const answer = s.answer
  const ordered = useMemo<FacilitiesPoint[]>(
    () => s.places.slice().sort((a, b) => Number(b.highlight) - Number(a.highlight) || (a.dist_m ?? 1e9) - (b.dist_m ?? 1e9)),
    [s.places],
  )
  const top = ordered.slice(0, 3)
  const selected = top.find((p) => p.id === selectedId) ?? top[0] ?? null
  const region = s.location ? regionOf(s.location.lat, s.location.lon) : top[0] ? regionOf(top[0].lat, top[0].lon) : null
  const phone = region ? REGIONS[region].communityCenterPhone : ''
  const centerName = region ? REGIONS[region].communityCenterName : '주민센터'
  const readText = answer ? answerToShareText(answer) : undefined
  const onSelectPoint = useCallback((p: MapPoint) => setSelectedId(p.id), [])

  return (
    <div className="space-y-6">
      <CitizenHeader
        textToRead={readText}
        subtitle={
          <button type="button" onClick={() => setSheet(true)} data-testid="location-trigger" className="inline-flex min-h-11 max-w-full items-center gap-1 text-base text-ink-2">
            <MapPin className="size-4 text-primary" aria-hidden />
            {s.location ? (
              <span className="truncate">
                {s.location.label} 근처 · <span className="text-primary">위치 사용 중</span>
              </span>
            ) : (
              <span className="truncate font-semibold text-primary">어디 주변을 찾을까요? 위치 고르기</span>
            )}
            <ChevronRight className="size-4 shrink-0 text-ink-3" aria-hidden />
          </button>
        }
      />
      <LocationSheet open={sheet} onClose={() => setSheet(false)} value={s.location} onChange={s.setLocation} />

      {asked && (
        <div className="flex items-end justify-end gap-2">
          {asked.voice && <span className="pb-1 text-xs text-ink-3">음성으로 질문</span>}
          <p className="max-w-[80%] rounded-[18px] rounded-br-[6px] bg-primary px-4 py-3 text-base leading-snug text-white">{asked.text}</p>
        </div>
      )}

      {ask.isPending && (
        <div className="space-y-2" role="status">
          <div className="h-5 w-3/4 animate-pulse rounded bg-canvas" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-canvas" />
          <p className="text-sm text-ink-3">답을 준비하고 있어요. 30초쯤 걸릴 수 있어요.</p>
        </div>
      )}
      {ask.isError && <ErrorState error={ask.error} title="답을 받지 못했어요" />}

      {!answer && !ask.isPending && !asked && (
        <section className="space-y-3">
          <p className="text-lg text-ink-2">가까운 경로당, 도서관, 보건소를 찾아 드려요. 아래에 물어보세요.</p>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.citizen.map((q) => (
              <button key={q} type="button" onClick={() => s.setQuestion(q)} className="rounded-full border border-line-strong bg-surface px-3 py-2 text-sm text-ink-2 hover:bg-canvas">
                {q}
              </button>
            ))}
          </div>
        </section>
      )}

      {answer && !ask.isPending && (
        <div className={desktop ? 'grid gap-8 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]' : 'space-y-6'}>
          <div className="space-y-6">
          <FragmentRenderer
            display={answer}
            mode="citizen"
            context={{ region, selectedPointId: selected?.id ?? null, onSelectPoint, mapClassName: desktop ? 'h-80' : 'h-60', orderedIds: top.map((p) => p.id), home: s.location ? { lat: s.location.lat, lon: s.location.lon, label: '우리 집' } : null, compactDetails: true }}
          />

          {top.length > 0 && (
            <section className="space-y-2" data-testid="place-list">
              {top.map((p, i) => (
                <PlaceCard key={p.id} place={p} number={i + 1} selected={selected?.id === p.id} onSelect={() => setSelectedId(p.id)} />
              ))}
              {ordered.length > top.length && (
                <Link to="/citizen/places" className="inline-flex min-h-11 items-center gap-1 text-base font-semibold text-primary">
                  가까운 곳 {ordered.length}곳 모두 보기 <ChevronRight className="size-4" aria-hidden />
                </Link>
              )}
            </section>
          )}
          </div>

          <div className="space-y-6">
          <WeekStrip />
          <HelpPanel facilityId={selected?.id ?? null} facilityName={selected?.name} />

          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" size="lg" className="whitespace-nowrap px-2 text-[15px]" icon={<Share2 className="big-hide size-5" />} onClick={() => shareText('우리 동네 갈 곳', readText ?? '')}>
              가족에게 공유
            </Button>
            {phone ? (
              <a href={`tel:${phone.replace(/[^\d+]/g, '')}`} className={`${buttonClass('dark', 'lg')} whitespace-nowrap px-2 text-[15px]`}>
                <Phone className="size-5" aria-hidden />
                {centerName}에 전화
              </a>
            ) : (
              <Button variant="dark" size="lg" className="whitespace-nowrap px-2 text-[15px]" icon={<Phone className="big-hide size-5" />} disabled title="전화번호 확인 중">
                주민센터에 전화
              </Button>
            )}
          </div>
          </div>
        </div>
      )}

      <AskBar value={s.question} onChange={s.setQuestion} onSubmit={submit} pending={ask.isPending} />
    </div>
  )
}
