import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { REGIONS, REGION_KEYS, type RegionKey } from '@/config'

export function RegionTabs({ value, onChange, size = 'sm' }: { value: RegionKey; onChange: (r: RegionKey) => void; size?: 'sm' | 'md' | 'lg' }) {
  return <SegmentedControl size={size} aria-label="지역" value={value} onChange={onChange} options={REGION_KEYS.map((r) => ({ value: r, label: REGIONS[r].label }))} className="shadow-card" />
}
