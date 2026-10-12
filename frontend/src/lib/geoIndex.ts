/** 내부 ID(fac_id, cell_id) → 사람에게 보여줄 이름. 두 지역 GeoJSON 을 읽어 만든다 */
import { useMemo } from 'react'
import { useFacilitiesLayer, useTypesLayer } from '@/map/useGeoLayer'
import type { FacilityProps } from '@/types/geo'

export function useFacilityIndex() {
  const gn = useFacilitiesLayer('강남')
  const cc = useFacilitiesLayer('춘천')
  const index = useMemo(() => {
    const m = new Map<string, FacilityProps & { lat: number; lon: number }>()
    for (const col of [gn.data, cc.data]) {
      col?.features.forEach((f) => {
        const [lon, lat] = f.geometry.coordinates
        m.set(f.properties.fac_id, { ...f.properties, lat, lon })
      })
    }
    return m
  }, [gn.data, cc.data])
  return { index, loading: gn.isPending || cc.isPending }
}

export function useCellIndex() {
  const gn = useTypesLayer('강남')
  const cc = useTypesLayer('춘천')
  const index = useMemo(() => {
    const m = new Map<string, { emd_name: string; type?: string; region: '강남' | '춘천'; lat: number; lon: number }>()
    const add = (col: typeof gn.data, region: '강남' | '춘천') =>
      col?.features.forEach((f) => {
        const ring = f.geometry.coordinates[0] ?? []
        const lat = ring.reduce((a, c) => a + c[1], 0) / (ring.length || 1)
        const lon = ring.reduce((a, c) => a + c[0], 0) / (ring.length || 1)
        m.set(f.properties.cell_id, { emd_name: f.properties.emd_name, type: f.properties.type, region, lat, lon })
      })
    add(gn.data, '강남')
    add(cc.data, '춘천')
    return m
  }, [gn.data, cc.data])
  return { index, loading: gn.isPending || cc.isPending }
}
