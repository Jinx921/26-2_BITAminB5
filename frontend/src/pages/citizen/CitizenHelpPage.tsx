import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '@/api'
import { A11yBar } from '@/components/citizen/A11yBar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
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

/**
 * 지원 요청 (POST /api/v1/support-requests). 자동 매칭은 없고 담당자가 확인한 뒤 연결한다.
 * 연락처는 동의했을 때만 보낸다.
 */
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

  if (!place) {
    return (
      <div className="space-y-4">
        <A11yBar />
        <EmptyState
          title="어느 곳인지 알 수 없어요"
          description="갈 곳 목록에서 다시 골라 주세요."
          action={
            <Link to="/citizen/places" className="text-lg font-semibold text-blue-700 underline">
              갈 곳 보기
            </Link>
          }
        />
      </div>
    )
  }

  if (create.isSuccess) {
    return (
      <div className="space-y-4">
        <A11yBar textToRead="요청을 받았어요. 담당자가 확인한 뒤 연락드릴게요." />
        <Card className="space-y-3 text-center">
          <p className="text-2xl font-bold">요청을 받았어요</p>
          <p className="text-lg text-slate-700">
            {place.name} · {TYPE_LABEL[type].title}
          </p>
          <p className="text-lg text-slate-700">담당자가 확인한 뒤 연락드릴게요. 바로 연결되지는 않아요.</p>
          <div className="flex justify-center gap-2 pt-2">
            <Link to="/citizen/places" className="inline-flex min-h-14 items-center rounded-xl bg-blue-700 px-5 text-lg font-semibold text-white">
              갈 곳으로 돌아가기
            </Link>
          </div>
        </Card>
      </div>
    )
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    create.mutate()
  }

  return (
    <div className="space-y-4">
      <A11yBar textToRead={`${place.name}. ${TYPE_LABEL[type].desc}`} />
      <Card>
        <p className="text-lg text-slate-600">{place.kind}</p>
        <h1 className="text-2xl font-bold">{place.name}</h1>
      </Card>

      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="요청 종류">
          {(Object.keys(TYPE_LABEL) as SupportRequestType[]).map((t) => (
            <button
              key={t}
              type="button"
              role="radio"
              aria-checked={type === t}
              onClick={() => setType(t)}
              className={`rounded-2xl border p-4 text-left ${type === t ? 'border-blue-700 bg-blue-50' : 'border-slate-300 bg-white'}`}
            >
              <span className="block text-xl font-bold">{TYPE_LABEL[t].title}</span>
            </button>
          ))}
        </div>
        <p className="text-lg text-slate-700">{TYPE_LABEL[type].desc}</p>

        <Card className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">이름</span>
            <input required value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-xl" autoComplete="name" />
          </label>
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">언제 가고 싶으세요?</span>
            <input type="datetime-local" required value={when} onChange={(e) => setWhen(e.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-xl" />
          </label>
          <label className="flex items-start gap-3 rounded-xl bg-slate-50 p-3">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1.5 size-6" />
            <span className="text-lg">
              연락처를 담당자에게 알려줘도 괜찮아요
              <span className="block text-base text-slate-600">동의하지 않으면 연락처는 저장하지 않아요.</span>
            </span>
          </label>
          {consent && (
            <label className="block">
              <span className="mb-1 block text-lg font-semibold">연락받을 전화번호</span>
              <input type="tel" value={contact} onChange={(e) => setContact(e.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-xl" autoComplete="tel" placeholder="010-0000-0000" />
            </label>
          )}
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">하고 싶은 말 (선택)</span>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-xl" placeholder="예: 계단이 힘들어요" />
          </label>
        </Card>

        {create.isError && <ErrorState error={create.error} title="요청을 보내지 못했어요" />}
        <Button type="submit" size="xl" className="w-full" loading={create.isPending} disabled={!name.trim()}>
          요청 보내기
        </Button>
      </form>
    </div>
  )
}
