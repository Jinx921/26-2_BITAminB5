import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Download, Send } from 'lucide-react'
import { api, isMockMode } from '@/api'
import { SAMPLE_QUESTIONS } from '@/api/mock/questions'
import { QuestionBox } from '@/components/QuestionBox'
import { CandidatesLegend } from '@/components/map/CandidatesLegend'
import { RegionTabs } from '@/components/map/RegionTabs'
import { SimLegend, type SimRadius } from '@/components/map/SimLegend'
import { TypeLegend } from '@/components/map/TypeLegend'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { Spinner } from '@/components/ui/Spinner'
import { REGION_KEYS, regionOf, type RegionKey } from '@/config'
import { displayToFieldCheckList } from '@/features/admin/fieldList'
import { FragmentRenderer } from '@/fragments'
import { downloadTextFile } from '@/lib/download'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { BaseMap, GridLayer, PointsLayer, useCandidatesLayer, useSimLayer, useTypesLayer } from '@/map'
import { TYPE_ORDER } from '@/map/colors'
import type { GridCollection } from '@/types/geo'
import type { IsolationType, MapPoint } from '@/types/display'

type MapLayerKind = 'types' | 'candidates' | 'sim'
const LAYER_OPTIONS: { value: MapLayerKind; label: string }[] = [
  { value: 'types', label: '유형' },
  { value: 'candidates', label: '후보' },
  { value: 'sim', label: '배치' },
]
const LAYER_EMPTY: Record<MapLayerKind, string> = {
  types: '이 지역에는 유형 격자가 없습니다.',
  candidates: '이 지역에는 낮 활동이 줄어든 후보 동네가 없습니다.',
  sim: '이 지역에는 배치 시뮬레이션 대상(긴급방문형) 동네가 없습니다.',
}

function gridBounds(g: GridCollection): [[number, number], [number, number]] | null {
  let s = Infinity, n = -Infinity, w = Infinity, e = -Infinity
  for (const f of g.features) for (const [lon, lat] of f.geometry.coordinates[0] ?? []) { s = Math.min(s, lat); n = Math.max(n, lat); w = Math.min(w, lon); e = Math.max(e, lon) }
  return Number.isFinite(s) ? [[s, w], [n, e]] : null
}

/**
 * 관리자 메인: 왼쪽은 화면을 채우는 지도(유형 / 후보 / 배치), 오른쪽은 420px 질문·응답 패널.
 * 지역 전환은 세 레이어에 같이 적용되고, 레이어를 바꿔도 지도 위치·줌은 유지된다 (범위는 지역이 바뀔 때만 맞춘다).
 */
