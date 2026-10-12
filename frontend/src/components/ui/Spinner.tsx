import { Loader2 } from 'lucide-react'

export function Spinner({ label = '불러오는 중', className = '' }: { label?: string; className?: string }) {
  return (
    <div role="status" className={`flex items-center gap-2 text-ink-3 ${className}`}>
      <Loader2 className="size-5 animate-spin" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  )
}
