interface Props { trend?: number; current?: number; ago?: number }

export default function MRRTrend({ trend, current, ago }: Props) {
  if (trend === undefined || trend === null) {
    return <span className="text-xs text-gray-400">—</span>
  }
  const pct = (trend * 100).toFixed(1)
  const up = trend > 0
  const neutral = Math.abs(trend) < 0.005
  const color = neutral ? 'text-gray-500' : up ? 'text-green-600' : 'text-red-600'
  const arrow = neutral ? '→' : up ? '↑' : '↓'
  return (
    <span className={`inline-flex items-center gap-0.5 text-sm font-semibold tabular-nums ${color}`}>
      {arrow} {up && '+'}{pct}%
    </span>
  )
}
