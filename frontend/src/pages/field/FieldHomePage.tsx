import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { type RegionKey } from '@/config'
import { useDoneCells } from '@/features/field/doneStore'
import { BaseMap, PointsLayer, boundsOfPoints } from '@/map'
import { CHECK_LEVEL_COLOR } from '@/map/colors'
import type { FieldCheckList } from '@/types/api'

/** 현장 담당자: 관리자가 보낸 확인 목록. 없으면 .json 붙여넣기/파일로 불러온다 */
export function FieldHomePage() {
  const qc = useQueryClient()
  const list = useQuery({ queryKey: ['field-check-list'], queryFn: () => api.fetchFieldCheckList() })
  const { done } = useDoneCells()
  const [showDone, setShowDone] = useState(true)
  const [pasted, setPasted] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const importList = useMutation({
    mutationFn: async (text: string) => {
      let parsed: FieldCheckList
      try {
        parsed = JSON.parse(text) as FieldCheckList
      } catch {
        throw new Error('JSON 형식이 아닙니다. 관리자 화면에서 내려받은 .json 파일 내용을 넣어 주세요.')
      }
      if (!Array.isArray(parsed.cells) || parsed.cells.length === 0) throw new Error('확인할 동네가 들어 있지 않습니다.')
      return api.publishFieldCheckList(parsed)
    },
    onSuccess: () => {
      setPasted('')
      setImportError(null)
      qc.invalidateQueries({ queryKey: ['field-check-list'] })
    },
    onError: (e) => setImportError(e instanceof Error ? e.message : '불러오지 못했습니다.'),
  })

  const cells = useMemo(() => {
    const all = list.data?.cells ?? []
    return showDone ? all : all.filter((c) => !done[c.id])
  }, [list.data, showDone, done])
  const bounds = useMemo(() => boundsOfPoints(cells), [cells])
  const doneCount = (list.data?.cells ?? []).filter((c) => done[c.id]).length

  async function onFile(f: File | undefined) {
    if (!f) return
    importList.mutate(await f.text())
  }

  const importer = (
    <Card className="space-y-2">
      <p className="font-semibold">목록 불러오기</p>
      <p className="text-sm text-slate-600">관리자가 보낸 .json 파일을 고르거나 내용을 붙여 넣으세요.</p>
      <div className="flex flex-wrap gap-2">
        <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
        <Button variant="secondary" size="lg" onClick={() => fileRef.current?.click()}>
          파일 고르기
        </Button>
      </div>
      <textarea value={pasted} onChange={(e) => setPasted(e.target.value)} rows={3} placeholder='{"region": "춘천", "cells": [...]}' className="w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-sm" />
      <Button size="lg" onClick={() => importList.mutate(pasted)} disabled={!pasted.trim()} loading={importList.isPending}>
        붙여넣은 내용 불러오기
      </Button>
      {importError && (
        <p role="alert" className="text-red-700">
          {importError}
        </p>
      )}
    </Card>
  )

  if (list.isPending) return <Spinner className="p-4" />
  if (list.isError) return <ErrorState error={list.error} onRetry={() => list.refetch()} />

  if (!list.data) {
    return (
      <div className="space-y-4">
        <EmptyState title="받은 확인 목록이 없습니다" description="관리자가 목록을 보내면 여기에 나타납니다." />
        {importer}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
          <span>{list.data.region ?? ''}</span>
          <span>· {list.data.cells.length}곳</span>
          <span>· {new Date(list.data.created_at).toLocaleString('ko-KR')}</span>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-800">완료 {doneCount}</span>
        </div>
        <p className="text-lg">{list.data.headline}</p>
        <label className="flex items-center gap-2 text-base">
          <input type="checkbox" checked={showDone} onChange={(e) => setShowDone(e.target.checked)} className="size-5" />
          저장 끝난 동네도 보기
        </label>
      </Card>

      {cells.length > 0 && (
        <BaseMap bounds={bounds} region={(list.data.region as RegionKey | null) ?? undefined} className="h-64" scrollWheelZoom={false}>
          <PointsLayer map={{ layer: 'checks', ref: 'list', geojson: null, points: cells }} />
        </BaseMap>
      )}

      <ol className="space-y-2">
        {cells.map((c) => (
          <li key={c.id}>
            <Link to={`/field/cells/${encodeURIComponent(c.id)}`} className={`block rounded-2xl border bg-white p-4 ${done[c.id] ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200'}`}>
              <div className="flex items-center gap-3">
                <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-base font-bold text-white" style={{ background: CHECK_LEVEL_COLOR[c.level] ?? '#334155' }}>
                  {c.order}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xl font-bold">{c.emd_name}</p>
                  <p className="text-base text-slate-600">
                    {c.level} · 확인 질문 {c.questions.length}개
                  </p>
                </div>
                {done[c.id] ? <span className="text-base font-semibold text-emerald-700">저장됨 ✓</span> : <span className="text-2xl text-slate-400">›</span>}
              </div>
            </Link>
          </li>
        ))}
      </ol>
      {cells.length === 0 && <EmptyState title="남은 동네가 없습니다" description="모든 동네의 확인 결과를 저장했습니다." />}

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer font-semibold">다른 목록 불러오기</summary>
        <div className="mt-3">{importer}</div>
      </details>
    </div>
  )
}
