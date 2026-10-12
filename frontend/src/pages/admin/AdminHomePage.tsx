import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Send } from 'lucide-react'
import { api } from '@/api'
import { SAMPLE_QUESTIONS } from '@/api/mock/questions'
import { QuestionBox } from '@/components/QuestionBox'
import { RegionTabs } from '@/components/map/RegionTabs'
import { TypeLegend } from '@/components/map/TypeLegend'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { REGION_KEYS, regionOf, type RegionKey } from '@/config'
import { displayToFieldCheckList } from '@/features/admin/fieldList'
import { FragmentRenderer } from '@/fragments'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { BaseMap, GridLayer, PointsLayer, applyFieldOverrides, computeFieldOverrides, useTypesLayer } from '@/map'
import { TYPE_ORDER } from '@/map/colors'
import type { GridCollection } from '@/types/geo'
import type { IsolationType, MapPoint } from '@/types/display'

function gridBounds(g: GridCollection): [[number, number], [number, number]] | null {
  let s = Infinity, n = -Infinity, w = Infinity, e = -Infinity
  for (const f of g.features) for (const [lon, lat] of f.geometry.coordinates[0] ?? []) { s = Math.min(s, lat); n = Math.max(n, lat); w = Math.min(w, lon); e = Math.max(e, lon) }
  return Number.isFinite(s) ? [[s, w], [n, e]] : null
}

/** 관리자 메인: 왼쪽은 화면을 채우는 유형 지도, 오른쪽은 420px 질문·응답 패널 */
export function AdminHomePage() {
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [visible, setVisible] = useState<Set<IsolationType>>(new Set(TYPE_ORDER))
  const [showExcluded, setShowExcluded] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const navigate = useNavigate()

  const grid = useTypesLayer(region)
  const ask = useAskQuestion()
  const display = ask.data ?? null

  const sendList = useMutation({
    mutationFn: async () => {
      const list = display ? displayToFieldCheckList(display) : null
      if (!list) throw new Error('이 답변에는 현장 확인 동네가 없습니다.')
      return api.publishFieldCheckList(list)
    },
    onSuccess: () => navigate('/admin/field-list'),
  })

  // ⚠️ 임시: 현장 기록으로 판정 덮어쓰기 (map/applyFieldOverrides.ts). 백엔드가 반영하면 이 조회는 뺀다
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
  const bounds = useMemo(() => (grid.data ? gridBounds(grid.data) : null), [grid.data])

  const counts = useMemo(() => {
    const c: Partial<Record<IsolationType, number>> = {}
    gridData?.features.forEach((f) => { const t = f.properties.type ?? '관찰형'; c[t] = (c[t] ?? 0) + 1 })
    return c
  }, [gridData])

  const highlightIds = useMemo(() => {
    const s = new Set<string>()
    const m = display?.map
    if (m && m.layer !== 'facilities') m.points.forEach((p) => p.highlight && s.add(p.id))
    return s
  }, [display])

  const onSelectPoint = (p: MapPoint) => setSelectedId(p.id)
  function submit(question: string) {
    setSelectedId(null)
    for (const r of REGION_KEYS) if (question.includes(r)) setRegion(r)
    ask.mutate({ mode: 'admin', question })
  }
  const answerRegion = useMemo(() => { const p = display?.map?.points?.[0]; return p ? regionOf(p.lat, p.lon) : null }, [display])
  const effectiveRegion = answerRegion ?? region

  return (
    <div className="flex h-full">
      {/* 지도 */}
      <section className="relative min-w-0 flex-1">
        {grid.isPending && <div className="absolute inset-0 z-10 flex items-center justify-center bg-surface/60"><Spinner label="지도를 불러오는 중" /></div>}
        {grid.isError && <div className="p-4"><ErrorState error={grid.error} onRetry={() => grid.refetch()} title="지도 파일을 불러오지 못했습니다" /></div>}
        {gridData && (
          <BaseMap bounds={bounds} region={effectiveRegion} className="h-full rounded-none border-0" zoomPosition="topright">
            <GridLayer data={gridData} variant="types" visibleTypes={visible} highlightIds={highlightIds} selectedId={selectedId} onSelect={(p) => setSelectedId(p.cell_id)} />
            {display?.map && display.map.layer !== 'types' && <PointsLayer map={display.map} selectedId={selectedId} onSelect={onSelectPoint} />}
          </BaseMap>
        )}
        <div className="absolute left-3 top-3 z-[1000]">
          <RegionTabs value={effectiveRegion} onChange={setRegion} />
        </div>
        <div className="absolute bottom-6 left-3 z-[1000] w-44 space-y-2">
          <TypeLegend counts={counts} visible={visible} onToggle={(t) => setVisible((prev) => { const n = new Set(prev); if (n.has(t)) n.delete(t); else n.add(t); return n })} />
          {overrides.size > 0 && (
            <label className="flex items-center gap-2 rounded-btn border border-line bg-surface/95 px-2 py-1.5 text-xs text-ink-2 shadow-card">
              <input type="checkbox" checked={showExcluded} onChange={(e) => setShowExcluded(e.target.checked)} className="accent-primary" />
              현장 확인으로 제외된 곳 보기
            </label>
          )}
        </div>
      </section>

      {/* 패널 */}
      <aside className="flex w-[420px] shrink-0 flex-col border-l border-line">
        <div className="border-b border-line p-4">
          <QuestionBox onSubmit={submit} pending={ask.isPending} placeholder="예: 춘천에서 어디부터 확인해야 해?" samples={display || ask.isPending ? undefined : SAMPLE_QUESTIONS.admin.slice(0, 6)} />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {ask.isError && <ErrorState error={ask.error} title="답변을 받지 못했습니다" />}
          {ask.isPending && <Spinner label="에이전트가 분석 중입니다" />}
          {display && !ask.isPending && (
            <div className="space-y-4">
              <FragmentRenderer display={display} mode="admin" context={{ region: effectiveRegion, selectedPointId: selectedId, onSelectPoint, hideMap: true }} />
              {display.map?.layer === 'checks' && (
                <div className="border-t border-line pt-3">
                  <Button icon={<Send className="size-4" />} onClick={() => sendList.mutate()} loading={sendList.isPending}>
                    현장 담당자에게 보내기
                  </Button>
                  <p className="mt-1 text-xs text-ink-3">{display.map.points.length}곳. 현장 확인 목록 탭에서 복사·내려받기도 할 수 있습니다.</p>
                  {sendList.isError && <ErrorState error={sendList.error} title="보내지 못했습니다" />}
                </div>
              )}
              {overrides.size > 0 && <p className="text-xs text-ink-3">현장 확인 기록 {overrides.size}곳이 지도에 반영됨 (임시: 프론트 계산, 답변 속 숫자에는 반영되지 않음).</p>}
            </div>
          )}
          {!display && !ask.isPending && !ask.isError && (
            <div className="pt-6 text-sm text-ink-3">
              <p className="font-semibold text-ink-2">어디부터 확인할지, 이동형 거점은 어디가 좋을지, 제안서 초안까지 물어볼 수 있습니다.</p>
              <p className="mt-2">답변에서 언급한 동네는 왼쪽 지도에 굵은 테두리로 표시됩니다.</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
