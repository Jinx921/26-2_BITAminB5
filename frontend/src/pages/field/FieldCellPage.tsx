import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '@/api'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import {
  ANSWER_LABEL,
  ANSWER_OPTIONS,
  CHECKLIST_ITEMS,
  SUPPORT_NEEDED_LABEL,
  SUPPORT_OPTIONS,
  buildChecklist,
  keyForQuestion,
  type ChecklistKey,
} from '@/features/field/checklist'
import { useDoneCells } from '@/features/field/doneStore'
import { formatDateTime } from '@/lib/datetime'
import { BaseMap, PointsLayer } from '@/map'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { ChecklistAnswer, SupportNeededAnswer } from '@/types/api'

function OptionRow<T extends string>({ options, value, onChange, name }: { options: { value: T; label: string }[]; value: T | undefined; onChange: (v: T) => void; name: string }) {
  return (
    <div role="radiogroup" aria-label={name} className="grid grid-cols-3 gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`min-h-14 rounded-xl border px-2 text-lg font-semibold ${value === o.value ? 'border-blue-700 bg-blue-700 text-white' : 'border-slate-300 bg-white text-slate-800'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/**
 * 동네 하나의 확인 항목에 답하고 저장한다 (POST /api/v1/field-checks).
 * 에이전트가 준 질문만 보여주고, '지원 필요 여부'는 모든 동네에서 묻는다 (현장기록_규격 3절).
 * cell_id 는 화면에 쓰지 않는다.
 */
export function FieldCellPage() {
  const { cellId = '' } = useParams()
  const id = decodeURIComponent(cellId)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { markDone } = useDoneCells()

  const list = useQuery({ queryKey: ['field-check-list'], queryFn: () => api.fetchFieldCheckList() })
  const cell = list.data?.cells.find((c) => c.id === id)
  const history = useQuery({ queryKey: ['field-checks', id], queryFn: () => api.listFieldChecks(id), enabled: !!id })

  const [answers, setAnswers] = useState<Partial<Record<ChecklistKey, ChecklistAnswer>>>({})
  const [support, setSupport] = useState<SupportNeededAnswer | undefined>()
  const [note, setNote] = useState('')

  // 에이전트 질문 → 저장 키. 매칭 안 되는 질문은 메모로만 남긴다
  const items = useMemo(() => {
    const qs = cell?.questions ?? []
    return qs.map((q) => ({ question: q, key: keyForQuestion(q) }))
  }, [cell])
  const unmatched = items.filter((i) => i.key === null)

  const save = useMutation({
    mutationFn: () => {
      const extra = unmatched.length ? unmatched.map((u) => `[저장 항목 없음] ${u.question}`).join('\n') : ''
      return api.createFieldCheck({
        cell_id: id,
        checklist: buildChecklist(answers, support ?? 'unsure'),
        checked_at: new Date().toISOString(),
        note: [note.trim(), extra].filter(Boolean).join('\n'),
      })
    },
    onSuccess: () => {
      markDone(id)
      qc.invalidateQueries({ queryKey: ['field-checks'] })
      navigate('/field')
    },
  })

  if (list.isPending) return <Spinner className="p-4" />
  if (!cell) {
    return (
      <EmptyState
        title="목록에 없는 동네입니다"
        action={
          <Link to="/field" className="text-lg font-semibold text-blue-700 underline">
            확인 목록으로
          </Link>
        }
      />
    )
  }

  const answeredAll = items.every((i) => i.key === null || answers[i.key]) && support !== undefined

  return (
    <div className="space-y-4">
      <Link to="/field" className="text-lg text-blue-700">
        ‹ 확인 목록
      </Link>
      <Card className="flex items-center gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white" style={{ background: CHECK_LEVEL_COLOR[cell.level] ?? '#334155' }}>
          {cell.order}
        </span>
        <div>
          <h1 className="text-2xl font-bold">{cell.emd_name}</h1>
          <p className="text-base text-slate-600">{cell.level}</p>
        </div>
      </Card>

      <BaseMap bounds={[[cell.lat - 0.004, cell.lon - 0.004], [cell.lat + 0.004, cell.lon + 0.004]]} className="h-48" scrollWheelZoom={false}>
        <PointsLayer map={{ layer: 'checks', ref: 'cell', geojson: null, points: [cell] }} />
      </BaseMap>

      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        {items.map((it, i) => (
          <Card key={i} className="space-y-3">
            <p className="text-lg font-semibold">
              {i + 1}. {it.question}
            </p>
            {it.key ? (
              <OptionRow name={it.question} options={ANSWER_OPTIONS} value={answers[it.key]} onChange={(v) => setAnswers((a) => ({ ...a, [it.key as ChecklistKey]: v }))} />
            ) : (
              <p className="text-sm text-amber-800">이 질문은 저장 항목이 정해지지 않아 메모로 함께 저장됩니다.</p>
            )}
          </Card>
        ))}

        <Card className="space-y-3 border-blue-200">
          <p className="text-lg font-semibold">
            {items.length + 1}. {SUPPORT_NEEDED_LABEL}
          </p>
          <OptionRow name={SUPPORT_NEEDED_LABEL} options={SUPPORT_OPTIONS} value={support} onChange={setSupport} />
        </Card>

        <Card>
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">메모 (선택)</span>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} className="w-full rounded-xl border border-slate-300 px-3 py-3 text-lg" placeholder="현장에서 본 것, 주민 이야기 등. 판정에는 쓰이지 않습니다." />
          </label>
        </Card>

        {save.isError && <ErrorState error={save.error} title="저장하지 못했습니다" />}
        <Button type="submit" size="xl" className="w-full" loading={save.isPending} disabled={!answeredAll}>
          결과 저장
        </Button>
        {!answeredAll && <p className="text-center text-sm text-slate-500">모든 질문에 답하면 저장할 수 있습니다.</p>}
      </form>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer font-semibold">이 동네의 이전 기록 {history.data ? `(${history.data.length})` : ''}</summary>
        {history.isPending && <Spinner className="mt-2" />}
        {history.data && history.data.length === 0 && <p className="mt-2 text-slate-600">저장된 기록이 없습니다.</p>}
        {history.data && history.data.length > 0 && (
          <ul className="mt-2 space-y-2 text-sm">
            {history.data.map((h) => (
              <li key={h.id} className="rounded-xl bg-slate-50 p-3">
                <p className="text-slate-500">{formatDateTime(h.checked_at)}</p>
                <ul className="mt-1">
                  {CHECKLIST_ITEMS.map((it) =>
                    h.checklist[it.key] !== 'unknown' ? (
                      <li key={it.key}>
                        {it.label} → <b>{ANSWER_LABEL[h.checklist[it.key]]}</b>
                      </li>
                    ) : null,
                  )}
                  <li>
                    지원 필요 → <b>{ANSWER_LABEL[h.checklist.support_needed] ?? h.checklist.support_needed}</b>
                  </li>
                </ul>
                {h.note && <p className="mt-1 whitespace-pre-line text-slate-700">{h.note}</p>}
              </li>
            ))}
          </ul>
        )}
      </details>
    </div>
  )
}
