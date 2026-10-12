import { copyToClipboard } from '@/lib/download'
import type { Display } from '@/types/display'

/** 가족에게 공유할 글. 시민 화면 규칙대로 위험·유형 정보는 없다 (display 에 애초에 없음) */
export function answerToShareText(d: Display): string {
  const lines = [d.headline, '', ...d.details]
  if (d.caution) lines.push('', `※ ${d.caution}`)
  return lines.join('\n').trim()
}

export async function shareText(title: string, text: string): Promise<'shared' | 'copied' | 'failed'> {
  if (typeof navigator !== 'undefined' && 'share' in navigator) {
    try {
      await navigator.share({ title, text })
      return 'shared'
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return 'failed'
    }
  }
  return (await copyToClipboard(text)) ? 'copied' : 'failed'
}

/** 카카오맵 길찾기 링크 (앱·웹 모두 열림). 키 없이 쓸 수 있는 공개 URL */
export function directionsUrl(name: string, lat: number, lon: number): string {
  return `https://map.kakao.com/link/to/${encodeURIComponent(name)},${lat},${lon}`
}
