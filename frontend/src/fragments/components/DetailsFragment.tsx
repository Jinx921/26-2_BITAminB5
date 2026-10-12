import type { FragmentProps } from '../types'

const BULLET = /^\s*[-•·]\s+/

/** 문단 하나를 줄 단위로 나눠 "- " 목록 줄은 ul 로, 나머지는 p 로 그린다 (agent/README: 목록 줄의 줄바꿈을 살린다) */
function renderParagraph(text: string, key: number, big: boolean) {
  const lines = text.split('\n').map((l) => l.trimEnd()).filter((l) => l.trim() !== '')
  const blocks: { kind: 'p' | 'ul'; lines: string[] }[] = []
  for (const line of lines) {
    const isBullet = BULLET.test(line)
    const last = blocks[blocks.length - 1]
    if (isBullet) {
      if (last?.kind === 'ul') last.lines.push(line.replace(BULLET, ''))
      else blocks.push({ kind: 'ul', lines: [line.replace(BULLET, '')] })
    } else {
      if (last?.kind === 'p') last.lines.push(line)
      else blocks.push({ kind: 'p', lines: [line] })
    }
  }
  const textCls = big ? 'text-lg leading-relaxed' : 'leading-relaxed'
  return blocks.map((b, i) =>
    b.kind === 'ul' ? (
      <ul key={`${key}-${i}`} className={`list-disc space-y-1 pl-6 ${textCls}`}>
        {b.lines.map((l, j) => (
          <li key={j}>{l}</li>
        ))}
      </ul>
    ) : (
      <p key={`${key}-${i}`} className={textCls}>
        {b.lines.join(' ')}
      </p>
    ),
  )
}

export function DetailsFragment({ fragment, mode }: FragmentProps<string[]>) {
  const paragraphs = Array.isArray(fragment.data) ? fragment.data : [String(fragment.data)]
  return (
    <div className="space-y-3 text-slate-800" data-fragment="details">
      {paragraphs.map((p, i) => renderParagraph(p, i, mode === 'citizen'))}
    </div>
  )
}
