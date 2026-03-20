import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postDecision, type Decision } from '../api/client'

interface Props {
  accountId: string
  decisions: Decision[]
}

export default function DecisionRecorder({ accountId, decisions }: Props) {
  const [text, setText] = useState('')
  const [owner, setOwner] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => postDecision(accountId, text, owner || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account', accountId] })
      setText('')
      setOwner('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return
    mutation.mutate()
  }

  return (
    <div className="card">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Decision Recorder</h3>

      {/* Existing decisions */}
      {decisions.length > 0 && (
        <ul className="mb-4 space-y-2">
          {decisions.map((d) => (
            <li key={d.id} className="text-sm bg-gray-50 rounded-lg p-3 border border-gray-100">
              <p className="text-gray-800">{d.text}</p>
              <div className="flex items-center gap-2 mt-1">
                {d.decided_by && (
                  <span className="text-xs text-gray-500 font-medium">{d.decided_by}</span>
                )}
                <span className="text-xs text-gray-400">
                  {new Date(d.timestamp).toLocaleString()}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* New decision form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Record a decision or action taken on this account..."
          rows={3}
          className="w-full text-sm border border-gray-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-tenzing-400 focus:border-transparent"
        />
        <div className="flex items-center gap-3">
          <input
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="Decided by (optional)"
            className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-tenzing-400"
          />
          <button
            type="submit"
            disabled={!text.trim() || mutation.isPending}
            className="px-4 py-2 bg-tenzing-500 text-white text-sm font-medium rounded-lg hover:bg-tenzing-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? 'Saving...' : 'Save Decision'}
          </button>
        </div>
        {mutation.isError && (
          <p className="text-xs text-red-600">Failed to save decision. Please try again.</p>
        )}
      </form>
    </div>
  )
}
