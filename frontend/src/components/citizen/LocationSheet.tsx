import { useState } from 'react'
import { CircleMarker, useMapEvents } from 'react-leaflet'
import { LocateFixed, MapPin, Search } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { Sheet } from '@/components/ui/Sheet'
import { REGIONS, REGION_KEYS, regionOf, type RegionKey } from '@/config'
import { geocodeAddress, reverseGeocode, type GeocodeResult } from '@/features/citizen/geocode'
import type { LocationChoice } from '@/features/citizen/sessionContext'
import { BaseMap } from '@/map'

function ClickCatcher({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) })
  return null
}

export interface LocationSheetProps {
  open: boolean
  onClose: () => void
  value: LocationChoice | null
  onChange: (l: LocationChoice | null) => void
}

/** 위치 변경 시트: 지금 있는 곳 / 지도에서 고르기 / 주소 입력. 위치는 저장하지 않는다 */
export function LocationSheet({ open, onClose, value, onChange }: LocationSheetProps) {
  const [mode, setMode] = useState<'map' | 'address' | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodeResult[]>([])

  function useGps() {
    if (!('geolocation' in navigator)) return setError('이 기기에서는 위치를 가져올 수 없어요. 지도에서 골라 주세요.')
    setBusy(true)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setBusy(false)
        const { latitude: lat, longitude: lon } = pos.coords
        onChange({ lat, lon, label: '지금 있는 곳', source: 'gps' })
        if (!regionOf(lat, lon)) setError('지금 계신 곳은 서비스 지역(강남구·춘천시) 밖이에요. 지도나 주소로 골라 주세요.')
        else onClose()
      },
      (err) => {
        setBusy(false)
        setError(err.code === err.PERMISSION_DENIED ? '위치 사용이 허용되지 않았어요. 지도에서 골라 주세요.' : '위치를 가져오지 못했어요.')
      },
      { timeout: 10000, maximumAge: 60000 },
    )
  }

  async function pickOnMap(lat: number, lon: number) {
    onChange({ lat, lon, label: '지도에서 고른 곳', source: 'map' })
    const name = await reverseGeocode(lat, lon)
    if (name) onChange({ lat, lon, label: name, source: 'map' })
  }

  async function search() {
    const q = query.trim()
    if (!q) return
    setBusy(true)
    setError(null)
    try {
      const rows = await geocodeAddress(q)
      setResults(rows)
      if (rows.length === 0) setError('주소를 찾지 못했어요. 동 이름이나 도로명을 넣어 보세요.')
    } catch (e) {
      setError(e instanceof Error ? e.message : '주소를 찾지 못했어요.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title="어디 주변을 찾을까요?">
      <div className="space-y-3">
        {value && (
          <p className="text-sm text-ink-3">
            지금: <span className="font-semibold text-ink">{value.label}</span>
          </p>
        )}
        <div className="grid gap-2">
          <Button variant="outline" size="lg" className="justify-start" icon={<LocateFixed className="size-5 text-primary" />} onClick={useGps} loading={busy && mode === null}>
            지금 있는 곳
          </Button>
          <Button variant={mode === 'map' ? 'fill' : 'outline'} size="lg" className="justify-start" icon={<MapPin className="size-5" />} onClick={() => setMode(mode === 'map' ? null : 'map')}>
            지도에서 고르기
          </Button>
          <Button variant={mode === 'address' ? 'fill' : 'outline'} size="lg" className="justify-start" icon={<Search className="size-5" />} onClick={() => setMode(mode === 'address' ? null : 'address')}>
            주소 입력
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-sm text-amber-ink">
            {error}
          </p>
        )}

        {mode === 'map' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm text-ink-2">지도를 눌러 동네를 골라 주세요.</p>
              <SegmentedControl size="sm" options={REGION_KEYS.map((r) => ({ value: r, label: REGIONS[r].label }))} value={region} onChange={setRegion} aria-label="지역" />
            </div>
            <BaseMap region={region} className="h-64" scrollWheelZoom={false}>
              <ClickCatcher onPick={pickOnMap} />
              {value && <CircleMarker center={[value.lat, value.lon]} radius={9} pathOptions={{ color: '#fff', fillColor: '#1d4ed8', fillOpacity: 1, weight: 3 }} />}
            </BaseMap>
            <Button size="lg" className="w-full" disabled={!value} onClick={onClose} data-testid="location-done">
              이 위치로 찾기
            </Button>
          </div>
        )}

        {mode === 'address' && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), search())}
                placeholder={`예: ${REGIONS[region].label} 00동 00로 12`}
                aria-label="주소"
                className="min-w-0 flex-1 rounded-btn border border-line-strong px-3 py-3 text-base"
              />
              <Button onClick={search} loading={busy}>
                찾기
              </Button>
            </div>
            {results.length > 0 && (
              <ul className="divide-y divide-line">
                {results.map((r) => (
                  <li key={`${r.lat},${r.lon}`}>
                    <button
                      type="button"
                      className="w-full py-3 text-left text-base hover:bg-canvas"
                      onClick={() => {
                        onChange({ lat: r.lat, lon: r.lon, label: r.label.split(',').slice(0, 3).join(','), source: 'address' })
                        setResults([])
                        onClose()
                      }}
                    >
                      {r.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </Sheet>
  )
}
