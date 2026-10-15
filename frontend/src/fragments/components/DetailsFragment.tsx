import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { FragmentProps } from '../types'

const BULLET = /^\s*[-•·]\s+/

/** 문단 하나를 줄 단위로 나눠 "- " 목록 줄은 ul 로, 나머지는 p 로 그린다 */
function renderParagraph(text: string, key: number, big: boolean) {
  const lines = text.split('\n').map((l) => l.trimEnd()).filter((l) => l.trim() !== '')
  const blocks: { kind: 'p' | 'ul'; lines: string[] }[] = []
  for (const line of lines) {
    const isBullet = BULLET.test(line)
    const last = blocks[blocks.length - 1]
    if (isBullet) {
      if (last?.kind === 'ul') last.lines.push(line.replace(BULLET, ''))
      else blocks.push({ kind: 'ul', lines: [line.replace(BULLET, '')] })
    } else if (last?.kind === 'p') last.lines.push(line)
    else blocks.push({ kind: 'p', lines: [line] })
  }
  const cls = big ? 'text-base leading-relaxed' : 'text-[15px] leading-relaxed'
  return blocks.map((b, i) =>
    b.kind === 'ul' ? (
      <ul key={`${key}-${i}`} className={`list-disc space-y-1 pl-5 ${cls}`}>
        {b.lines.map((l, j) => (
          <li key={j}>{l}</li>
        ))}
      </ul>
    ) : (
      <p key={`${key}-${i}`} className={cls}>
        {b.lines.join(' ')}
      </p>
    ),
  )
}

export function DetailsFragment({ fragment, mode, context }: FragmentProps<string[]>) {
  const paragraphs = Array.isArray(fragment.data) ? fragment.data : [String(fragment.data)]
  const [open, setOpen] = useState(false)
  const compact = mode === 'citizen' && context.compactDetails && paragraphs.length > 1

  if (compact) {
    return (
      <div className="text-ink-2" data-fragment="details">
        {renderParagraph(paragraphs[0], 0, true)}
        {open && <div className="mt-2 space-y-2">{paragraphs.slice(1).map((p, i) => renderParagraph(p, i + 1, true))}</div>}
        <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="mt-1 inline-flex min-h-11 items-center gap-1 text-base font-semibold text-primary">
          {open ? '접기' : '자세히'}
          <ChevronDown className={`size-4 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
        </button>
      </div>
    )
  }
  return (
    <div className="space-y-2 text-ink-2" data-fragment="details">
      {paragraphs.map((p, i) => renderParagraph(p, i, mode === 'citizen'))}
    </div>
  )
}
