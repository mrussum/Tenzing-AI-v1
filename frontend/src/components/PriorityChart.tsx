import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts'
import type { PortfolioKPIs } from '../api/client'

interface Props {
  kpis: PortfolioKPIs
}

const TIERS = [
  { key: 'critical_count', label: 'Critical', fill: '#ef4444' },
  { key: 'high_count',     label: 'High',     fill: '#f97316' },
  { key: 'medium_count',   label: 'Medium',   fill: '#eab308' },
  { key: 'low_count',      label: 'Low',      fill: '#22c55e' },
  { key: 'paused_count',   label: 'Paused',   fill: '#94a3b8' },
]

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow px-3 py-2 text-xs">
      <p className="font-semibold" style={{ color: d.fill }}>{d.label}</p>
      <p className="text-gray-600">{d.value} account{d.value !== 1 ? 's' : ''}</p>
    </div>
  )
}

export default function PriorityChart({ kpis }: Props) {
  const data = TIERS.map(({ key, label, fill }) => ({
    label,
    fill,
    value: kpis[key as keyof PortfolioKPIs] as number,
  })).filter((d) => d.value > 0)

  return (
    <div className="h-36">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 8, left: 8, bottom: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40}>
            <LabelList
              dataKey="value"
              position="top"
              style={{ fontSize: 12, fontWeight: 700, fill: '#374151' }}
            />
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
