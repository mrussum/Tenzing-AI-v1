interface Props { confidence: string; nullCount?: number }

const MAP: Record<string, string> = {
  High: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  Medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  Low: 'bg-red-50 text-red-700 border border-red-200',
}

export default function ConfidencePill({ confidence, nullCount }: Props) {
  const cls = MAP[confidence] ?? MAP['Medium']
  const title = nullCount !== undefined ? `${nullCount} signal fields missing` : undefined
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cls}`} title={title}>
      {confidence === 'Low' && <span>⚠</span>}
      {confidence} confidence
    </span>
  )
}
