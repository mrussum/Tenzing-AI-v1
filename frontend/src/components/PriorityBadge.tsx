interface Props {
  priority: string
  size?: 'sm' | 'md'
}

const DOT: Record<string, string> = {
  Critical: 'bg-red-500',
  High: 'bg-orange-500',
  Medium: 'bg-yellow-400',
  Low: 'bg-green-500',
  Paused: 'bg-gray-400',
}

export default function PriorityBadge({ priority, size = 'md' }: Props) {
  const cls =
    priority === 'Critical'
      ? 'badge-critical'
      : priority === 'High'
        ? 'badge-high'
        : priority === 'Medium'
          ? 'badge-medium'
          : priority === 'Low'
            ? 'badge-low'
            : 'badge-paused'

  return (
    <span className={cls}>
      <span className={`w-1.5 h-1.5 rounded-full ${DOT[priority] ?? 'bg-gray-400'} mr-1.5 inline-block`} />
      {priority}
    </span>
  )
}
