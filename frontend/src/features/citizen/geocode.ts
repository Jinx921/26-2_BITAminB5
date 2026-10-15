/** 주소 → 좌표. 카카오 키가 없어 OSM Nominatim 을 쓴다 (초당 1회 제한, 결과는 한국어 우선) */
export interface GeocodeResult {
  label: string
  lat: number
  lon: number
}

export async function geocodeAddress(query: string, signal?: AbortSignal): Promise<GeocodeResult[]> {
  const url = new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('q', query)
  url.searchParams.set('format', 'jsonv2')
  url.searchParams.set('countrycodes', 'kr')
  url.searchParams.set('limit', '5')
  url.searchParams.set('accept-language', 'ko')
  const res = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error('주소를 찾는 서버에 연결하지 못했어요.')
  const rows = (await res.json()) as { display_name: string; lat: string; lon: string }[]
  return rows.map((r) => ({ label: r.display_name, lat: Number(r.lat), lon: Number(r.lon) }))
}

/** 좌표 → 짧은 주소 (지도에서 고른 곳 이름 붙이기) */
export async function reverseGeocode(lat: number, lon: number, signal?: AbortSignal): Promise<string | null> {
  try {
    const url = new URL('https://nominatim.openstreetmap.org/reverse')
    url.searchParams.set('lat', String(lat))
    url.searchParams.set('lon', String(lon))
    url.searchParams.set('format', 'jsonv2')
    url.searchParams.set('accept-language', 'ko')
    url.searchParams.set('zoom', '16')
    const res = await fetch(url, { signal })
    if (!res.ok) return null
    const j = (await res.json()) as { address?: Record<string, string>; display_name?: string }
    const a = j.address ?? {}
    const parts = [a.city || a.county, a.borough || a.suburb || a.town || a.village, a.quarter || a.neighbourhood || a.road].filter(Boolean)
    return parts.length ? parts.join(' ') : (j.display_name ?? null)
  } catch {
    return null
  }
}
