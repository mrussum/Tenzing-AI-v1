interface Props {
  value: number       // 0-100
  type: 'risk' | 'opportunity' | 'health'
  showLabel?: boolean
}

const COLORS: Record<string, { bar: string; text: string }> = {
  risk: { bar: 'bg-red-400', text: 'text-red-700' },
  opportunity: { bar: 'bg-blue-400', text: 'text-blue-700' },
  health: { bar: 'bg-green-400', text: 'text-green-700' },
}

export default function ScoreBar({ value, type, showLabel = true }: Props) {
  const { bar, text } = COLORS[type]
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 bg-gray-100 rounded-full h-1.5 min-w-0">
        <div
          className={`h-1.5 rounded-full ${bar} transition-all`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      {showLabel && (
        <span className={`text-xs font-semibold tabular-nums w-8 text-right ${text}`}>
          {Math.round(value)}
        </span>
      )}
    </div>
  )
}
