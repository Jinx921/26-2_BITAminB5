import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { api } from '@/api'
import { FIELD_CHECK_LIST_QUERY_OPTIONS, fieldCheckListQueryKey } from '@/api/fieldCheckListSync'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { Spinner } from '@/components/ui/Spinner'
import { ANSWER_LABEL, ANSWER_OPTIONS, CHECKLIST_ITEMS, SUPPORT_NEEDED_LABEL, SUPPORT_OPTIONS, buildChecklist, keyForQuestion, type ChecklistKey } from '@/features/field/checklist'
import { useDoneCells } from '@/features/field/doneStore'
import { formatDateTime } from '@/lib/datetime'
import { BaseMap, PointsLayer } from '@/map'
import { COLUMN_WIDTH, useViewMode } from '@/features/viewMode'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { ChecklistAnswer, SupportNeededAnswer } from '@/types/api'

/** 동네 하나의 확인 항목. 질문마다 세그먼트 한 줄, 메모 한 칸, 저장은 하단 고정 버튼 하나 */
export function FieldCellPage() {
  const { cellId = '' } = useParams()
  const id = decodeURIComponent(cellId)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuth()
  const { markDone } = useDoneCells()

  const list = useQuery({
    queryKey: fieldCheckListQueryKey(user?.id),
    queryFn: () => api.fetchFieldCheckList(),
    ...FIELD_CHECK_LIST_QUERY_OPTIONS,
  })
  const cell = list.data?.cells.find((c) => c.id === id)
  const history = useQuery({ queryKey: ['field-checks', id], queryFn: () => api.listFieldChecks(id), enabled: !!id })

  const [answers, setAnswers] = useState<Partial<Record<ChecklistKey, ChecklistAnswer>>>({})
  const [support, setSupport] = useState<SupportNeededAnswer | undefined>()
  const [note, setNote] = useState('')
  const [view] = useViewMode()
  const desktop = view === 'desktop'

  const items = useMemo(() => (cell?.questions ?? []).map((q) => ({ question: q, key: keyForQuestion(q) })), [cell])
  const unmatched = items.filter((i) => i.key === null)

  const save = useMutation({
    mutationFn: () =>
      api.createFieldCheck({
        cell_id: id,
        checklist: buildChecklist(answers, support ?? 'unsure'),
        checked_at: new Date().toISOString(),
        note: [note.trim(), unmatched.length ? unmatched.map((u) => `[저장 항목 없음] ${u.question}`).join('\n') : ''].filter(Boolean).join('\n'),
      }),
    onSuccess: () => { markDone(id); qc.invalidateQueries({ queryKey: ['field-checks'] }); navigate('/field') },
  })

  if (list.isPending) return <Spinner className="py-6" />
  if (list.isError) return <ErrorState error={list.error} title="확인 목록을 불러오지 못했습니다" />
  if (!cell) return <EmptyState title="목록에 없는 동네입니다" action={<Link to="/field" className="font-semibold text-primary">확인 목록으로</Link>} />

  const answeredAll = items.every((i) => i.key === null || answers[i.key]) && support !== undefined

  return (
    <div className="space-y-5">
      <Link to="/field" className="inline-flex min-h-11 items-center gap-1 text-base text-ink-2"><ChevronLeft className="size-4" aria-hidden />확인 목록</Link>
      <div className="flex items-center gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white" style={{ background: CHECK_LEVEL_COLOR[cell.level] ?? '#111827' }}>{cell.order}</span>
        <div>
          <h2 className="text-2xl font-bold leading-tight">{cell.emd_name}</h2>
          <p className="text-sm text-ink-3">{cell.level}</p>
        </div>
      </div>
      <div className={desktop ? 'grid gap-8 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]' : 'space-y-5'}>
      <div className={desktop ? 'order-2 space-y-5 md:sticky md:top-4 md:self-start' : 'contents'}>
      <BaseMap bounds={[[cell.lat - 0.004, cell.lon - 0.004], [cell.lat + 0.004, cell.lon + 0.004]]} className={desktop ? 'h-72' : 'h-40'} scrollWheelZoom={desktop}>
        <PointsLayer map={{ layer: 'checks', ref: 'cell', geojson: null, points: [cell] }} />
      </BaseMap>
      {desktop && history.data && history.data.length > 0 && <p className="text-sm text-ink-3">이전 기록 {history.data.length}건은 아래 '이전 기록'에서 볼 수 있습니다.</p>}
      </div>

      <div className="order-1 space-y-5">
      <form id="field-check-form" className="space-y-5" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        {items.map((it, i) => (
          <div key={i}>
            <p className="mb-2 text-base font-semibold">{i + 1}. {it.question}</p>
            {it.key ? (
              <SegmentedControl fill size="lg" aria-label={it.question} options={ANSWER_OPTIONS} value={answers[it.key]} onChange={(v) => setAnswers((a) => ({ ...a, [it.key as ChecklistKey]: v }))} />
            ) : (
              <p className="text-sm text-amber-ink">이 질문은 저장 항목이 정해지지 않아 메모로 함께 저장됩니다.</p>
            )}
          </div>
        ))}
        <div>
          <p className="mb-2 text-base font-semibold">{items.length + 1}. {SUPPORT_NEEDED_LABEL}</p>
          <SegmentedControl fill size="lg" aria-label={SUPPORT_NEEDED_LABEL} options={SUPPORT_OPTIONS} value={support} onChange={setSupport} />
        </div>
        <label className="block">
          <span className="mb-1 block text-base font-semibold">메모 (선택)</span>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="w-full rounded-btn border border-line-strong px-3 py-3 text-base focus:border-primary focus:outline-none" placeholder="현장에서 본 것, 주민 이야기 등. 판정에는 쓰이지 않습니다." />
        </label>
        {save.isError && <ErrorState error={save.error} title="저장하지 못했습니다" />}
      </form>
      </div>
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer font-semibold text-ink-2">이 동네의 이전 기록 {history.data ? `(${history.data.length})` : ''}</summary>
        {history.isPending && <Spinner className="mt-2" />}
        {history.data && history.data.length === 0 && <p className="mt-2 text-ink-3">저장된 기록이 없습니다.</p>}
        {history.data && history.data.length > 0 && (
          <ul className="mt-2 divide-y divide-line">
            {history.data.map((h) => (
              <li key={h.id} className="py-2">
                <p className="text-ink-3">{formatDateTime(h.checked_at)}</p>
                <ul className="mt-1 text-ink-2">
                  {CHECKLIST_ITEMS.map((it) => (h.checklist[it.key] !== 'unknown' ? <li key={it.key}>{it.label} → <b>{ANSWER_LABEL[h.checklist[it.key]]}</b></li> : null))}
                  <li>지원 필요 → <b>{ANSWER_LABEL[h.checklist.support_needed] ?? h.checklist.support_needed}</b></li>
                </ul>
                {h.note && <p className="mt-1 whitespace-pre-line text-ink-2">{h.note}</p>}
              </li>
            ))}
          </ul>
        )}
      </details>

      <div data-fixed-bar className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/95 backdrop-blur">
        <div className={`mx-auto px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] ${COLUMN_WIDTH[view]}`}>
          <Button type="submit" form="field-check-form" size="lg" className="w-full" loading={save.isPending} disabled={!answeredAll}>
            결과 저장
          </Button>
          {!answeredAll && <p className="mt-1 text-center text-xs text-ink-3">모든 질문에 답하면 저장할 수 있습니다.</p>}
        </div>
      </div>
    </div>
  )
}
