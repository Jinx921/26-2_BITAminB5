import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronRight, Upload } from 'lucide-react'
import { api, isMockMode } from '@/api'
import { isApiError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
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
import { useViewMode } from '@/features/viewMode'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { FieldCheckList } from '@/types/api'

/** 현장 담당자: 받은 확인 목록 (행 목록). 없으면 .json 으로 불러온다 */
export function FieldHomePage() {
  const qc = useQueryClient()
  const { user } = useAuth()
  const listQueryKey = ['field-check-list', user?.id] as const
  const list = useQuery({
    queryKey: listQueryKey,
    queryFn: () => api.fetchFieldCheckList(),
  })
  const { done } = useDoneCells()
  const [importOpen, setImportOpen] = useState(false)
  const [pasted, setPasted] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [view] = useViewMode()
  const desktop = view === 'desktop'

  const importList = useMutation({
    mutationFn: async (text: string) => {
      let parsed: unknown
      try { parsed = JSON.parse(text) } catch { throw new Error('JSON 형식이 아닙니다. 관리자 화면에서 내려받은 .json 파일을 넣어 주세요.') }
      if (!parsed || typeof parsed !== 'object' || !('cells' in parsed) || !Array.isArray(parsed.cells) || parsed.cells.length === 0) {
        throw new Error('확인할 동네가 들어 있지 않습니다.')
      }
      try {
        return await api.saveFieldCheckList(parsed as FieldCheckList)
      } catch (error) {
        if (isApiError(error) && error.status === 422) {
          throw new Error('현장 확인 목록 형식이 올바르지 않습니다. 관리자 화면에서 내려받은 JSON 파일을 다시 확인해 주세요.')
        }
        throw error
      }
    },
    onSuccess: (saved) => { setPasted(''); setImportError(null); setImportOpen(false); qc.setQueryData(listQueryKey, saved) },
    onError: (e) => setImportError(e instanceof Error ? e.message : '불러오지 못했습니다.'),
  })

  const cells = useMemo(() => list.data?.cells ?? [], [list.data])
  const bounds = useMemo(() => boundsOfPoints(cells), [cells])
  const doneCount = cells.filter((c) => done[c.id]).length

  const importer = (
    <Sheet open={importOpen} onClose={() => setImportOpen(false)} title="목록 불러오기">
      <p className="text-sm text-ink-2">
        {isMockMode
          ? '관리자가 전달한 .json 파일을 고르거나 내용을 붙여 넣으세요. 목업 모드에서는 이 브라우저의 테스트 저장소에 저장됩니다.'
          : '관리자가 전달한 .json 파일을 고르거나 내용을 붙여 넣으세요. 저장되면 같은 계정으로 로그인한 다른 기기에서도 확인할 수 있습니다.'}
      </p>
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
        <EmptyState
          title="저장된 확인 목록이 없습니다"
          description={isMockMode
            ? '목업 모드에서는 이 브라우저의 테스트 저장소를 사용합니다. 실제 다른 기기 동기화는 백엔드 API 모드에서 사용할 수 있습니다.'
            : '관리자가 전달한 .json 파일을 불러오면 계정에 저장되어 다른 기기에서도 표시됩니다.'}
          action={<Button variant="outline" icon={<Upload className="size-4" />} onClick={() => setImportOpen(true)}>파일로 불러오기</Button>}
        />
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
      <div className={desktop ? 'grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]' : 'space-y-4'}>
      {cells.length > 0 && (
        <div className={desktop ? 'order-2 md:sticky md:top-4 md:self-start' : ''}>
          <BaseMap bounds={bounds} region={(list.data.region as RegionKey | null) ?? undefined} className={desktop ? 'h-[36rem]' : 'h-52'} scrollWheelZoom={desktop}>
            <PointsLayer map={{ layer: 'checks', ref: 'list', geojson: null, points: cells }} />
          </BaseMap>
        </div>
      )}
      <List className="order-1 border-t border-line">
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
      </div>
      <Button variant="text" size="sm" className="-ml-3" icon={<Upload className="size-4" />} onClick={() => setImportOpen(true)}>다른 목록 불러오기</Button>
      {importer}
    </div>
  )
}
