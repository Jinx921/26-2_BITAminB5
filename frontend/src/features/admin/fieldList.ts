/** 현장 확인 목록: 에이전트 응답(checks 레이어) → 전달용 목록, 텍스트·마크다운 변환 */
import { regionOf } from '@/config'
import type { FieldCheckList } from '@/types/api'
import type { Display } from '@/types/display'

export function displayToFieldCheckList(d: Display): FieldCheckList | null {
  if (d.map?.layer !== 'checks' || d.map.points.length === 0) return null
  const cells = d.map.points.slice().sort((a, b) => a.order - b.order)
  const first = cells[0]
  return { region: regionOf(first.lat, first.lon), headline: d.headline, created_at: new Date().toISOString(), cells }
}

/** 담당자에게 메신저로 보낼 수 있는 글. cell_id 는 쓰지 않는다 */
export function fieldListToText(list: FieldCheckList): string {
  const lines = [`[현장 확인 목록] ${list.region ?? ''} · ${new Date(list.created_at).toLocaleDateString('ko-KR')}`, list.headline, '']
  for (const c of list.cells) {
    lines.push(`${c.order}. ${c.emd_name} (${c.level})`)
    c.questions.forEach((q) => lines.push(`   - ${q}`))
  }
  lines.push('', '모든 동네 공통: 이 동네에 지원이 필요해 보이나요?')
  return lines.join('\n')
}

export function fieldListToMarkdown(list: FieldCheckList): string {
  const lines = [`# 현장 확인 목록 · ${list.region ?? ''}`, '', `*${new Date(list.created_at).toLocaleString('ko-KR')} 생성*`, '', list.headline, '']
  for (const c of list.cells) {
    lines.push(`## ${c.order}. ${c.emd_name} — ${c.level}`, '')
    c.questions.forEach((q) => lines.push(`- [ ] ${q}`))
    lines.push('- [ ] (공통) 이 동네에 지원이 필요해 보이나요?', '')
  }
  return lines.join('\n')
}
