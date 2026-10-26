import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

export interface SheetProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  /** 모바일은 아래에서 올라오는 시트, 데스크톱은 가운데 모달 */
  className?: string
}

/** 바텀 시트 / 모달. 자주 쓰지 않는 동작(위치 변경, 메뉴 등)을 넣는다 */
export function Sheet({ open, onClose, title, children, className = '' }: SheetProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-[2000] flex items-end justify-center sm:items-center" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="absolute inset-0 bg-navy/40" aria-label="닫기" onClick={onClose} />
      <div className={`relative max-h-[90dvh] w-full max-w-[430px] overflow-y-auto rounded-t-[20px] bg-surface p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] sm:rounded-card ${className}`}>
        <div className="mb-3 flex items-center justify-between">
          {title ? <h2 className="text-lg font-bold">{title}</h2> : <span />}
          <button type="button" onClick={onClose} aria-label="닫기" className="-mr-2 inline-flex size-11 items-center justify-center rounded-full text-ink-2 hover:bg-canvas">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  )
}
