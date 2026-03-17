interface Props {
  title: string
  value: string | number
  subtitle?: string
  color?: 'blue' | 'red' | 'green' | 'amber'
  icon?: string
}

const COLOR_MAP: Record<string, string> = {
  blue: 'text-tenzing-500',
  red: 'text-red-500',
  green: 'text-green-600',
  amber: 'text-amber-500',
}

export default function KPICard({ title, value, subtitle, color = 'blue', icon }: Props) {
  return (
    <div className="card flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <p className={`text-3xl font-bold tabular-nums ${COLOR_MAP[color]}`}>{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
    </div>
  )
}
