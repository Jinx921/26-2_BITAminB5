import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, isMockMode } from '@/api'
import { RegionTabs } from '@/components/map/RegionTabs'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { PageHeader } from '@/components/ui/PageHeader'
import { Spinner } from '@/components/ui/Spinner'
import { type RegionKey } from '@/config'
import { displayToFieldCheckList, fieldListToMarkdown, fieldListToText } from '@/features/admin/fieldList'
import { copyToClipboard, downloadTextFile } from '@/lib/download'
import { useAskQuestion } from '@/lib/useAskQuestion'
import { BaseMap, PointsLayer, boundsOfPoints } from '@/map'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { FieldCheckList } from '@/types/api'

/**
 * 현장 확인 목록: 에이전트에게 목록을 받아 현장 담당자에게 보낸다.
 * 백엔드 전달 API 가 없어 목업은 공유 저장소, 실제 모드는 복사·내려받기(현장 앱에서 붙여넣기)로 전달한다.
 */
export function AdminFieldListPage() {
  const qc = useQueryClient()
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [draft, setDraft] = useState<FieldCheckList | null>(null)
  const [copied, setCopied] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const current = useQuery({ queryKey: ['field-check-list'], queryFn: () => api.fetchFieldCheckList() })
  const ask = useAskQuestion()
  const publish = useMutation({
    mutationFn: (list: FieldCheckList) => api.publishFieldCheckList(list),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['field-check-list'] }),
  })

  function generate() {
    setDraft(null)
    ask.mutate(
      { mode: 'admin', question: `${region} 현장 확인 목록 만들어 줘` },
      {
        onSuccess: (d) => {
          const list = displayToFieldCheckList(d)
          setDraft(list)
        },
      },
    )
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
    <>
      <PageHeader
        title="현장 확인 목록 보내기"
        description="판정이 애매한 동네와 확인 질문을 받아 현장 담당자에게 전달합니다."
        actions={
          <>
            <RegionTabs value={region} onChange={setRegion} />
            <Button onClick={generate} loading={ask.isPending}>
              목록 새로 만들기
            </Button>
          </>
        }
      />

      {ask.isError && <ErrorState error={ask.error} title="목록을 받지 못했습니다" />}
      {ask.isPending && (
        <Card>
          <Spinner label="에이전트가 현장 확인 목록을 만드는 중" />
        </Card>
      )}
      {ask.isSuccess && !draft && !ask.isPending && <ErrorState error={new Error('응답에 현장 확인 동네가 없습니다. 질문을 바꿔 다시 시도해 주세요.')} title="목록이 비어 있습니다" />}

      {current.isPending && !list && <Spinner />}
      {!list && !ask.isPending && !current.isPending && (
        <EmptyState title="보낸 목록이 없습니다" description="지역을 고르고 '목록 새로 만들기'를 누르면 에이전트가 현장 확인 목록을 만듭니다." />
      )}

      {list && !ask.isPending && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <section className="space-y-3">
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${isDraft ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'}`}>{isDraft ? '새 목록 (아직 안 보냄)' : '보낸 목록'}</span>
                <span className="text-sm text-slate-500">
                  {list.region ?? ''} · {list.cells.length}곳 · {new Date(list.created_at).toLocaleString('ko-KR')}
                </span>
              </div>
              <p className="text-slate-800">{list.headline}</p>
              <div className="flex flex-wrap gap-2">
                {isDraft && (
                  <Button onClick={() => publish.mutate(list, { onSuccess: () => setDraft(null) })} loading={publish.isPending}>
                    현장 담당자에게 보내기
                  </Button>
                )}
                <Button variant="secondary" onClick={copy}>
                  {copied ? '복사됨' : '글로 복사'}
                </Button>
                <Button variant="secondary" onClick={() => downloadTextFile(`현장확인목록_${list.region ?? ''}.md`, fieldListToMarkdown(list), 'text/markdown;charset=utf-8')}>
                  .md 내려받기
                </Button>
                <Button variant="secondary" onClick={() => downloadTextFile(`현장확인목록_${list.region ?? ''}.json`, JSON.stringify(list, null, 2), 'application/json')}>
                  .json 내려받기 (현장 앱용)
                </Button>
              </div>
              {publish.isError && <ErrorState error={publish.error} title="보내지 못했습니다" />}
              {!isMockMode && (
                <p className="text-xs text-slate-500">
                  전달 API 가 아직 없어 .json 파일을 내려받아 현장 담당자 앱의 "목록 불러오기"에 넣는 방식으로 전달합니다.
                </p>
              )}
            </Card>

            <ol className="space-y-2">
              {list.cells.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(c.id)}
                    className={`w-full rounded-xl border bg-white p-3 text-left ${selectedId === c.id ? 'border-sky-500 ring-2 ring-sky-200' : 'border-slate-200'}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="inline-flex size-7 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: CHECK_LEVEL_COLOR[c.level] ?? '#334155' }}>
                        {c.order}
                      </span>
                      <span className="font-semibold">{c.emd_name}</span>
                      <span className="text-sm text-slate-500">{c.level}</span>
                    </div>
                    <ul className="mt-2 list-disc pl-6 text-sm text-slate-700">
                      {c.questions.map((q) => (
                        <li key={q}>{q}</li>
                      ))}
                    </ul>
                  </button>
                </li>
              ))}
            </ol>
          </section>

          <section>
            {mapData && (
              <BaseMap bounds={bounds} region={(list.region as RegionKey | null) ?? region} className="h-[36rem]">
                <PointsLayer map={mapData} selectedId={selectedId} onSelect={(p) => setSelectedId(p.id)} />
              </BaseMap>
            )}
          </section>
        </div>
      )}
    </>
  )
}
