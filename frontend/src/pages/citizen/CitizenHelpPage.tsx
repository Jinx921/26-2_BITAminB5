import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { CheckCircle2, ChevronLeft } from 'lucide-react'
import { api } from '@/api'
import { CitizenHeader } from '@/components/citizen/CitizenHeader'
import { Button } from '@/components/ui/Button'
import { buttonClass } from '@/components/ui/buttonClass'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useCitizenSession } from '@/features/citizen/useCitizenSession'
import type { SupportRequestType } from '@/types/api'

const TYPE_LABEL: Record<SupportRequestType, { title: string; desc: string }> = {
  companion: { title: '함께 갈 이웃 찾기', desc: '같은 곳에 가는 이웃과 함께 갈 수 있도록 담당자가 연결해 드려요.' },
  mobility: { title: '이동 도움 요청', desc: '혼자 가기 어려우면 차량이나 동행 도움을 요청할 수 있어요.' },
}

function defaultWhen(): string {
  const d = new Date()
  d.setDate(d.getDate() + 2)
  d.setHours(10, 0, 0, 0)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

const input = 'w-full rounded-btn border border-line-strong px-3 py-3 text-lg focus:border-primary focus:outline-none'

/** 지원 요청. 자동 매칭 없이 담당자가 확인한 뒤 연결. 연락처는 동의했을 때만 보낸다 */
export function CitizenHelpPage() {
  const { facilityId = '' } = useParams()
  const [params] = useSearchParams()
  const s = useCitizenSession()
  const place = s.findPlace(decodeURIComponent(facilityId))
  const [type, setType] = useState<SupportRequestType>(params.get('type') === 'mobility' ? 'mobility' : 'companion')
  const [name, setName] = useState('')
  const [contact, setContact] = useState('')
  const [consent, setConsent] = useState(false)
  const [when, setWhen] = useState(defaultWhen)
  const [note, setNote] = useState('')

  const create = useMutation({
    mutationFn: () =>
      api.createSupportRequest({
        facility_id: decodeURIComponent(facilityId),
        requester_name: name.trim(),
        contact: consent ? contact.trim() || null : null,
        contact_consent: consent,
        requested_at: new Date(when).toISOString(),
        request_type: type,
        note: note.trim(),
      }),
  })

  const back = <Link to="/citizen/places" className="inline-flex min-h-11 items-center gap-1 text-base text-ink-2"><ChevronLeft className="size-4" aria-hidden />갈 곳으로</Link>

  if (!place) {
    return (
      <div className="space-y-5">
        <CitizenHeader subtitle={back} />
        <EmptyState title="어느 곳인지 알 수 없어요" description="갈 곳 목록에서 다시 골라 주세요." action={<Link to="/citizen/places" className="font-semibold text-primary">갈 곳 보기</Link>} />
      </div>
    )
  }

  if (create.isSuccess) {
    return (
      <div className="space-y-5">
        <CitizenHeader textToRead="요청을 받았어요. 담당자가 확인한 뒤 연락드릴게요." subtitle={back} />
        <div className="py-8 text-center">
          <CheckCircle2 className="mx-auto size-12 text-green" aria-hidden />
          <p className="mt-3 text-2xl font-bold">요청을 받았어요</p>
          <p className="mt-1 text-base text-ink-2">
            {place.name} · {TYPE_LABEL[type].title}
          </p>
          <p className="mt-3 text-base text-ink-2">담당자가 확인한 뒤 연락드릴게요. 바로 연결되지는 않아요.</p>
          <Link to="/citizen" className={`${buttonClass('fill', 'lg')} mt-6`}>
            처음으로
          </Link>
        </div>
      </div>
    )
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    if (name.trim()) create.mutate()
  }

  return (
    <div className="space-y-5">
      <CitizenHeader textToRead={`${place.name}. ${TYPE_LABEL[type].desc}`} subtitle={back} />
      <div>
        <p className="text-sm text-ink-3">{place.kind}</p>
        <h2 className="text-2xl font-bold">{place.name}</h2>
      </div>
      <form onSubmit={submit} className="space-y-5">
        <div>
          <SegmentedControl fill size="lg" aria-label="요청 종류" value={type} onChange={setType} options={[{ value: 'companion', label: '함께 갈 이웃' }, { value: 'mobility', label: '이동 도움' }]} />
          <p className="mt-2 text-base text-ink-2">{TYPE_LABEL[type].desc}</p>
        </div>
        <label className="block">
          <span className="mb-1 block text-base font-semibold">이름</span>
          <input required value={name} onChange={(e) => setName(e.target.value)} className={input} autoComplete="name" />
        </label>
        <label className="block">
          <span className="mb-1 block text-base font-semibold">언제 가고 싶으세요?</span>
          <input type="datetime-local" required value={when} onChange={(e) => setWhen(e.target.value)} className={input} />
        </label>
        <label className="flex items-start gap-3">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 size-5 accent-primary" />
          <span className="text-base">
            연락처를 담당자에게 알려줘도 괜찮아요
            <span className="block text-sm text-ink-3">동의하지 않으면 연락처는 저장하지 않아요.</span>
          </span>
        </label>
        {consent && (
          <label className="block">
            <span className="mb-1 block text-base font-semibold">연락받을 전화번호</span>
            <input type="tel" value={contact} onChange={(e) => setContact(e.target.value)} className={input} autoComplete="tel" placeholder="010-0000-0000" />
          </label>
        )}
        <label className="block">
          <span className="mb-1 block text-base font-semibold">하고 싶은 말 (선택)</span>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className={input} placeholder="예: 계단이 힘들어요" />
        </label>
        {create.isError && <ErrorState error={create.error} title="요청을 보내지 못했어요" />}
        <Button type="submit" size="lg" className="w-full" loading={create.isPending} disabled={!name.trim()}>
          요청 보내기
        </Button>
      </form>
    </div>
  )
}
