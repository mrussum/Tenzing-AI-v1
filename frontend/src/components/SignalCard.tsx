interface Row { label: string; value: React.ReactNode }

interface Props {
  title: string
  icon?: string
  rows: Row[]
}

export default function SignalCard({ title, icon, rows }: Props) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        {icon && <span className="text-base">{icon}</span>}
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{title}</h3>
      </div>
      <dl className="space-y-2">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <dt className="text-gray-500 truncate">{label}</dt>
            <dd className="font-medium text-gray-900 ml-2 text-right">{value ?? <span className="text-gray-300">—</span>}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
