import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { QuestionBox } from '@/components/QuestionBox'
import { A11yBar } from '@/components/citizen/A11yBar'
import { LocationPicker } from '@/components/citizen/LocationPicker'
import { PlaceCard } from '@/components/citizen/PlaceCard'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { ErrorState } from '@/components/ui/ErrorState'
import { REGIONS, regionOf } from '@/config'
import { useSpeechInput } from '@/features/citizen/a11y'
import { useCitizenSession } from '@/features/citizen/useCitizenSession'
import { answerToShareText, shareText } from '@/features/citizen/share'
import { FragmentRenderer } from '@/fragments'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { SAMPLE_QUESTIONS } from '@/api/mock/questions'

/** 시민 첫 화면: 위치 고르기 → 질문(음성 포함) → 답변과 장소 카드 */
export function CitizenHomePage() {
  const s = useCitizenSession()
  const ask = useAskQuestion()
  const speech = useSpeechInput(useCallback((t: string) => s.setQuestion(t), [s]))

  function submit(question: string) {
    s.setQuestion(question)
    ask.mutate(
      { mode: 'citizen', question, location: s.location ? { lat: s.location.lat, lon: s.location.lon } : undefined },
      { onSuccess: (d) => s.setAnswer(d) },
    )
  }

  const answer = s.answer
  const readText = answer ? answerToShareText(answer) : undefined
  const region = s.location ? regionOf(s.location.lat, s.location.lon) : null
  const phone = region ? REGIONS[region].communityCenterPhone : ''
  const centerName = region ? REGIONS[region].communityCenterName : '주민센터'

  return (
    <div className="space-y-5">
      <A11yBar textToRead={readText} />

      <Card>
        <LocationPicker value={s.location} onChange={s.setLocation} />
      </Card>

      <Card>
        <QuestionBox
          size="lg"
          value={s.question}
          onChange={s.setQuestion}
          onSubmit={submit}
          pending={ask.isPending}
          placeholder="예: 어머니 댁 근처에 다니실 만한 곳 있어요?"
          samples={SAMPLE_QUESTIONS.citizen}
          extra={
            speech.supported ? (
              <Button
                type="button"
                size="xl"
                variant={speech.listening ? 'danger' : 'secondary'}
                onClick={() => (speech.listening ? speech.stop() : speech.start())}
                aria-label={speech.listening ? '말하기 멈추기' : '말로 물어보기'}
                title="말로 물어보기"
              >
                {speech.listening ? '듣는 중…' : '🎤'}
              </Button>
            ) : undefined
          }
        />
        {speech.error && <p className="mt-2 text-amber-800">{speech.error}</p>}
        {!s.location && <p className="mt-2 text-slate-600">위치를 먼저 고르면 가까운 곳을 알려드릴 수 있어요.</p>}
      </Card>

      {ask.isError && <ErrorState error={ask.error} title="답을 받지 못했어요" />}

      {answer && !ask.isPending && (
        <>
          <Card className="space-y-4">
            <FragmentRenderer display={answer} mode="citizen" context={{ region, mapClassName: 'h-64' }} />
            <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-4">
              <Button size="lg" variant="secondary" onClick={() => shareText('우리 동네 갈 곳', readText ?? '')}>
                가족에게 공유
              </Button>
              {phone && (
                <a href={`tel:${phone.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-14 items-center justify-center rounded-xl border border-slate-300 bg-white px-5 text-lg font-semibold">
                  {centerName}에 전화
                </a>
              )}
            </div>
          </Card>

          {s.places.length > 0 && (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">가까운 곳 {s.places.length}곳</h2>
                <Link to="/citizen/places" className="text-lg font-semibold text-blue-700 underline">
                  지도로 보기
                </Link>
              </div>
              {s.places
                .slice()
                .sort((a, b) => Number(b.highlight) - Number(a.highlight) || (a.dist_m ?? 1e9) - (b.dist_m ?? 1e9))
                .slice(0, 4)
                .map((p) => (
                  <PlaceCard key={p.id} place={p} />
                ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
