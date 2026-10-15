import type { HTMLAttributes, ReactNode } from 'react'

/** 실제로 묶어야 하는 단위에만 쓴다 (장소 카드, 강조 패널). 안에 또 카드를 넣지 않는다 */
export function Card({ children, className = '', ...rest }: HTMLAttributes<HTMLDivElement> & { children: ReactNode }) {
  return (
    <div className={`rounded-card border border-line bg-surface p-4 ${className}`} {...rest}>
      {children}
    </div>
  )
}
