export function Spinner({ label = '불러오는 중', className = '' }: { label?: string; className?: string }) {
  return (
    <div role="status" className={`flex items-center gap-3 text-slate-600 ${className}`}>
      <span className="size-6 animate-spin rounded-full border-3 border-slate-300 border-t-blue-700" aria-hidden />
      <span>{label}</span>
    </div>
  )
}
