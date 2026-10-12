import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { PageHeader } from '@/components/ui/PageHeader'
import { Spinner } from '@/components/ui/Spinner'
import { formatDateTime } from '@/lib/datetime'
import { useCellIndex, useFacilityIndex } from '@/lib/geoIndex'
import type { SupportRequestStatus, SupportRequestType } from '@/types/api'

const STATUS_LABEL: Record<SupportRequestStatus, string> = { pending: '대기', approved: '승인', rejected: '반려', completed: '완료' }
const STATUS_STYLE: Record<SupportRequestStatus, string> = {
  pending: 'bg-amber-50 text-amber-800',
  approved: 'bg-blue-50 text-blue-800',
  rejected: 'bg-slate-100 text-slate-600',
  completed: 'bg-emerald-50 text-emerald-800',
}
const TYPE_LABEL: Record<SupportRequestType, string> = { companion: '함께 가기', mobility: '이동 도움' }
const FILTERS: (SupportRequestStatus | 'all')[] = ['pending', 'approved', 'completed', 'rejected', 'all']

/** 시민 요청 목록(상태 변경)과 집계(수요 신호·현장 피드백) */
export function AdminRequestsPage() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<SupportRequestStatus | 'all'>('pending')
  const { index: facilities } = useFacilityIndex()
  const { index: cells } = useCellIndex()

  const list = useQuery({ queryKey: ['support-requests', filter], queryFn: () => api.listSupportRequests(filter === 'all' ? undefined : filter) })
  const signals = useQuery({ queryKey: ['demand-signals'], queryFn: () => api.getDemandSignals() })
  const feedback = useQuery({ queryKey: ['field-feedback-summary'], queryFn: () => api.getFieldFeedbackSummary() })

  const update = useMutation({
    mutationFn: ({ id, status }: { id: number; status: SupportRequestStatus }) => api.updateSupportRequestStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['support-requests'] })
      qc.invalidateQueries({ queryKey: ['demand-signals'] })
    },
  })

  const facName = (id: string) => facilities.get(id)?.name ?? '시설 (이름 확인 중)'

  return (
    <>
      <PageHeader title="시민 요청 목록과 집계" description="함께 가기·이동 도움 요청은 자동 매칭하지 않고 담당자가 확인한 뒤 연결합니다." />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <section className="space-y-3">
          <div className="flex flex-wrap gap-2" role="tablist">
            {FILTERS.map((f) => (
              <button key={f} type="button" role="tab" aria-selected={filter === f} onClick={() => setFilter(f)} className={`rounded-full border px-3 py-1 text-sm font-medium ${filter === f ? 'border-blue-700 bg-blue-700 text-white' : 'border-slate-300 bg-white text-slate-700'}`}>
                {f === 'all' ? '전체' : STATUS_LABEL[f]}
              </button>
            ))}
          </div>
          {list.isPending && <Spinner />}
          {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
          {list.data && list.data.length === 0 && <EmptyState title="요청이 없습니다" description={filter === 'all' ? '아직 들어온 요청이 없습니다.' : `${STATUS_LABEL[filter as SupportRequestStatus]} 상태인 요청이 없습니다.`} />}
          {list.data && list.data.length > 0 && (
            <ul className="space-y-2">
              {list.data.map((r) => (
                <li key={r.id}>
                  <Card className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[r.status]}`}>{STATUS_LABEL[r.status]}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">{TYPE_LABEL[r.request_type]}</span>
                        <span className="font-semibold">{facName(r.facility_id)}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-700">
                        {r.requester_name} · 희망 {formatDateTime(r.requested_at)}
                        {r.contact_consent && r.contact ? ` · ${r.contact}` : ' · 연락처 미동의'}
                      </p>
                      {r.note && <p className="mt-1 text-sm text-slate-600">“{r.note}”</p>}
                      <p className="mt-1 text-xs text-slate-400">접수 {formatDateTime(r.created_at)}</p>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {r.status === 'pending' && (
                        <>
                          <Button size="md" onClick={() => update.mutate({ id: r.id, status: 'approved' })} loading={update.isPending}>
                            승인
                          </Button>
                          <Button size="md" variant="secondary" onClick={() => update.mutate({ id: r.id, status: 'rejected' })} loading={update.isPending}>
                            반려
                          </Button>
                        </>
                      )}
                      {r.status === 'approved' && (
                        <Button size="md" onClick={() => update.mutate({ id: r.id, status: 'completed' })} loading={update.isPending}>
                          완료 처리
                        </Button>
                      )}
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
          {update.isError && <ErrorState error={update.error} title="상태를 바꾸지 못했습니다" />}
        </section>

        <aside className="space-y-4">
          <Card>
            <h2 className="font-semibold">수요 신호 (시설·종류·상태별 건수)</h2>
            <p className="mt-1 text-xs text-slate-500">3건 미만 묶음은 개인 식별을 막기 위해 집계에서 제외됩니다.</p>
            {signals.isPending && <Spinner className="mt-3" />}
            {signals.isError && <ErrorState error={signals.error} onRetry={() => signals.refetch()} />}
            {signals.data && signals.data.length === 0 && <p className="mt-3 text-sm text-slate-600">아직 집계할 만큼 요청이 쌓이지 않았습니다.</p>}
            {signals.data && signals.data.length > 0 && (
              <table className="mt-3 w-full text-sm">
                <thead className="text-left text-slate-500">
                  <tr>
                    <th className="py-1 font-medium">시설</th>
                    <th className="py-1 font-medium">종류</th>
                    <th className="py-1 font-medium">상태</th>
                    <th className="py-1 text-right font-medium">건</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.data.map((s, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="py-1">{facName(s.facility_id)}</td>
                      <td className="py-1">{TYPE_LABEL[s.request_type]}</td>
                      <td className="py-1">{STATUS_LABEL[s.status]}</td>
                      <td className="py-1 text-right tabular-nums">{s.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card>
            <h2 className="font-semibold">현장 피드백 요약 (동네별 확인 횟수)</h2>
            {feedback.isPending && <Spinner className="mt-3" />}
            {feedback.isError && <ErrorState error={feedback.error} onRetry={() => feedback.refetch()} />}
            {feedback.data && feedback.data.length === 0 && <p className="mt-3 text-sm text-slate-600">아직 현장 확인 기록이 없습니다.</p>}
            {feedback.data && feedback.data.length > 0 && (
              <ul className="mt-3 space-y-1 text-sm">
                {feedback.data.map((f) => (
                  <li key={f.cell_id} className="flex justify-between border-t border-slate-100 py-1">
                    <span>{cells.get(f.cell_id)?.emd_name ?? '동네 (이름 확인 중)'}</span>
                    <span className="tabular-nums text-slate-600">{f.checked_count}회 · 응답 항목 {f.checklist_responses?.length ?? 0}개</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </aside>
      </div>
    </>
  )
}
