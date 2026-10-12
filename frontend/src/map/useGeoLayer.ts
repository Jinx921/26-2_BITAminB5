import { useQuery } from '@tanstack/react-query'
import { api } from '@/api'
import type { RegionKey } from '@/config'

/** 시설 지도는 시민용 allowlist API 를 사용한다. 목업 모드만 public/geo fixture 를 읽는다. */
export function useFacilitiesLayer(region: RegionKey | null) {
  return useQuery({
    queryKey: ['geo', 'facilities', region],
    enabled: region !== null,
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: () => api.getFacilitiesMap(region!),
  })
}

export const useTypesLayer = (region: RegionKey | null, showExcluded = false) =>
  useQuery({
    queryKey: ['geo', 'admin', 'types', region, showExcluded],
    enabled: region !== null,
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: () => api.getAdminTypesMap(region!, showExcluded),
  })

export const useCandidatesLayer = (region: RegionKey | null) =>
  useQuery({
    queryKey: ['geo', 'admin', 'candidates', region],
    enabled: region !== null,
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: () => api.getAdminCandidatesMap(region!),
  })

export const useSimLayer = (region: RegionKey | null, k: 3 = 3, r: 1000 | 3000 = 1000) =>
  useQuery({
    queryKey: ['geo', 'admin', 'placements', region, k, r],
    enabled: region !== null,
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: () => api.getAdminPlacementsMap(region!, r, k),
  })
