import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, describeError } from '@/api'
import { SAMPLE_QUESTIONS } from '@/api/mock/questions'
import { QuestionBox } from '@/components/QuestionBox'
import { RegionTabs } from '@/components/map/RegionTabs'
import { TypeLegend } from '@/components/map/TypeLegend'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { PageHeader } from '@/components/ui/PageHeader'
import { Spinner } from '@/components/ui/Spinner'
import { Button } from '@/components/ui/Button'
import { REGION_KEYS, regionOf, type RegionKey } from '@/config'
import { displayToFieldCheckList } from '@/features/admin/fieldList'
import { FragmentRenderer } from '@/fragments'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { BaseMap, GridLayer, PointsLayer, applyFieldOverrides, computeFieldOverrides, useTypesLayer } from '@/map'
import { TYPE_ORDER } from '@/map/colors'
import type { IsolationType, MapPoint } from '@/types/display'

/**
 * 관리자 메인: 동네 유형 지도(GeoJSON 전체 색칠) + 질문창 + 응답 조각.
 * 응답 지도 점은 메인 지도 위에 겹쳐 그리고, 언급된 동네 칸은 굵은 테두리로 강조한다.
 */
export function AdminHomePage() {
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [visible, setVisible] = useState<Set<IsolationType>>(new Set(TYPE_ORDER))
  const [showExcluded, setShowExcluded] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const grid = useTypesLayer(region)
  const ask = useAskQuestion()
  const display = ask.data ?? null
  const navigate = useNavigate()
  const sendList = useMutation({
    mutationFn: async () => {
      const list = display ? displayToFieldCheckList(display) : null
      if (!list) throw new Error('이 답변에는 현장 확인 동네가 없습니다.')
      return api.publishFieldCheckList(list)
    },
    onSuccess: () => navigate('/admin/field-list'),
  })

  // ⚠️ 임시: 현장 기록으로 판정 덮어쓰기 (map/applyFieldOverrides.ts 참고). 백엔드가 반영하면 이 조회는 뺀다
  const checkedCells = useMemo(() => {
    const ids = new Set<string>()
    if (display?.map?.layer === 'types' || display?.map?.layer === 'checks') display.map.points.forEach((p) => ids.add(p.id))
    return [...ids]
  }, [display])
  const fieldChecks = useQuery({
    queryKey: ['field-checks', 'for-map', checkedCells],
    enabled: checkedCells.length > 0,
    queryFn: async () => (await Promise.all(checkedCells.map((id) => api.listFieldChecks(id).catch(() => [])))).flat(),
  })
  const overrides = useMemo(() => computeFieldOverrides(fieldChecks.data ?? []), [fieldChecks.data])
  const gridData = useMemo(() => (grid.data ? applyFieldOverrides(grid.data, overrides, { showExcluded }) : null), [grid.data, overrides, showExcluded])

  const counts = useMemo(() => {
    const c: Partial<Record<IsolationType, number>> = {}
    gridData?.features.forEach((f) => {
      const t = f.properties.type ?? '관찰형'
      c[t] = (c[t] ?? 0) + 1
    })
    return c
  }, [gridData])

  // 답변에서 언급한 동네 (highlight) 칸 강조
  const highlightIds = useMemo(() => {
    const s = new Set<string>()
    const m = display?.map
    if (m && m.layer !== 'facilities') m.points.forEach((p) => p.highlight && s.add(p.id))
    return s
  }, [display])

  function onSelectPoint(p: MapPoint) {
    setSelectedId(p.id)
  }

  function submit(question: string) {
    setSelectedId(null)
    // 질문에 지역 이름이 있으면 지도도 그 지역으로
    for (const r of REGION_KEYS) if (question.includes(r)) setRegion(r)
    ask.mutate({ mode: 'admin', question })
  }

  // 응답의 첫 점으로 지역을 맞춘다 (질문에 지역명이 없을 때)
  const answerRegion = useMemo(() => {
    const p = display?.map?.points?.[0]
    return p ? regionOf(p.lat, p.lon) : null
  }, [display])
  const effectiveRegion = answerRegion ?? region

  return (
    <>
      <PageHeader title="동네 유형 지도와 질문" description="250m 칸을 네 가지 유형으로 색칠합니다. 질문하면 답변에서 언급한 동네가 지도에 강조됩니다." actions={<RegionTabs value={effectiveRegion} onChange={setRegion} />} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <TypeLegend counts={counts} visible={visible} onToggle={(t) => setVisible((prev) => { const n = new Set(prev); if (n.has(t)) n.delete(t); else n.add(t); return n })} />
            {overrides.size > 0 && (
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" checked={showExcluded} onChange={(e) => setShowExcluded(e.target.checked)} />
                현장 확인으로 제외된 곳 보기
              </label>
            )}
          </div>

          {grid.isPending && <Spinner label="지도를 불러오는 중" />}
          {grid.isError && <ErrorState error={grid.error} onRetry={() => grid.refetch()} title="지도 파일을 불러오지 못했습니다" />}
          {gridData && (
            <BaseMap region={effectiveRegion} className="h-[32rem]">
              <GridLayer data={gridData} variant="types" visibleTypes={visible} highlightIds={highlightIds} selectedId={selectedId} onSelect={(p) => setSelectedId(p.cell_id)} />
              {display?.map && display.map.layer !== 'types' && <PointsLayer map={display.map} selectedId={selectedId} onSelect={onSelectPoint} />}
            </BaseMap>
          )}
          {overrides.size > 0 && (
            <p className="text-xs text-slate-500">현장 확인 기록 {overrides.size}곳이 지도에 반영되었습니다 (임시: 프론트 계산, 답변 속 숫자에는 반영되지 않음).</p>
          )}
        </section>

        <section className="space-y-4">
          <Card>
            <QuestionBox onSubmit={submit} pending={ask.isPending} placeholder="예: 춘천에서 어디부터 확인해야 해?" samples={SAMPLE_QUESTIONS.admin.slice(0, 6)} />
          </Card>

          {ask.isError && <ErrorState error={ask.error} title="답변을 받지 못했습니다" />}
          {ask.isPending && (
            <Card>
              <Spinner label="에이전트가 분석 중입니다" />
            </Card>
          )}
          {display && !ask.isPending && (
            <Card className="space-y-4">
              <FragmentRenderer display={display} mode="admin" context={{ region: effectiveRegion, selectedPointId: selectedId, onSelectPoint, mapClassName: 'h-64' }} />
              {display.map?.layer === 'checks' && (
                <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
                  <Button onClick={() => sendList.mutate()} loading={sendList.isPending}>
                    이 목록을 현장 담당자에게 보내기
                  </Button>
                  <span className="text-sm text-slate-500">{display.map.points.length}곳 · 현장 확인 목록 화면에서 복사·내려받기도 할 수 있습니다</span>
                </div>
              )}
              {sendList.isError && <ErrorState error={sendList.error} title="보내지 못했습니다" />}
            </Card>
          )}
          {!display && !ask.isPending && !ask.isError && (
            <EmptyState title="질문을 입력해 보세요" description="어디부터 확인할지, 이동형 거점은 어디가 좋을지, 제안서 초안까지 물어볼 수 있습니다." />
          )}
          {ask.isError && <p className="sr-only">{describeError(ask.error)}</p>}
        </section>
      </div>
    </>
  )
}
