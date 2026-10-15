/** 환경 변수와 지역 상수를 한 곳에 모은다. */

// Vite 밖(테스트 스크립트 등)에서 import 될 때도 깨지지 않게 한다
const viteEnv: ImportMetaEnv = import.meta.env ?? {}

export const env = {
  apiBaseUrl: (viteEnv.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, ''),
  useMock: viteEnv.VITE_USE_MOCK === 'true',
  geoBaseUrl: (viteEnv.VITE_GEO_BASE_URL ?? '/geo').replace(/\/$/, ''),
} as const

export type RegionKey = '강남' | '춘천'

export interface RegionConfig {
  key: RegionKey
  /** 사람에게 보여주는 이름 */
  label: string
  /** 지도 초기 중심 [lat, lon] */
  center: [number, number]
  /** 지도 범위 [[남, 서], [북, 동]] (lat, lon). 이 밖의 시설 점은 그리지 않는다 */
  bbox: [[number, number], [number, number]]
  /** 주민센터·구청 대표 전화. 값은 확인 후 채운다 (비어 있으면 버튼을 숨긴다) */
  communityCenterPhone: string
  communityCenterName: string
}

export const REGIONS: Record<RegionKey, RegionConfig> = {
  강남: {
    key: '강남',
    label: '서울 강남구',
    center: [37.4959, 127.0664],
    bbox: [
      [37.44, 126.99],
      [37.56, 127.14],
    ],
    communityCenterPhone: '',
    communityCenterName: '강남구청',
  },
  춘천: {
    key: '춘천',
    label: '춘천시',
    center: [37.8813, 127.7298],
    bbox: [
      [37.55, 127.4],
      [38.2, 128.1],
    ],
    communityCenterPhone: '',
    communityCenterName: '춘천시청',
  },
}

export const REGION_KEYS = Object.keys(REGIONS) as RegionKey[]

/** 좌표가 어느 지역 범위에 드는지. 둘 다 아니면 null */
export function regionOf(lat: number, lon: number): RegionKey | null {
  for (const r of REGION_KEYS) {
    const [[s, w], [n, e]] = REGIONS[r].bbox
    if (lat >= s && lat <= n && lon >= w && lon <= e) return r
  }
  return null
}

/** 에이전트 답변 대기 안내용. README 기준 15~35초, 문서는 1분 안팎 */
export const QUESTION_WAIT_HINT_SECONDS = 30
