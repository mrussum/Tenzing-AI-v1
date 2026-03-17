import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPortfolioSummary } from '../api/client'
import Navbar from '../components/Navbar'
import KPICard from '../components/KPICard'

function fmt(n?: number) {
  if (n === undefined || n === null) return '—'
  if (n >= 1_000_000) return `£${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `£${(n / 1_000).toFixed(0)}K`
  return `£${n.toFixed(0)}`
}

export default function Briefing() {
  const [loadAI, setLoadAI] = useState(false)

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['portfolio-summary', loadAI],
    queryFn: () => fetchPortfolioSummary(loadAI),
    staleTime: loadAI ? Infinity : 30_000,
  })

  const kpis = summary?.kpis

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Leadership Briefing</h1>
            <p className="text-sm text-gray-500 mt-1">AI-powered portfolio narrative for executive review</p>
          </div>
          <div className="text-xs text-gray-400 text-right">
            {summary?.generated_at && (
              <p>Generated {new Date(summary.generated_at).toLocaleString()}</p>
            )}
          </div>
        </div>

        {/* KPIs */}
        {kpis && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard title="Total ARR" value={fmt(kpis.total_arr_gbp)} color="blue" icon="💷" />
            <KPICard title="Accounts at Risk" value={kpis.accounts_at_risk} color="red" icon="⚠️" />
            <KPICard title="Expansion Opps" value={kpis.expansion_opportunities} color="green" icon="🚀" />
            <KPICard title="Avg Health" value={kpis.avg_health_score} color="amber" icon="💚" />
          </div>
        )}

        {/* Priority summary */}
        {kpis && (
          <div className="card">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Portfolio Composition</p>
            <div className="grid grid-cols-5 gap-4 text-center">
              {[
                { label: 'Critical', count: kpis.critical_count, color: 'text-red-600', bg: 'bg-red-50' },
                { label: 'High', count: kpis.high_count, color: 'text-orange-600', bg: 'bg-orange-50' },
                { label: 'Medium', count: kpis.medium_count, color: 'text-yellow-600', bg: 'bg-yellow-50' },
                { label: 'Low', count: kpis.low_count, color: 'text-green-600', bg: 'bg-green-50' },
                { label: 'Paused', count: kpis.paused_count, color: 'text-gray-500', bg: 'bg-gray-50' },
              ].map(({ label, count, color, bg }) => (
                <div key={label} className={`${bg} rounded-xl py-4`}>
                  <p className={`text-2xl font-bold ${color}`}>{count}</p>
                  <p className="text-xs text-gray-500 mt-1">{label}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Briefing */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">AI Portfolio Narrative</h2>
            {!loadAI && !isLoading && (
              <button
                onClick={() => setLoadAI(true)}
                className="px-4 py-2 bg-tenzing-500 text-white text-sm font-medium rounded-lg hover:bg-tenzing-600 transition-colors"
              >
                Generate AI Briefing
              </button>
            )}
          </div>

          {isLoading && loadAI ? (
            <div className="flex flex-col items-center gap-3 py-12">
              <div className="w-8 h-8 border-4 border-tenzing-200 border-t-tenzing-500 rounded-full animate-spin" />
              <p className="text-sm text-gray-500">Generating leadership briefing with Claude...</p>
              <p className="text-xs text-gray-400">Analysing 60 accounts for cross-cutting themes</p>
            </div>
          ) : error ? (
            <p className="text-sm text-red-500">Failed to load briefing</p>
          ) : summary?.briefing ? (
            <div className="prose prose-sm max-w-none">
              {summary.briefing.split('\n').map((line, i) => {
                if (!line.trim()) return <div key={i} className="h-2" />
                return (
                  <p key={i} className="text-sm text-gray-700 leading-relaxed">
                    {line}
                  </p>
                )
              })}
            </div>
          ) : !loadAI ? (
            <div className="text-center py-12 text-gray-400 text-sm">
              <p className="text-3xl mb-3">📋</p>
              <p>Click "Generate AI Briefing" to create a portfolio narrative using Claude.</p>
              <p className="text-xs mt-1">This analyses all 60 accounts for cross-cutting themes and executive insights.</p>
            </div>
          ) : null}
        </div>
      </main>
    </div>
  )
}
