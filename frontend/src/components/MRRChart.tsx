import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'

interface Props {
  current?: number | null
  ago?: number | null
}

function fmtGBP(v: number) {
  if (v >= 1_000_000) return `£${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000) return `£${(v / 1_000).toFixed(1)}K`
  return `£${v.toFixed(0)}`
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700">{payload[0].payload.period}</p>
      <p className="text-gray-600">{fmtGBP(payload[0].value)}</p>
    </div>
  )
}

export default function MRRChart({ current, ago }: Props) {
  if (current == null && ago == null) return null

  const cur  = current ?? 0
  const prev = ago ?? 0
  const trend = cur - prev
  const trendPct = prev !== 0 ? ((trend / prev) * 100).toFixed(1) : null

  const data = [
    { period: '3 months ago', value: prev, fill: '#94a3b8' },
    { period: 'Current',      value: cur,  fill: trend >= 0 ? '#22c55e' : '#ef4444' },
  ]

  const yMin = Math.min(prev, cur) * 0.92
  const yMax = Math.max(prev, cur) * 1.08

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-gray-400">MRR comparison</p>
        {trendPct !== null && (
          <span className={`text-xs font-semibold ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {trend >= 0 ? '▲' : '▼'} {Math.abs(Number(trendPct))}% vs 3m ago
          </span>
        )}
      </div>
      <div className="h-28">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barSize={44} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
            <XAxis
              dataKey="period"
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis domain={[yMin, yMax]} hide />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
            <ReferenceLine y={prev} stroke="#cbd5e1" strokeDasharray="3 3" />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
