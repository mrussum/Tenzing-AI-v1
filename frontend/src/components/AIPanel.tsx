import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAccountAnalysis, type AIAnalysis } from '../api/client'
import PriorityBadge from './PriorityBadge'
import ConfidencePill from './ConfidencePill'

interface Props {
  accountId: string
  deterministicPriority: string
  confidence: string
}

const OWNER_COLOR: Record<string, string> = {
  CSM:        'bg-purple-100 text-purple-700',
  Sales:      'bg-blue-100   text-blue-700',
  Leadership: 'bg-red-100    text-red-700',
}

export default function AIPanel({ accountId, deterministicPriority, confidence }: Props) {
  const [requested, setRequested] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const { data: ai, isLoading, error } = useQuery<AIAnalysis>({
    queryKey: ['account-analysis', accountId, refreshKey],
    queryFn: () => fetchAccountAnalysis(accountId, refreshKey > 0),
    enabled: requested,
    staleTime: Infinity,
  })

  if (!requested) {
    return (
      <div className="card border-dashed border-2 border-tenzing-100 flex flex-col items-center justify-center py-10 gap-3">
        <div className="text-center">
          <p className="text-gray-500 text-sm">AI analysis not yet loaded</p>
          <p className="text-xs text-gray-400 mt-1">
            Deterministic priority: <span className="font-semibold">{deterministicPriority}</span>
          </p>
        </div>
        <button
          onClick={() => setRequested(true)}
          className="mt-1 px-5 py-2 bg-tenzing-500 text-white rounded-lg text-sm font-medium hover:bg-tenzing-600 transition-colors"
        >
          Generate AI Analysis
        </button>
        <p className="text-xs text-gray-400">Powered by Claude Sonnet</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="card flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-tenzing-200 border-t-tenzing-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Analysing account with Claude…</p>
          <p className="text-xs text-gray-400">Synthesising all signals and notes</p>
        </div>
      </div>
    )
  }

  if (error || !ai) {
    return (
      <div className="card border border-red-200 bg-red-50 space-y-2">
        <p className="text-red-700 text-sm font-medium">AI analysis failed</p>
        <p className="text-red-500 text-xs">{(error as Error)?.message ?? 'Unknown error'}</p>
        <button
          onClick={() => { setRefreshKey((k) => k + 1) }}
          className="text-xs text-tenzing-500 hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (ai.error) {
    return (
      <div className="card border border-amber-200 bg-amber-50 space-y-2">
        <p className="text-amber-700 text-sm font-medium">AI service issue</p>
        <p className="text-amber-600 text-xs">{ai.error}</p>
        <p className="text-xs text-gray-500">Deterministic priority shown: <strong>{deterministicPriority}</strong></p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Priority header */}
      <div className="card">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <PriorityBadge priority={ai.priority} />
            <ConfidencePill confidence={ai.confidence} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Claude Sonnet</span>
            <button
              onClick={() => setRefreshKey((k) => k + 1)}
              title="Refresh analysis"
              className="text-gray-300 hover:text-tenzing-500 transition-colors text-sm"
            >
              ↻
            </button>
          </div>
        </div>
        <p className="text-sm text-gray-700 leading-relaxed">{ai.priority_reasoning}</p>
      </div>

      {/* Top risks */}
      {ai.top_risks.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Top Risks
          </h3>
          <ul className="space-y-3">
            {ai.top_risks.map((r, i) => (
              <li key={i} className="flex gap-3">
                <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-red-100 text-red-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-gray-800">{r.risk}</p>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{r.evidence}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Top opportunities */}
      {ai.top_opportunities.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Top Opportunities
          </h3>
          <ul className="space-y-3">
            {ai.top_opportunities.map((o, i) => (
              <li key={i} className="flex gap-3">
                <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-gray-800">{o.opportunity}</p>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{o.evidence}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommended actions */}
      {ai.recommended_actions.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Recommended Actions
          </h3>
          <ol className="space-y-3">
            {ai.recommended_actions.map((a, i) => (
              <li key={i} className="flex gap-3 items-start">
                <span className="mt-0.5 flex-shrink-0 text-xs font-bold text-gray-400 w-4">
                  {i + 1}.
                </span>
                <p className="flex-1 text-sm text-gray-800 leading-relaxed">{a.action}</p>
                <span
                  className={`flex-shrink-0 px-2 py-0.5 rounded text-xs font-semibold ${
                    OWNER_COLOR[a.owner] ?? 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {a.owner}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
