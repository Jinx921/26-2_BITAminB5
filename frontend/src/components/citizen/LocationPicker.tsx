import { useState } from 'react'
import { CircleMarker, useMapEvents } from 'react-leaflet'
import { Button } from '@/components/ui/Button'
import { REGIONS, regionOf, type RegionKey } from '@/config'
import { geocodeAddress, reverseGeocode, type GeocodeResult } from '@/features/citizen/geocode'
import type { LocationChoice } from '@/features/citizen/session'
import { BaseMap } from '@/map'
import { RegionTabs } from '@/components/map/RegionTabs'

/** 지도 클릭을 받아 위치를 고른다 */
function ClickCatcher({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) })
  return null
}

export interface LocationPickerProps {
  value: LocationChoice | null
  onChange: (l: LocationChoice | null) => void
}

/**
 * 찾을 위치 고르기: 지금 있는 곳(GPS) / 지도에서 고르기 / 주소 입력.
 * 위치는 저장하지 않고 질문에만 쓴다.
 */
export function LocationPicker({ value, onChange }: LocationPickerProps) {
  const [mode, setMode] = useState<'none' | 'map' | 'address'>('none')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [region, setRegion] = useState<RegionKey>('춘천')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodeResult[]>([])

  function useGps() {
    if (!('geolocation' in navigator)) {
      setError('이 기기에서는 위치를 가져올 수 없어요. 지도에서 골라 주세요.')
      return
    }
    setBusy(true)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setBusy(false)
        const { latitude: lat, longitude: lon } = pos.coords
        onChange({ lat, lon, label: '지금 있는 곳', source: 'gps' })
        if (!regionOf(lat, lon)) setError('지금 계신 곳은 서비스 지역(강남구·춘천시) 밖이에요. 지도나 주소로 골라 주세요.')
        setMode('none')
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-lg font-semibold">어디 주변을 찾을까요?</span>
        {value && (
          <span className="rounded-full bg-blue-50 px-3 py-1 text-base text-blue-800">
            {value.label}
            <button type="button" className="ml-2 font-bold" aria-label="위치 지우기" onClick={() => onChange(null)}>
              ×
            </button>
          </span>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <Button size="lg" variant={value?.source === 'gps' ? 'primary' : 'secondary'} onClick={useGps} loading={busy && mode === 'none'}>
          지금 있는 곳
        </Button>
        <Button size="lg" variant={mode === 'map' ? 'primary' : 'secondary'} onClick={() => setMode(mode === 'map' ? 'none' : 'map')}>
          지도에서 고르기
        </Button>
        <Button size="lg" variant={mode === 'address' ? 'primary' : 'secondary'} onClick={() => setMode(mode === 'address' ? 'none' : 'address')}>
          주소 입력
        </Button>
      </div>
      {error && (
        <p role="alert" className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
          {error}
        </p>
      )}

      {mode === 'map' && (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-slate-700">지도를 눌러 동네를 골라 주세요.</p>
            <RegionTabs value={region} onChange={setRegion} />
          </div>
          <BaseMap region={region} className="h-72" scrollWheelZoom={false}>
            <ClickCatcher onPick={pickOnMap} />
            {value && <CircleMarker center={[value.lat, value.lon]} radius={10} pathOptions={{ color: '#1d4ed8', fillColor: '#3b82f6', fillOpacity: 0.9 }} />}
          </BaseMap>
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
              className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-lg"
            />
            <Button size="lg" onClick={search} loading={busy}>
              찾기
            </Button>
          </div>
          {results.length > 0 && (
            <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
              {results.map((r) => (
                <li key={`${r.lat},${r.lon}`}>
                  <button
                    type="button"
                    className="w-full px-4 py-3 text-left text-base hover:bg-slate-50"
                    onClick={() => {
                      onChange({ lat: r.lat, lon: r.lon, label: r.label.split(',').slice(0, 3).join(','), source: 'address' })
                      setResults([])
                      setMode('none')
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
  )
}
