interface Props { sentiment?: string }

const MAP: Record<string, string> = {
  Positive: 'bg-green-50 text-green-700',
  Neutral: 'bg-gray-100 text-gray-600',
  Negative: 'bg-red-50 text-red-700',
  Mixed: 'bg-yellow-50 text-yellow-700',
}

const EMOJI: Record<string, string> = {
  Positive: '😊',
  Neutral: '😐',
  Negative: '😟',
  Mixed: '🤔',
}

export default function SentimentChip({ sentiment }: Props) {
  if (!sentiment) return <span className="text-xs text-gray-400">No sentiment data</span>
  const cls = MAP[sentiment] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {EMOJI[sentiment] ?? ''} {sentiment}
    </span>
  )
}
