import type { BarChartData } from '@/types/display'
import type { FragmentProps } from '../types'

/** 개입안 비교 막대그래프. 한 계열이라 한 색, 범례 없음, 값은 직접 표기. 표 보기는 접어 둔다 */
export function ChartFragment({ fragment, mode }: FragmentProps<BarChartData>) {
  if (mode !== 'admin') return null
  const chart = fragment.data
  if (!chart || chart.type !== 'bar' || !Array.isArray(chart.items)) return null
  const max = Math.max(chart.total || 0, ...chart.items.map((i) => i.value))
  return (
    <figure data-fragment="chart">
      <figcaption className="mb-2 text-sm font-semibold text-ink">{chart.title}</figcaption>
      <ol className="space-y-1.5">
        {chart.items.map((item) => {
          const pct = max > 0 ? (item.value / max) * 100 : 0
          return (
            <li key={item.label} className="group grid grid-cols-[minmax(6rem,32%)_1fr] items-center gap-3 text-sm" title={`${item.label}: ${item.value}${chart.unit} 해소, ${item.remaining}${chart.unit} 남음`}>
              <span className="truncate text-ink-2">{item.label}</span>
              <div className="relative h-6 rounded-[6px] bg-canvas">
                <div className="absolute inset-y-0 left-0 rounded-[6px] bg-primary group-hover:brightness-110" style={{ width: `${Math.max(pct, item.value > 0 ? 1 : 0)}%` }} aria-hidden />
                <span className="absolute inset-y-0 flex items-center whitespace-nowrap text-xs font-semibold tabular-nums" style={{ left: `${pct}%` }}>
                  <span className={pct > 70 ? '-translate-x-full pr-2 text-white' : 'pl-2 text-ink'}>
                    {item.value}
                    {chart.unit}
                  </span>
                </span>
              </div>
            </li>
          )
        })}
      </ol>
      <p className="mt-1.5 text-xs text-ink-3">
        기준 동네 {chart.total}
        {chart.unit}. 막대는 해소되는 수, 나머지는 남는 수.
      </p>
      <details className="mt-1 text-sm">
        <summary className="cursor-pointer text-ink-3">표로 보기</summary>
        <table className="mt-1 w-full text-left text-sm">
          <thead className="text-ink-3">
            <tr>
              <th className="py-1 pr-2 font-medium">개입안</th>
              <th className="py-1 pr-2 font-medium">해소</th>
              <th className="py-1 font-medium">남음</th>
            </tr>
          </thead>
          <tbody>
            {chart.items.map((i) => (
              <tr key={i.label} className="border-t border-line">
                <td className="py-1 pr-2">{i.label}</td>
                <td className="py-1 pr-2 tabular-nums">{i.value}{chart.unit}</td>
                <td className="py-1 tabular-nums">{i.remaining}{chart.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