export function AdminHomePage() {
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [layer, setLayer] = useState<MapLayerKind>('types')
  const [radius, setRadius] = useState<SimRadius>(1000)
  const [visible, setVisible] = useState<Set<IsolationType>>(new Set(TYPE_ORDER))
  const [showExcluded, setShowExcluded] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const navigate = useNavigate()

  const ask = useAskQuestion()
  const display = ask.data ?? null
  const fieldCheckList = display ? displayToFieldCheckList(display) : null

  // 응답 지도 첫 점의 지역을 따른다 (질문에 지역명이 없을 때)
  const answerRegion = useMemo(() => { const p = display?.map?.points?.[0]; return p ? regionOf(p.lat, p.lon) : null }, [display])
  const effectiveRegion = answerRegion ?? region

  // 유형 지도는 범위·집계용으로 항상 읽고, 후보·배치는 고른 레이어일 때만 읽는다
  const types = useTypesLayer(effectiveRegion, showExcluded)
  const candidates = useCandidatesLayer(layer === 'candidates' ? effectiveRegion : null)
  const sim = useSimLayer(layer === 'sim' ? effectiveRegion : null, 3, radius)
  const current = layer === 'types' ? types : layer === 'candidates' ? candidates : sim

  // 지역이 바뀔 때만 범위를 맞춘다 (레이어 전환은 위치·줌 유지)
  const bounds = useMemo(() => (types.data ? gridBounds(types.data) : null), [types.data])

  const sendList = useMutation({
    mutationFn: async () => {
      if (!fieldCheckList) throw new Error('이 답변에는 현장 확인 동네가 없습니다.')
      return api.publishFieldCheckList(fieldCheckList)
    },
    onSuccess: () => navigate('/admin/field-list'),
  })

  const typeCounts = useMemo(() => {
    const c: Partial<Record<IsolationType, number>> = {}
    types.data?.features.forEach((f) => { const t = f.properties.type ?? '관찰형'; c[t] = (c[t] ?? 0) + 1 })
    return c
  }, [types.data])
  const monthCounts = useMemo(() => {
    const c: Partial<Record<number, number>> = {}
    candidates.data?.features.forEach((f) => { const m = f.properties.persistent_months ?? 0; c[m] = (c[m] ?? 0) + 1 })
    return c
  }, [candidates.data])
  const simStats = useMemo(() => {
    const total = sim.data?.features.length ?? 0
    const covered = sim.data?.features.filter((f) => f.properties.covered === 1).length ?? 0
    return { total, covered }
  }, [sim.data])

  // 답변에서 언급한 칸(굵게) / 답변 결과에 든 칸(중간). 후보 응답은 결과 전체를 강조한다
  const highlightIds = useMemo(() => {
    const s = new Set<string>()
    const m = display?.map
    if (m && m.layer !== 'facilities') m.points.forEach((p) => p.highlight && s.add(p.id))
    return s
  }, [display])
  const secondaryIds = useMemo(() => {
    const s = new Set<string>()
    const m = display?.map
    if (m && m.layer === 'candidates' && layer === 'candidates') m.points.forEach((p) => s.add(p.id))
    return s
  }, [display, layer])
  const siteCount = display?.map && (display.map.layer === 'sites' || display.map.layer === 'interventions') ? display.map.points.length : 0

  const onSelectPoint = (p: MapPoint) => setSelectedId(p.id)
  function submit(question: string) {
    setSelectedId(null)
    for (const r of REGION_KEYS) if (question.includes(r)) setRegion(r)
    ask.mutate(
      { mode: 'admin', question },
      {
        // 응답 레이어에 맞춰 지도 레이어를 자동으로 고른다
        onSuccess: (d) => {
          const l = d.map?.layer
          if (l === 'candidates') setLayer('candidates')
          else if (l === 'sites' || l === 'interventions') setLayer('sim')
          else if (l === 'types' || l === 'checks') setLayer('types')
        },
      },
    )
  }

  const isEmpty = current.data !== undefined && current.data.features.length === 0

  return (
    <div className="flex h-full">
      {/* 지도 */}
      <section className="relative min-w-0 flex-1">
        {current.isPending && <div className="absolute inset-0 z-[1001] flex items-center justify-center bg-surface/60"><Spinner label="지도를 불러오는 중" /></div>}
        {current.isError && <div className="absolute inset-x-0 top-16 z-[1001] mx-auto max-w-md"><ErrorState error={current.error} onRetry={() => current.refetch()} title="지도를 불러오지 못했습니다" /></div>}
        {isEmpty && !current.isPending && <p className="absolute inset-x-0 top-16 z-[1001] mx-auto w-fit rounded-btn border border-line bg-surface/95 px-3 py-2 text-sm text-ink-2 shadow-card">{LAYER_EMPTY[layer]}</p>}

        <BaseMap bounds={bounds} region={effectiveRegion} className="h-full rounded-none border-0" zoomPosition="topright">
          {layer === 'types' && types.data && (
            <GridLayer key={`types-${effectiveRegion}-${showExcluded}`} data={types.data} variant="types" visibleTypes={visible} highlightIds={highlightIds} selectedId={selectedId} onSelect={(p) => setSelectedId(p.cell_id)} />
          )}
          {layer === 'candidates' && candidates.data && (
            <GridLayer key={`candidates-${effectiveRegion}`} data={candidates.data} variant="candidates" highlightIds={highlightIds} secondaryIds={secondaryIds} selectedId={selectedId} onSelect={(p) => setSelectedId(p.cell_id)} />
          )}
          {layer === 'sim' && sim.data && (
            <GridLayer key={`sim-${effectiveRegion}-${radius}`} data={sim.data} variant="sim" highlightIds={highlightIds} selectedId={selectedId} onSelect={(p) => setSelectedId(p.cell_id)} />
          )}
          {/* 후보 응답은 격자 테두리로 강조하므로 후보 지도 위에는 점을 따로 찍지 않는다 */}
          {display?.map && display.map.layer !== 'types' && display.map.layer !== 'facilities' && !(display.map.layer === 'candidates' && layer === 'candidates') && (
            <PointsLayer map={display.map} selectedId={selectedId} onSelect={onSelectPoint} />
          )}
        </BaseMap>

        <div className="absolute left-3 top-3 z-[1000] flex flex-col items-start gap-2">
          <RegionTabs value={effectiveRegion} onChange={setRegion} />
          <SegmentedControl size="sm" aria-label="지도 레이어" value={layer} onChange={setLayer} options={LAYER_OPTIONS} className="shadow-card" />
        </div>
        <div className="absolute bottom-6 left-3 z-[1000] w-64 space-y-2">
          {layer === 'types' && (
            <>
              <TypeLegend counts={typeCounts} visible={visible} onToggle={(t) => setVisible((prev) => { const n = new Set(prev); if (n.has(t)) n.delete(t); else n.add(t); return n })} />
              <label className="flex items-center gap-2 rounded-btn border border-line bg-surface/95 px-2 py-1.5 text-xs text-ink-2 shadow-card">
                <input type="checkbox" checked={showExcluded} onChange={(e) => setShowExcluded(e.target.checked)} className="accent-primary" />
                현장 확인으로 제외된 곳 보기
              </label>
            </>
          )}
          {layer === 'candidates' && <CandidatesLegend counts={monthCounts} total={candidates.data?.features.length} />}
          {layer === 'sim' && <SimLegend radius={radius} onRadiusChange={setRadius} covered={sim.data ? simStats.covered : undefined} total={sim.data ? simStats.total : undefined} siteCount={siteCount} />}
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
              {display.map?.layer === 'checks' && isMockMode && (
                <div className="border-t border-line pt-3">
                  <Button icon={<Send className="size-4" />} onClick={() => sendList.mutate()} loading={sendList.isPending}>
                    현장 담당자에게 보내기
                  </Button>
                  <p className="mt-1 text-xs text-ink-3">{display.map.points.length}곳. 현장 확인 목록 탭에서 복사·내려받기도 할 수 있습니다.</p>
                  {sendList.isError && <ErrorState error={sendList.error} title="보내지 못했습니다" />}
                </div>
              )}
              {display.map?.layer === 'checks' && !isMockMode && (
                <div className="border-t border-line pt-3">
                  {fieldCheckList ? (
                    <Button
                      variant="outline"
                      icon={<Download className="size-4" />}
                      onClick={() => downloadTextFile(`현장확인목록_${fieldCheckList.region ?? ''}.json`, JSON.stringify(fieldCheckList, null, 2), 'application/json')}
                    >
                      현장 확인 목록 JSON 내려받기
                    </Button>
                  ) : (
                    <ErrorState error={new Error('이 답변에서 현장 확인 목록을 만들 수 없습니다.')} title="목록을 내려받지 못했습니다" />
                  )}
                  <p className="mt-1 text-xs text-ink-3">백엔드 전달 API는 아직 없습니다. 내려받은 JSON을 현장 담당자에게 직접 전달해 주세요.</p>
                </div>
              )}
            </div>
          )}
          {!display && !ask.isPending && !ask.isError && (
            <div className="pt-6 text-sm text-ink-3">
              <p className="font-semibold text-ink-2">어디부터 확인할지, 이동형 거점은 어디가 좋을지, 제안서 초안까지 물어볼 수 있습니다.</p>
              <p className="mt-2">답변에서 언급한 동네는 왼쪽 지도에 굵은 테두리로 표시됩니다. 지도 왼쪽 위에서 유형 / 후보 / 배치 지도를 바꿔 볼 수 있습니다.</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
