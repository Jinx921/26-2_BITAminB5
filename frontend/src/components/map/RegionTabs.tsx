import { REGIONS, REGION_KEYS, type RegionKey } from '@/config'

export function RegionTabs({ value, onChange, size = 'md' }: { value: RegionKey; onChange: (r: RegionKey) => void; size?: 'md' | 'lg' }) {
  return (
    <div role="tablist" aria-label="지역" className="inline-flex rounded-xl border border-slate-300 bg-white p-1">
      {REGION_KEYS.map((r) => (
        <button
          key={r}
          role="tab"
          type="button"
          aria-selected={value === r}
          onClick={() => onChange(r)}
          className={`rounded-lg px-4 font-semibold ${size === 'lg' ? 'py-3 text-lg' : 'py-1.5 text-sm'} ${value === r ? 'bg-blue-700 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
        >
          {REGIONS[r].label}
        </button>
      ))}
    </div>
  )
}
