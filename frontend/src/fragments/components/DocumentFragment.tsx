import { useState } from 'react'
import { ChevronDown, Copy, Download, FileText } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { copyToClipboard, downloadTextFile, safeFilename } from '@/lib/download'
import type { DocumentData } from '@/types/display'
import type { FragmentProps } from '../types'

/** 문서: 접힌 한 줄 항목. 누르면 본문이 펼쳐지고 복사·.md 내려받기가 있다 */
export function DocumentFragment({ fragment }: FragmentProps<DocumentData>) {
  const doc = fragment.data
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  async function copy() {
    setCopied(await copyToClipboard(doc.markdown ?? ''))
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="rounded-card border border-line" data-fragment="document">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center gap-3 p-3 text-left">
        <FileText className="size-5 shrink-0 text-primary" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold text-ink">{doc.title}</p>
          <p className="text-xs text-ink-3">{doc.type_name} 초안 · 담당자 검토 후 사용</p>
        </div>
        <ChevronDown className={`size-5 shrink-0 text-ink-3 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
      </button>
      {open && (
        <div className="border-t border-line p-4">
          <div className="mb-4 flex gap-2">
            <Button variant="outline" size="sm" icon={<Copy className="size-4" />} onClick={copy}>
              {copied ? '복사됨' : '복사'}
            </Button>
            <Button size="sm" icon={<Download className="size-4" />} onClick={() => downloadTextFile(`${safeFilename(doc.title)}.md`, doc.markdown ?? '', 'text/markdown;charset=utf-8')}>
              .md 내려받기
            </Button>
          </div>
          <div className="space-y-4">
            {(doc.sections ?? []).map((s, i) => (
              <section key={i}>
                <h3 className="mb-1 text-sm font-bold text-ink">{s.heading}</h3>
                <p className="whitespace-pre-line text-[15px] leading-relaxed text-ink-2">{s.body}</p>
              </section>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
