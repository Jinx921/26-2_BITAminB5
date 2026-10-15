import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, RefreshCw, Send } from 'lucide-react'
import { api, isMockMode } from '@/api'
import { RegionTabs } from '@/components/map/RegionTabs'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Menu } from '@/components/ui/Menu'
import { Spinner } from '@/components/ui/Spinner'
import { type RegionKey } from '@/config'
import { displayToFieldCheckList, fieldListToMarkdown, fieldListToText } from '@/features/admin/fieldList'
import { copyToClipboard, downloadTextFile } from '@/lib/download'
import { formatDateTime } from '@/lib/datetime'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { BaseMap, PointsLayer, boundsOfPoints } from '@/map'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { FieldCheckList } from '@/types/api'

/** 현장 확인 목록: 에이전트에게 받아 현장 담당자에게 보낸다. 왼쪽 행 목록, 오른쪽 지도 */
export function AdminFieldListPage() {
  const qc = useQueryClient()
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [draft, setDraft] = useState<FieldCheckList | null>(null)
  const [copied, setCopied] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const current = useQuery({ queryKey: ['field-check-list'], queryFn: () => api.fetchFieldCheckList(), enabled: isMockMode })
  const ask = useAskQuestion()
  const publish = useMutation({ mutationFn: (list: FieldCheckList) => api.publishFieldCheckList(list), onSuccess: () => qc.invalidateQueries({ queryKey: ['field-check-list'] }) })

  function generate() {
    setDraft(null)
    ask.mutate({ mode: 'admin', question: `${region} 현장 확인 목록 만들어 줘` }, { onSuccess: (d) => setDraft(displayToFieldCheckList(d)) })
  }

  const list = draft ?? current.data ?? null
  const isDraft = draft !== null
  const bounds = useMemo(() => (list ? boundsOfPoints(list.cells) : null), [list])
  const mapData = useMemo(() => (list ? ({ layer: 'checks', ref: 'list', geojson: null, points: list.cells } as const) : null), [list])

  async function copy() {
    if (!list) return
    setCopied(await copyToClipboard(fieldListToText(list)))
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="flex h-full">
      <section className="flex w-[480px] shrink-0 flex-col border-r border-line">
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
          <h1 className="text-lg font-bold">현장 확인 목록</h1>
          <div className="flex items-center gap-2">
            <RegionTabs value={region} onChange={setRegion} />
            <Button size="sm" variant={list ? 'outline' : 'fill'} icon={<RefreshCw className="size-4" />} onClick={generate} loading={ask.isPending}>
              {list ? '새로 만들기' : '목록 만들기'}
            </Button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          {ask.isError && <ErrorState error={ask.error} title="목록을 받지 못했습니다" />}
          {ask.isPending && <Spinner label="에이전트가 현장 확인 목록을 만드는 중" />}
          {ask.isSuccess && !draft && !ask.isPending && <ErrorState error={new Error('응답에 현장 확인 동네가 없습니다. 다시 시도해 주세요.')} title="목록이 비어 있습니다" />}
          {current.isPending && isMockMode && !list && <Spinner />}
          {!list && !ask.isPending && (!isMockMode || !current.isPending) && (
            <EmptyState
              title={isMockMode ? '보낸 목록이 없습니다' : '백엔드 전달 API가 없습니다'}
              description={isMockMode ? "지역을 고르고 '목록 만들기'를 누르면 에이전트가 판정이 애매한 동네와 확인 질문을 뽑습니다." : "목록 생성은 가능하지만 백엔드의 현장 확인 목록 전달 API가 아직 없습니다. 생성한 목록을 .json으로 내려받아 현장 담당자에게 직접 전달해 주세요."}
            />
          )}

          {list && !ask.isPending && (
            <>
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${isDraft ? 'bg-amber-50 text-amber-ink' : 'bg-green-soft text-green'}`}>{isDraft ? '아직 안 보냄' : '보낸 목록'}</span>
                    <span className="text-ink-3">{list.region ?? ''} · {list.cells.length}곳 · {formatDateTime(list.created_at)}</span>
                  </p>
                  <p className="mt-1 text-sm text-ink-2">{list.headline}</p>
                </div>
              </div>
              <div className="mb-3 flex items-center gap-2">
                {isDraft && isMockMode && (
                  <Button size="sm" icon={<Send className="size-4" />} onClick={() => publish.mutate(list, { onSuccess: () => setDraft(null) })} loading={publish.isPending}>
                    현장 담당자에게 보내기
                  </Button>
                )}
                <Button size="sm" variant="outline" icon={<Copy className="size-4" />} onClick={copy}>{copied ? '복사됨' : '글로 복사'}</Button>
                <Menu
                  label="내려받기"
                  items={[
                    { label: '.md 내려받기', onSelect: () => downloadTextFile(`현장확인목록_${list.region ?? ''}.md`, fieldListToMarkdown(list), 'text/markdown;charset=utf-8') },
                    { label: '.json 내려받기 (현장 앱용)', onSelect: () => downloadTextFile(`현장확인목록_${list.region ?? ''}.json`, JSON.stringify(list, null, 2), 'application/json') },
                  ]}
                />
              </div>
              {publish.isError && <ErrorState error={publish.error} title="보내지 못했습니다" />}
              {!isMockMode && <p className="mb-3 text-xs text-ink-3">백엔드 전달 API가 아직 없어 전송하지 않습니다. .json을 내려받아 현장 담당자가 직접 가져와야 합니다.</p>}

              <ol className="divide-y divide-line border-t border-line">
                {list.cells.map((c) => (
                  <li key={c.id}>
                    <button type="button" onClick={() => setSelectedId(c.id)} className={`-mx-2 flex w-[calc(100%+1rem)] items-start gap-3 rounded-[8px] px-2 py-3 text-left hover:bg-canvas ${selectedId === c.id ? 'bg-primary-soft' : ''}`}>
                      <span className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: CHECK_LEVEL_COLOR[c.level] ?? '#111827' }}>{c.order}</span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-baseline gap-2"><span className="font-semibold">{c.emd_name}</span><span className="text-xs text-ink-3">{c.level}</span></span>
                        <ul className="mt-1 list-disc pl-4 text-xs text-ink-2">{c.questions.map((q) => <li key={q}>{q}</li>)}</ul>
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      </section>
      <section className="min-w-0 flex-1">
        {mapData ? (
          <BaseMap bounds={bounds} region={(list?.region as RegionKey | null) ?? region} className="h-full rounded-none border-0" zoomPosition="topright">
            <PointsLayer map={mapData} selectedId={selectedId} onSelect={(p) => setSelectedId(p.id)} />
          </BaseMap>
        ) : (
          <BaseMap region={region} className="h-full rounded-none border-0" zoomPosition="topright" />
        )}
      </section>
    </div>
  )
}
