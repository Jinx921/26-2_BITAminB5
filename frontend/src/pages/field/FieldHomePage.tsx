import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronRight, Upload } from 'lucide-react'
import { api } from '@/api'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { List, ListRow } from '@/components/ui/ListRow'
import { Sheet } from '@/components/ui/Sheet'
import { Spinner } from '@/components/ui/Spinner'
import { type RegionKey } from '@/config'
import { useDoneCells } from '@/features/field/doneStore'
import { formatDateTime } from '@/lib/datetime'
import { BaseMap, PointsLayer, boundsOfPoints } from '@/map'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { FieldCheckList } from '@/types/api'

/** 현장 담당자: 받은 확인 목록 (행 목록). 없으면 .json 으로 불러온다 */
export function FieldHomePage() {
  const qc = useQueryClient()
  const list = useQuery({ queryKey: ['field-check-list'], queryFn: () => api.fetchFieldCheckList() })
  const { done } = useDoneCells()
  const [importOpen, setImportOpen] = useState(false)
  const [pasted, setPasted] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const importList = useMutation({
    mutationFn: async (text: string) => {
      let parsed: FieldCheckList
      try { parsed = JSON.parse(text) as FieldCheckList } catch { throw new Error('JSON 형식이 아닙니다. 관리자 화면에서 내려받은 .json 파일을 넣어 주세요.') }
      if (!Array.isArray(parsed.cells) || parsed.cells.length === 0) throw new Error('확인할 동네가 들어 있지 않습니다.')
      return api.publishFieldCheckList(parsed)
    },
    onSuccess: () => { setPasted(''); setImportError(null); setImportOpen(false); qc.invalidateQueries({ queryKey: ['field-check-list'] }) },
    onError: (e) => setImportError(e instanceof Error ? e.message : '불러오지 못했습니다.'),
  })

  const cells = useMemo(() => list.data?.cells ?? [], [list.data])
  const bounds = useMemo(() => boundsOfPoints(cells), [cells])
  const doneCount = cells.filter((c) => done[c.id]).length

  const importer = (
    <Sheet open={importOpen} onClose={() => setImportOpen(false)} title="목록 불러오기">
      <p className="text-sm text-ink-2">관리자가 보낸 .json 파일을 고르거나 내용을 붙여 넣으세요.</p>
      <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) importList.mutate(await f.text()) }} />
      <Button variant="outline" className="mt-3 w-full" icon={<Upload className="size-4" />} onClick={() => fileRef.current?.click()}>파일 고르기</Button>
      <textarea value={pasted} onChange={(e) => setPasted(e.target.value)} rows={4} placeholder='{"region": "춘천", "cells": [...]}' className="mt-3 w-full rounded-btn border border-line-strong px-3 py-2 font-mono text-sm" />
      <Button className="mt-2 w-full" onClick={() => importList.mutate(pasted)} disabled={!pasted.trim()} loading={importList.isPending}>붙여넣은 내용 불러오기</Button>
      {importError && <p role="alert" className="mt-2 text-sm text-danger">{importError}</p>}
    </Sheet>
  )

  if (list.isPending) return <Spinner className="py-6" />
  if (list.isError) return <ErrorState error={list.error} onRetry={() => list.refetch()} />
  if (!list.data) {
    return (
      <>
        <EmptyState title="받은 확인 목록이 없습니다" description="관리자가 목록을 보내면 여기에 나타납니다." action={<Button variant="outline" icon={<Upload className="size-4" />} onClick={() => setImportOpen(true)}>파일로 불러오기</Button>} />
        {importer}
      </>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-ink-3">{list.data.region ?? ''} · {cells.length}곳 · {formatDateTime(list.data.created_at)} · <span className="font-semibold text-green">완료 {doneCount}</span></p>
        <p className="mt-1 text-base text-ink-2">{list.data.headline}</p>
      </div>
      {cells.length > 0 && (
        <BaseMap bounds={bounds} region={(list.data.region as RegionKey | null) ?? undefined} className="h-52" scrollWheelZoom={false}>
          <PointsLayer map={{ layer: 'checks', ref: 'list', geojson: null, points: cells }} />
        </BaseMap>
      )}
      <List className="border-t border-line">
        {cells.map((c) => (
          <ListRow
            key={c.id}
            to={`/field/cells/${encodeURIComponent(c.id)}`}
            muted={!!done[c.id]}
            leading={<span className="inline-flex size-8 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: done[c.id] ? '#9ca3af' : (CHECK_LEVEL_COLOR[c.level] ?? '#111827') }}>{c.order}</span>}
            title={<span className="text-lg">{c.emd_name}</span>}
            subtitle={`${c.level} · 확인 질문 ${c.questions.length}개`}
            trailing={done[c.id] ? <span className="inline-flex items-center gap-1 text-green"><Check className="size-4" />저장됨</span> : <ChevronRight className="size-5 text-ink-3" />}
          />
        ))}
      </List>
      <Button variant="text" size="sm" className="-ml-3" icon={<Upload className="size-4" />} onClick={() => setImportOpen(true)}>다른 목록 불러오기</Button>
      {importer}
    </div>
  )
}
