import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { copyToClipboard, downloadTextFile, safeFilename } from '@/lib/download'
import type { DocumentData } from '@/types/display'
import type { FragmentProps } from '../types'

/** 문서(제안서·현황 보고·주민 안내문). sections 로 그리고 markdown 은 복사·.md 내려받기에 쓴다 */
export function DocumentFragment({ fragment }: FragmentProps<DocumentData>) {
  const doc = fragment.data
  const [copied, setCopied] = useState(false)

  async function copy() {
    const ok = await copyToClipboard(doc.markdown ?? '')
    setCopied(ok)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5" data-fragment="document">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">{doc.type_name}</span>
          <h2 className="mt-2 text-xl font-bold">{doc.title}</h2>
          <p className="mt-1 text-sm text-slate-500">초안입니다. 담당자 검토 후 사용하세요.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={copy}>
            {copied ? '복사됨' : '복사'}
          </Button>
          <Button onClick={() => downloadTextFile(`${safeFilename(doc.title)}.md`, doc.markdown ?? '', 'text/markdown;charset=utf-8')}>
            .md 내려받기
          </Button>
        </div>
      </div>
      <div className="space-y-5">
        {(doc.sections ?? []).map((s, i) => (
          <section key={i}>
            <h3 className="mb-1 font-semibold text-slate-900">{s.heading}</h3>
            <p className="whitespace-pre-line leading-relaxed text-slate-800">{s.body}</p>
          </section>
        ))}
      </div>
    </article>
  )
}
