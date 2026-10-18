import { useEffect, useRef, useState, type ReactNode } from 'react'
import { MoreHorizontal } from 'lucide-react'

export interface MenuItem {
  label: ReactNode
  onSelect: () => void
  danger?: boolean
}

/** 점 세 개 메뉴. 로그아웃처럼 자주 안 쓰는 동작을 넣는다. align: 펼친 상자를 버튼의 어느 쪽 끝에 맞출지 */
export function Menu({ items, label = '메뉴', header, align = 'right' }: { items: MenuItem[]; label?: string; header?: ReactNode; align?: 'left' | 'right' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-label={label} aria-expanded={open} onClick={() => setOpen((v) => !v)} className="inline-flex size-11 items-center justify-center rounded-full text-ink-2 hover:bg-canvas">
        <MoreHorizontal className="size-5" />
      </button>
      {open && (
        <div role="menu" className={`absolute ${align === 'left' ? 'left-0' : 'right-0'} z-30 mt-1 min-w-44 overflow-hidden rounded-card border border-line bg-surface py-1 shadow-card`}>
          {header && <div className="border-b border-line px-3 py-2 text-xs text-ink-3">{header}</div>}
          {items.map((it, i) => (
            <button
              key={i}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                it.onSelect()
              }}
              className={`block w-full px-3 py-2.5 text-left text-sm hover:bg-canvas ${it.danger ? 'text-danger' : 'text-ink'}`}
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
