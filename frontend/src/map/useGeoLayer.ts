import { useQuery } from '@tanstack/react-query'
import type { FeatureCollection } from 'geojson'
import { env } from '@/config'
import type { RegionKey } from '@/config'
import type { FacilityCollection, GridCollection } from '@/types/geo'

/** public/geo (또는 VITE_GEO_BASE_URL) 의 GeoJSON 파일을 읽는다. 파일은 바뀌지 않으므로 캐시를 끝까지 쓴다 */
export function useGeoLayer<T extends FeatureCollection>(name: string | null) {
  return useQuery({
    queryKey: ['geo', name],
    enabled: name !== null,
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async (): Promise<T> => {
      const res = await fetch(`${env.geoBaseUrl}/${encodeURIComponent(name!)}.geojson`)
      if (!res.ok) throw new Error(`지도 파일을 불러오지 못했습니다 (${name}.geojson, ${res.status})`)
      return (await res.json()) as T
    },
  })
}

export const useTypesLayer = (region: RegionKey | null) => useGeoLayer<GridCollection>(region ? `types_${region}` : null)
export const useCandidatesLayer = (region: RegionKey | null) => useGeoLayer<GridCollection>(region ? `candidates_${region}` : null)
export const useSimLayer = (region: RegionKey | null, k = 3, r = 1000) =>
  useGeoLayer<GridCollection>(region ? `sim_${region}_k${k}_r${r}` : null)
export const useFacilitiesLayer = (region: RegionKey | null) =>
  useGeoLayer<FacilityCollection>(region ? `facilities_${region}` : null)
