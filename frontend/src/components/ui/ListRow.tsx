import type { HTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

/** 구분선만 있는 목록. 카드 대신 쓴다 */
export function List({ children, className = '', ...rest }: HTMLAttributes<HTMLUListElement> & { children: ReactNode }) {
  return (
    <ul className={`divide-y divide-line ${className}`} {...rest}>
      {children}
    </ul>
  )
}

export interface ListRowProps {
  leading?: ReactNode
  title: ReactNode
  subtitle?: ReactNode
  trailing?: ReactNode
  to?: string
  onClick?: () => void
  selected?: boolean
  muted?: boolean
  className?: string
  children?: ReactNode
}

export function ListRow({ leading, title, subtitle, trailing, to, onClick, selected, muted, className = '', children }: ListRowProps) {
  const inner = (
    <>
      {leading && <div className="shrink-0">{leading}</div>}
      <div className="min-w-0 flex-1">
        <div className={`font-semibold ${muted ? 'text-ink-3' : 'text-ink'}`}>{title}</div>
        {subtitle && <div className="mt-0.5 text-sm text-ink-3">{subtitle}</div>}
        {children}
      </div>
      {trailing && <div className="shrink-0 text-sm text-ink-3">{trailing}</div>}
    </>
  )
  const base = `flex items-center gap-3 py-3 ${selected ? 'bg-primary-soft' : ''} ${muted ? 'opacity-60' : ''} ${className}`
  if (to) {
    return (
      <li>
        <Link to={to} className={`${base} -mx-2 rounded-[8px] px-2 hover:bg-canvas`}>
          {inner}
        </Link>
      </li>
    )
  }
  if (onClick) {
    return (
      <li>
        <button type="button" onClick={onClick} className={`${base} -mx-2 w-[calc(100%+1rem)] rounded-[8px] px-2 text-left hover:bg-canvas`}>
          {inner}
        </button>
      </li>
    )
  }
  return <li className={base}>{inner}</li>
}
