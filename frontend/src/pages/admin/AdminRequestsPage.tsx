import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { Spinner } from '@/components/ui/Spinner'
import { formatDateTime } from '@/lib/datetime'
import { useCellIndex, useFacilityIndex } from '@/lib/geoIndex'
import type { SupportRequestStatus, SupportRequestType } from '@/types/api'

const STATUS_LABEL: Record<SupportRequestStatus, string> = { pending: '대기', approved: '승인', rejected: '반려', completed: '완료' }
const STATUS_STYLE: Record<SupportRequestStatus, string> = {
  pending: 'bg-amber-50 text-amber-ink',
  approved: 'bg-primary-soft text-primary',
  rejected: 'bg-canvas text-ink-3',
  completed: 'bg-green-soft text-green',
}
const TYPE_LABEL: Record<SupportRequestType, string> = { companion: '함께 가기', mobility: '이동 도움' }
type Filter = SupportRequestStatus | 'all'

const th = 'py-2 pr-3 text-left text-xs font-medium text-ink-3'
const td = 'py-3 pr-3 align-top text-sm'

/** 시민 요청 목록(표 형태 행)과 집계 */
export function AdminRequestsPage() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<Filter>('pending')
  const { index: facilities } = useFacilityIndex()
  const { index: cells } = useCellIndex()

  const list = useQuery({ queryKey: ['support-requests', filter], queryFn: () => api.listSupportRequests(filter === 'all' ? undefined : filter) })
  const signals = useQuery({ queryKey: ['demand-signals'], queryFn: () => api.getDemandSignals() })
  const feedback = useQuery({ queryKey: ['field-feedback-summary'], queryFn: () => api.getFieldFeedbackSummary() })
  const update = useMutation({
    mutationFn: ({ id, status }: { id: number; status: SupportRequestStatus }) => api.updateSupportRequestStatus(id, status),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['support-requests'] }); qc.invalidateQueries({ queryKey: ['demand-signals'] }) },
  })
  const facName = (id: string) => facilities.get(id)?.name ?? '시설 (이름 확인 중)'

  return (
    <div className="mx-auto grid h-full max-w-7xl gap-8 overflow-y-auto px-6 py-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-bold">시민 요청</h1>
          <SegmentedControl size="sm" aria-label="상태" value={filter} onChange={setFilter} options={[{ value: 'pending', label: '대기' }, { value: 'approved', label: '승인' }, { value: 'completed', label: '완료' }, { value: 'rejected', label: '반려' }, { value: 'all', label: '전체' }]} />
        </div>
        <p className="mb-3 text-sm text-ink-3">함께 가기·이동 도움 요청은 자동 매칭하지 않고 담당자가 확인한 뒤 연결합니다.</p>
        {list.isPending && <Spinner />}
        {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
        {list.data && list.data.length === 0 && <EmptyState title="요청이 없습니다" description={filter === 'all' ? '아직 들어온 요청이 없습니다.' : `${STATUS_LABEL[filter as SupportRequestStatus]} 상태인 요청이 없습니다.`} />}
        {list.data && list.data.length > 0 && (
          <table className="w-full border-t border-line">
            <thead>
              <tr>
                <th className={th}>상태</th>
                <th className={th}>시설 · 종류</th>
                <th className={th}>요청자</th>
                <th className={th}>희망 일시</th>
                <th className={`${th} text-right`}>처리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {list.data.map((r) => (
                <tr key={r.id}>
                  <td className={td}><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[r.status]}`}>{STATUS_LABEL[r.status]}</span></td>
                  <td className={td}>
                    <div className="font-semibold text-ink">{facName(r.facility_id)}</div>
                    <div className="text-xs text-ink-3">{TYPE_LABEL[r.request_type]}{r.note && ` · “${r.note}”`}</div>
                  </td>
                  <td className={td}>
                    <div>{r.requester_name}</div>
                    <div className="text-xs text-ink-3">{r.contact_consent && r.contact ? r.contact : '연락처 미동의'}</div>
                  </td>
                  <td className={td}>
                    <div>{formatDateTime(r.requested_at)}</div>
                    <div className="text-xs text-ink-3">접수 {formatDateTime(r.created_at)}</div>
                  </td>
                  <td className={`${td} text-right`}>
                    {r.status === 'pending' && (
                      <div className="inline-flex gap-1">
                        <Button size="sm" onClick={() => update.mutate({ id: r.id, status: 'approved' })} loading={update.isPending}>승인</Button>
                        <Button size="sm" variant="text" onClick={() => update.mutate({ id: r.id, status: 'rejected' })} disabled={update.isPending}>반려</Button>
                      </div>
                    )}
                    {r.status === 'approved' && <Button size="sm" variant="outline" onClick={() => update.mutate({ id: r.id, status: 'completed' })} loading={update.isPending}>완료 처리</Button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {update.isError && <div className="mt-3"><ErrorState error={update.error} title="상태를 바꾸지 못했습니다" /></div>}
      </section>

      <aside className="space-y-8">
        <section>
          <h2 className="font-bold">수요 신호</h2>
          <p className="mb-2 text-xs text-ink-3">시설·종류·상태별 건수. 3건 미만 묶음은 개인 식별을 막기 위해 제외됩니다.</p>
          {signals.isPending && <Spinner />}
          {signals.isError && <ErrorState error={signals.error} onRetry={() => signals.refetch()} />}
          {signals.data && signals.data.length === 0 && <p className="text-sm text-ink-3">아직 집계할 만큼 요청이 쌓이지 않았습니다.</p>}
          {signals.data && signals.data.length > 0 && (
            <table className="w-full border-t border-line text-sm">
              <thead><tr><th className={th}>시설</th><th className={th}>종류</th><th className={th}>상태</th><th className={`${th} text-right`}>건</th></tr></thead>
              <tbody className="divide-y divide-line">
                {signals.data.map((s, i) => (
                  <tr key={i}><td className="py-2 pr-3">{facName(s.facility_id)}</td><td className="py-2 pr-3">{TYPE_LABEL[s.request_type]}</td><td className="py-2 pr-3">{STATUS_LABEL[s.status]}</td><td className="py-2 text-right tabular-nums">{s.count}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
        <section>
          <h2 className="font-bold">현장 피드백 요약</h2>
          <p className="mb-2 text-xs text-ink-3">동네별 확인 횟수</p>
          {feedback.isPending && <Spinner />}
          {feedback.isError && <ErrorState error={feedback.error} onRetry={() => feedback.refetch()} />}
          {feedback.data && feedback.data.length === 0 && <p className="text-sm text-ink-3">아직 현장 확인 기록이 없습니다.</p>}
          {feedback.data && feedback.data.length > 0 && (
            <table className="w-full border-t border-line text-sm">
              <tbody className="divide-y divide-line">
                {feedback.data.map((f) => (
                  <tr key={f.cell_id}><td className="py-2 pr-3">{cells.get(f.cell_id)?.emd_name ?? '동네 (이름 확인 중)'}</td><td className="py-2 text-right tabular-nums text-ink-2">{f.checked_count}회 · 응답 항목 {f.checklist_responses?.length ?? 0}개</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </aside>
    </div>
  )
}
