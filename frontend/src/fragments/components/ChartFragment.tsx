import type { BarChartData } from '@/types/display'
import type { FragmentProps } from '../types'

/**
 * 개입안 비교 막대그래프. 한 계열(해소되는 동네 수)이라 한 가지 색만 쓰고 범례는 두지 않는다.
 * 전체(total) 를 연한 트랙으로 깔고 값은 막대 끝에 직접 적는다. 표 보기도 함께 둔다.
 */
export function ChartFragment({ fragment, mode }: FragmentProps<BarChartData>) {
  if (mode !== 'admin') return null
  const chart = fragment.data
  if (!chart || chart.type !== 'bar' || !Array.isArray(chart.items)) return null
  const max = Math.max(chart.total || 0, ...chart.items.map((i) => i.value))
  return (
    <figure className="rounded-2xl border border-slate-200 bg-white p-4" data-fragment="chart">
      <figcaption className="mb-3 font-semibold text-slate-900">{chart.title}</figcaption>
      <ol className="space-y-2">
        {chart.items.map((item) => {
          const pct = max > 0 ? (item.value / max) * 100 : 0
          return (
            <li key={item.label} className="group grid grid-cols-[minmax(7rem,30%)_1fr] items-center gap-3 text-sm" title={`${item.label}: ${item.value}${chart.unit} 해소, ${item.remaining}${chart.unit} 남음`}>
              <span className="truncate text-slate-700">{item.label}</span>
              <div className="relative h-7 rounded-md bg-slate-100">
                <div
                  className="absolute inset-y-0 left-0 rounded-md bg-blue-700 transition-[filter] group-hover:brightness-110"
                  style={{ width: `${Math.max(pct, item.value > 0 ? 1 : 0)}%` }}
                  aria-hidden
                />
                <span className="absolute inset-y-0 flex items-center pl-2 text-xs font-semibold tabular-nums" style={{ left: `${pct}%` }}>
                  <span className={pct > 70 ? '-translate-x-full pr-2 pl-0 text-white' : 'text-slate-900'}>
                    {item.value}
                    {chart.unit}
                  </span>
                </span>
              </div>
            </li>
          )
        })}
      </ol>
      <p className="mt-2 text-xs text-slate-500">
        기준 동네 {chart.total}
        {chart.unit}. 막대는 해소되는 수, 나머지는 남는 수입니다.
      </p>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-slate-600">표로 보기</summary>
        <table className="mt-2 w-full text-left">
          <thead className="text-slate-500">
            <tr>
              <th className="py-1 pr-2 font-medium">개입안</th>
              <th className="py-1 pr-2 font-medium">해소</th>
              <th className="py-1 font-medium">남음</th>
            </tr>
          </thead>
          <tbody>
            {chart.items.map((i) => (
              <tr key={i.label} className="border-t border-slate-100">
                <td className="py-1 pr-2">{i.label}</td>
                <td className="py-1 pr-2 tabular-nums">
                  {i.value}
                  {chart.unit}
                </td>
                <td className="py-1 tabular-nums">
                  {i.remaining}
                  {chart.unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
