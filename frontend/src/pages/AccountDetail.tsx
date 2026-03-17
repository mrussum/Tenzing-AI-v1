import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchAccount } from '../api/client'
import Navbar from '../components/Navbar'
import PriorityBadge from '../components/PriorityBadge'
import ConfidencePill from '../components/ConfidencePill'
import ScoreBar from '../components/ScoreBar'
import MRRTrend from '../components/MRRTrend'
import MRRChart from '../components/MRRChart'
import SentimentChip from '../components/SentimentChip'
import SignalCard from '../components/SignalCard'
import AIPanel from '../components/AIPanel'
import DecisionRecorder from '../components/DecisionRecorder'

function fmt(n?: number | null, prefix = '£') {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${prefix}${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `${prefix}${(n / 1_000).toFixed(1)}K`
  return `${prefix}${n.toFixed(0)}`
}

function pct(n?: number | null) {
  if (n == null) return '—'
  return `${(n * 100).toFixed(0)}%`
}

function RenewalBadge({ days }: { days?: number | null }) {
  if (days == null) return <span className="text-gray-300">—</span>
  if (days < 0)
    return <span className="text-red-600 font-bold">Overdue {Math.abs(days)}d</span>
  if (days < 60)
    return <span className="text-red-600 font-bold">{days}d ⚠</span>
  if (days < 90)
    return <span className="text-amber-600 font-semibold">{days}d</span>
  return <span className="text-gray-700">{days}d</span>
}

export default function AccountDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: acc, isLoading, error } = useQuery({
    queryKey: ['account', id],
    queryFn: () => fetchAccount(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-32">
          <div className="w-10 h-10 border-4 border-tenzing-200 border-t-tenzing-500 rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (error || !acc) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-3">
          <p className="text-red-600 text-sm">Account not found or failed to load.</p>
          <Link to="/" className="text-tenzing-500 text-sm hover:underline">← Back to Portfolio</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Breadcrumb */}
        <Link to="/" className="text-tenzing-500 text-sm hover:underline">← Portfolio</Link>

        {/* ── Header card ── */}
        <div className="card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold text-gray-900 truncate">{acc.account_name}</h1>
                <PriorityBadge priority={acc.priority} />
                <ConfidencePill confidence={acc.confidence} nullCount={acc.null_field_count} />
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-gray-500">
                {[acc.segment, acc.region, acc.industry, acc.lifecycle_stage].filter(Boolean).map((v, i, a) => (
                  <span key={v} className="flex items-center gap-2">
                    {v}{i < a.length - 1 && <span className="text-gray-300">·</span>}
                  </span>
                ))}
                {acc.account_status === 'Paused' && <span className="badge-paused ml-1">Paused</span>}
              </div>
              <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-400">
                <span>AE: <span className="font-medium text-gray-600">{acc.account_owner ?? '—'}</span></span>
                <span>CSM: <span className="font-medium text-gray-600">{acc.csm_owner ?? '—'}</span></span>
                <span>Support tier: <span className="font-medium text-gray-600">{acc.support_tier ?? '—'}</span></span>
                {acc.last_qbr_date && (
                  <span>Last QBR: <span className="font-medium text-gray-600">{acc.last_qbr_date}</span></span>
                )}
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-3xl font-bold text-tenzing-500 tabular-nums">{fmt(acc.arr_gbp)}</p>
              <p className="text-xs text-gray-400 mt-0.5">Annual Recurring Revenue</p>
              <div className="mt-2 flex justify-end">
                <MRRTrend trend={acc.mrr_trend} />
              </div>
            </div>
          </div>

          {/* Score bars */}
          <div className="mt-5 grid grid-cols-3 gap-5 pt-4 border-t border-gray-50">
            {(
              [
                { label: 'Risk Score',        value: acc.risk_score,        type: 'risk'        },
                { label: 'Opportunity Score', value: acc.opportunity_score, type: 'opportunity' },
                { label: 'Health Score',      value: acc.health_score,      type: 'health'      },
              ] as const
            ).map(({ label, value, type }) => (
              <div key={label}>
                <div className="flex justify-between text-xs text-gray-500 mb-1.5">
                  <span>{label}</span>
                  <span className="font-semibold">{Math.round(value)}</span>
                </div>
                <ScoreBar value={value} type={type} showLabel={false} />
              </div>
            ))}
          </div>
        </div>

        {/* ── Main grid ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left: signal cards */}
          <div className="lg:col-span-2 space-y-4">

            {/* Commercial */}
            <SignalCard
              title="Commercial"
              icon="💷"
              rows={[
                { label: 'ARR',               value: fmt(acc.arr_gbp) },
                { label: 'MRR (current)',      value: fmt(acc.mrr_current_gbp) },
                { label: 'MRR (3m ago)',       value: fmt(acc.mrr_3m_ago_gbp) },
                {
                  label: 'Renewal date',
                  value: acc.renewal_date ?? '—',
                },
                {
                  label: 'Days to renewal',
                  value: <RenewalBadge days={acc.days_to_renewal} />,
                },
                { label: 'Billing',            value: acc.billing_frequency },
                { label: 'Expansion pipeline', value: fmt(acc.expansion_pipeline_gbp) },
                { label: 'Contraction risk',   value: fmt(acc.contraction_risk_gbp) },
                {
                  label: 'Overdue amount',
                  value: acc.overdue_amount_gbp
                    ? <span className="text-red-600 font-semibold">{fmt(acc.overdue_amount_gbp)}</span>
                    : <span className="text-green-600 text-xs">None</span>,
                },
              ]}
            />

            {/* MRR chart — lives below the commercial card */}
            {(acc.mrr_current_gbp != null || acc.mrr_3m_ago_gbp != null) && (
              <div className="card">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">MRR Trend</p>
                <MRRChart current={acc.mrr_current_gbp} ago={acc.mrr_3m_ago_gbp} />
              </div>
            )}

            {/* Health */}
            <SignalCard
              title="Health"
              icon="💚"
              rows={[
                { label: 'Seats purchased', value: acc.seats_purchased },
                { label: 'Seats used',      value: acc.seats_used },
                {
                  label: 'Seat utilisation',
                  value: acc.seat_utilisation != null ? (
                    <span className={
                      acc.seat_utilisation < 0.50 ? 'text-red-600 font-semibold' :
                      acc.seat_utilisation > 0.85 ? 'text-green-600 font-semibold' : ''
                    }>
                      {pct(acc.seat_utilisation)}
                    </span>
                  ) : '—',
                },
                {
                  label: 'Usage score (now)',
                  value: acc.usage_score_current != null ? (
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{acc.usage_score_current}</span>
                      {acc.usage_score_3m_ago != null && (
                        <span className={`text-xs ${
                          acc.usage_score_current > acc.usage_score_3m_ago ? 'text-green-600' :
                          acc.usage_score_current < acc.usage_score_3m_ago ? 'text-red-500' : 'text-gray-400'
                        }`}>
                          (was {acc.usage_score_3m_ago})
                        </span>
                      )}
                    </span>
                  ) : '—',
                },
                {
                  label: 'NPS',
                  value: acc.latest_nps != null ? (
                    <span className={
                      acc.latest_nps < 0   ? 'text-red-600 font-bold' :
                      acc.latest_nps >= 50 ? 'text-green-600 font-bold' : ''
                    }>
                      {acc.latest_nps}
                    </span>
                  ) : '—',
                },
                {
                  label: 'Avg CSAT (90d)',
                  value: acc.avg_csat_90d != null ? (
                    <span className={
                      acc.avg_csat_90d < 3.0 ? 'text-red-600 font-bold' :
                      acc.avg_csat_90d >= 4.5 ? 'text-green-600 font-bold' : ''
                    }>
                      {acc.avg_csat_90d.toFixed(1)} / 5.0
                    </span>
                  ) : '—',
                },
              ]}
            />

            {/* Support */}
            <SignalCard
              title="Support"
              icon="🎫"
              rows={[
                {
                  label: 'Open tickets',
                  value: acc.open_tickets_count != null ? (
                    <span className={acc.open_tickets_count >= 5 ? 'text-red-600 font-bold' : ''}>
                      {acc.open_tickets_count}
                    </span>
                  ) : '—',
                },
                {
                  label: 'Urgent tickets',
                  value: acc.urgent_open_tickets_count != null ? (
                    <span className={
                      acc.urgent_open_tickets_count >= 3 ? 'text-red-600 font-bold' :
                      acc.urgent_open_tickets_count >= 1 ? 'text-amber-600 font-semibold' : 'text-green-600'
                    }>
                      {acc.urgent_open_tickets_count}
                    </span>
                  ) : '—',
                },
                {
                  label: 'SLA breaches (90d)',
                  value: acc.sla_breaches_90d != null ? (
                    <span className={
                      acc.sla_breaches_90d >= 3 ? 'text-red-600 font-bold' :
                      acc.sla_breaches_90d >= 1 ? 'text-amber-600 font-semibold' : 'text-green-600'
                    }>
                      {acc.sla_breaches_90d}
                    </span>
                  ) : '—',
                },
              ]}
            />

            {/* Leads */}
            <SignalCard
              title="Leads & Pipeline"
              icon="🔗"
              rows={[
                { label: 'Open leads',         value: acc.open_leads_count ?? '—' },
                {
                  label: 'Avg lead score',
                  value: acc.avg_lead_score != null ? (
                    <span className={acc.avg_lead_score > 70 ? 'text-green-600 font-semibold' : ''}>
                      {acc.avg_lead_score.toFixed(0)} / 100
                    </span>
                  ) : '—',
                },
                { label: 'Last lead activity', value: acc.last_lead_activity_date ?? 'No recent activity' },
              ]}
            />

            {/* Notes */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <span>📝</span>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Notes & Sentiment</h3>
                <SentimentChip sentiment={acc.note_sentiment_hint} />
                {acc.latest_note_date && (
                  <span className="ml-auto text-xs text-gray-400">{acc.latest_note_date}</span>
                )}
              </div>
              {[
                { label: 'Support summary', value: acc.recent_support_summary },
                { label: 'Customer note',   value: acc.recent_customer_note },
                { label: 'Sales note',      value: acc.recent_sales_note },
              ].map(({ label, value }) => (
                <div key={label} className="mb-4 last:mb-0">
                  <p className="text-xs font-semibold text-gray-400 mb-1">{label}</p>
                  {value
                    ? <p className="text-sm text-gray-700 leading-relaxed">{value}</p>
                    : <p className="text-sm text-gray-300 italic">Insufficient qualitative data</p>
                  }
                </div>
              ))}
            </div>

            {/* Decisions */}
            <DecisionRecorder accountId={acc.account_id} decisions={acc.decisions} />
          </div>

          {/* Right: AI analysis */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-700">AI Analysis</h2>
              <span className="text-xs text-gray-400">Claude Sonnet 4</span>
            </div>
            <AIPanel
              accountId={acc.account_id}
              deterministicPriority={acc.priority}
              confidence={acc.confidence}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
