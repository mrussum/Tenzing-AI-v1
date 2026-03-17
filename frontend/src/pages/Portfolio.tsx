import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchAccounts, fetchPortfolioSummary, fetchFilterOptions, type AccountSummary } from '../api/client'
import Navbar from '../components/Navbar'
import KPICard from '../components/KPICard'
import PriorityBadge from '../components/PriorityBadge'
import ScoreBar from '../components/ScoreBar'
import MRRTrend from '../components/MRRTrend'
import ConfidencePill from '../components/ConfidencePill'
import SentimentChip from '../components/SentimentChip'

function fmt(n?: number) {
  if (n === undefined || n === null) return '—'
  if (n >= 1_000_000) return `£${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `£${(n / 1_000).toFixed(0)}K`
  return `£${n.toFixed(0)}`
}

export default function Portfolio() {
  const [region, setRegion] = useState('')
  const [segment, setSegment] = useState('')
  const [lifecycle, setLifecycle] = useState('')
  const [owner, setOwner] = useState('')
  const [search, setSearch] = useState('')

  const filters = {
    region: region || undefined,
    segment: segment || undefined,
    lifecycle_stage: lifecycle || undefined,
    owner: owner || undefined,
  }

  const { data: accounts = [], isLoading, error } = useQuery({
    queryKey: ['accounts', filters],
    queryFn: () => fetchAccounts(filters),
  })

  const { data: summary } = useQuery({
    queryKey: ['portfolio-summary'],
    queryFn: () => fetchPortfolioSummary(false),
  })

  const { data: filterOptions } = useQuery({
    queryKey: ['filter-options'],
    queryFn: fetchFilterOptions,
  })

  const filtered = search
    ? accounts.filter((a) =>
        a.account_name.toLowerCase().includes(search.toLowerCase()) ||
        (a.region ?? '').toLowerCase().includes(search.toLowerCase()) ||
        (a.segment ?? '').toLowerCase().includes(search.toLowerCase())
      )
    : accounts

  const kpis = summary?.kpis

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* KPI cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Total ARR"
            value={kpis ? fmt(kpis.total_arr_gbp) : '…'}
            color="blue"
            icon="💷"
          />
          <KPICard
            title="Accounts at Risk"
            value={kpis ? kpis.accounts_at_risk : '…'}
            subtitle="risk score > 50"
            color="red"
            icon="⚠️"
          />
          <KPICard
            title="Expansion Opps"
            value={kpis ? kpis.expansion_opportunities : '…'}
            subtitle="opportunity score > 50"
            color="green"
            icon="🚀"
          />
          <KPICard
            title="Avg Health Score"
            value={kpis ? `${kpis.avg_health_score}` : '…'}
            subtitle="out of 100"
            color="amber"
            icon="💚"
          />
        </div>

        {/* Priority distribution */}
        {kpis && (
          <div className="card">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Priority Distribution</p>
            <div className="flex flex-wrap gap-3">
              {[
                { label: 'Critical', count: kpis.critical_count, cls: 'badge-critical' },
                { label: 'High', count: kpis.high_count, cls: 'badge-high' },
                { label: 'Medium', count: kpis.medium_count, cls: 'badge-medium' },
                { label: 'Low', count: kpis.low_count, cls: 'badge-low' },
                { label: 'Paused', count: kpis.paused_count, cls: 'badge-paused' },
              ].map(({ label, count, cls }) => (
                <span key={label} className={cls}>
                  {label}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="card">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search accounts..."
              className="col-span-2 md:col-span-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-tenzing-400"
            />
            {[
              { label: 'Region', value: region, setter: setRegion, opts: filterOptions?.regions ?? [] },
              { label: 'Segment', value: segment, setter: setSegment, opts: filterOptions?.segments ?? [] },
              { label: 'Stage', value: lifecycle, setter: setLifecycle, opts: filterOptions?.lifecycle_stages ?? [] },
              { label: 'Owner', value: owner, setter: setOwner, opts: filterOptions?.owners ?? [] },
            ].map(({ label, value, setter, opts }) => (
              <select
                key={label}
                value={value}
                onChange={(e) => setter(e.target.value)}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-tenzing-400 bg-white"
              >
                <option value="">All {label}s</option>
                {opts.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            ))}
          </div>
        </div>

        {/* Account table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-tenzing-200 border-t-tenzing-500 rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-20 text-red-500 text-sm">Failed to load accounts</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Account</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Priority</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">ARR</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Renewal</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">MRR Trend</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Risk</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Opportunity</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Health</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Sentiment</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map((acc: AccountSummary) => (
                    <tr
                      key={acc.account_id}
                      className={`hover:bg-gray-50 transition-colors ${
                        acc.priority === 'Critical' ? 'bg-red-50/40' : ''
                      }`}
                    >
                      <td className="px-4 py-3">
                        <Link
                          to={`/accounts/${acc.account_id}`}
                          className="font-medium text-tenzing-600 hover:text-tenzing-800 hover:underline"
                        >
                          {acc.account_name}
                        </Link>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {acc.segment} · {acc.region}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <PriorityBadge priority={acc.priority} />
                      </td>
                      <td className="px-4 py-3 tabular-nums font-medium text-gray-800">
                        {fmt(acc.arr_gbp)}
                      </td>
                      <td className="px-4 py-3">
                        {acc.days_to_renewal !== undefined && acc.days_to_renewal !== null ? (
                          <span className={`text-xs font-medium tabular-nums ${
                            acc.days_to_renewal < 60
                              ? 'text-red-600'
                              : acc.days_to_renewal < 90
                                ? 'text-amber-600'
                                : 'text-gray-600'
                          }`}>
                            {acc.days_to_renewal < 0
                              ? `Overdue ${Math.abs(acc.days_to_renewal)}d`
                              : `${acc.days_to_renewal}d`}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <MRRTrend trend={acc.mrr_trend} />
                      </td>
                      <td className="px-4 py-3 w-28">
                        <ScoreBar value={acc.risk_score} type="risk" />
                      </td>
                      <td className="px-4 py-3 w-28">
                        <ScoreBar value={acc.opportunity_score} type="opportunity" />
                      </td>
                      <td className="px-4 py-3 w-28">
                        <ScoreBar value={acc.health_score} type="health" />
                      </td>
                      <td className="px-4 py-3">
                        <SentimentChip sentiment={acc.note_sentiment_hint} />
                      </td>
                      <td className="px-4 py-3">
                        <ConfidencePill confidence={acc.confidence} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && (
                <div className="text-center py-10 text-gray-400 text-sm">No accounts match filters</div>
              )}
            </div>
          )}
        </div>
        <p className="text-xs text-gray-400 text-right">{filtered.length} accounts shown</p>
      </main>
    </div>
  )
}
