import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchAccount } from '../api/client'
import Navbar from '../components/Navbar'
import PriorityBadge from '../components/PriorityBadge'
import ConfidencePill from '../components/ConfidencePill'
import ScoreBar from '../components/ScoreBar'
import MRRTrend from '../components/MRRTrend'
import SentimentChip from '../components/SentimentChip'
import SignalCard from '../components/SignalCard'
import AIPanel from '../components/AIPanel'
import DecisionRecorder from '../components/DecisionRecorder'

function fmt(n?: number | null, prefix = '£') {
  if (n === undefined || n === null) return '—'
  if (n >= 1_000_000) return `${prefix}${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${prefix}${(n / 1_000).toFixed(1)}K`
  return `${prefix}${n.toFixed(0)}`
}

function pct(n?: number | null) {
  if (n === undefined || n === null) return '—'
  return `${(n * 100).toFixed(0)}%`
}

export default function AccountDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: acc, isLoading, error } = useQuery({
    queryKey: ['account', id],
    queryFn: () => fetchAccount(id!, false),
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
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <p className="text-red-600 text-sm">Account not found or failed to load</p>
          <Link to="/" className="text-tenzing-500 text-sm mt-2 inline-block hover:underline">← Back to Portfolio</Link>
        </div>
      </div>
    )
  }

  const seatUtil = acc.seat_utilisation != null ? pct(acc.seat_utilisation) : '—'
  const mrrTrendPct = acc.mrr_trend != null ? `${(acc.mrr_trend * 100).toFixed(1)}%` : '—'

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Breadcrumb */}
        <Link to="/" className="text-tenzing-500 text-sm hover:underline">← Portfolio</Link>

        {/* Header */}
        <div className="card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold text-gray-900">{acc.account_name}</h1>
                <PriorityBadge priority={acc.priority} />
                <ConfidencePill confidence={acc.confidence} nullCount={acc.null_field_count} />
              </div>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500">
                <span>{acc.segment}</span>
                <span>·</span>
                <span>{acc.region}</span>
                <span>·</span>
                <span>{acc.industry}</span>
                <span>·</span>
                <span>{acc.lifecycle_stage}</span>
                {acc.account_status === 'Paused' && (
                  <span className="badge-paused">Paused</span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-gray-400">
                <span>AE: {acc.account_owner ?? '—'}</span>
                <span>·</span>
                <span>CSM: {acc.csm_owner ?? '—'}</span>
                <span>·</span>
                <span>Support: {acc.support_tier ?? '—'}</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-tenzing-500 tabular-nums">{fmt(acc.arr_gbp)}</p>
              <p className="text-xs text-gray-400 mt-0.5">Annual Recurring Revenue</p>
            </div>
          </div>

          {/* Score bars */}
          <div className="mt-5 grid grid-cols-3 gap-4">
            {[
              { label: 'Risk Score', value: acc.risk_score, type: 'risk' as const },
              { label: 'Opportunity Score', value: acc.opportunity_score, type: 'opportunity' as const },
              { label: 'Health Score', value: acc.health_score, type: 'health' as const },
            ].map(({ label, value, type }) => (
              <div key={label}>
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>{label}</span>
                  <span className="font-semibold">{Math.round(value)}</span>
                </div>
                <ScoreBar value={value} type={type} showLabel={false} />
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column — signals */}
          <div className="lg:col-span-2 space-y-4">

            {/* Commercial signals */}
            <SignalCard
              title="Commercial"
              icon="💷"
              rows={[
                { label: 'ARR', value: fmt(acc.arr_gbp) },
                { label: 'MRR (current)', value: fmt(acc.mrr_current_gbp) },
                {
                  label: 'MRR Trend (3m)',
                  value: <span className="flex items-center gap-2">
                    <MRRTrend trend={acc.mrr_trend} />
                    <span className="text-xs text-gray-400">{fmt(acc.mrr_3m_ago_gbp)} → {fmt(acc.mrr_current_gbp)}</span>
                  </span>,
                },
                { label: 'Renewal Date', value: acc.renewal_date ?? '—' },
                {
                  label: 'Days to Renewal',
                  value: acc.days_to_renewal != null ? (
                    <span className={acc.days_to_renewal < 60 ? 'text-red-600 font-bold' : acc.days_to_renewal < 90 ? 'text-amber-600 font-semibold' : ''}>
                      {acc.days_to_renewal < 0 ? `Overdue ${Math.abs(acc.days_to_renewal)}d` : `${acc.days_to_renewal}d`}
                    </span>
                  ) : '—',
                },
                { label: 'Billing', value: acc.billing_frequency },
                { label: 'Expansion Pipeline', value: fmt(acc.expansion_pipeline_gbp) },
                { label: 'Contraction Risk', value: fmt(acc.contraction_risk_gbp) },
                { label: 'Overdue Amount', value: acc.overdue_amount_gbp ? fmt(acc.overdue_amount_gbp) : '—' },
              ]}
            />

            {/* Health signals */}
            <SignalCard
              title="Health"
              icon="💚"
              rows={[
                { label: 'Seats Purchased', value: acc.seats_purchased },
                { label: 'Seats Used', value: acc.seats_used },
                {
                  label: 'Seat Utilisation',
                  value: (
                    <span className={
                      acc.seat_utilisation != null
                        ? acc.seat_utilisation < 0.5 ? 'text-red-600 font-semibold' : acc.seat_utilisation > 0.85 ? 'text-green-600 font-semibold' : ''
                        : ''
                    }>
                      {seatUtil}
                    </span>
                  ),
                },
                {
                  label: 'Usage Score (current)',
                  value: acc.usage_score_current != null ? (
                    <span className="flex items-center gap-2">
                      {acc.usage_score_current}
                      {acc.usage_score_3m_ago != null && (
                        <span className="text-xs text-gray-400">(was {acc.usage_score_3m_ago})</span>
                      )}
                    </span>
                  ) : '—',
                },
                {
                  label: 'NPS',
                  value: acc.latest_nps != null ? (
                    <span className={acc.latest_nps < 0 ? 'text-red-600 font-bold' : acc.latest_nps >= 50 ? 'text-green-600 font-bold' : ''}>
                      {acc.latest_nps}
                    </span>
                  ) : '—',
                },
                {
                  label: 'Avg CSAT (90d)',
                  value: acc.avg_csat_90d != null ? (
                    <span className={acc.avg_csat_90d < 3 ? 'text-red-600 font-bold' : acc.avg_csat_90d >= 4.5 ? 'text-green-600 font-bold' : ''}>
                      {acc.avg_csat_90d.toFixed(1)} / 5.0
                    </span>
                  ) : '—',
                },
              ]}
            />

            {/* Support signals */}
            <SignalCard
              title="Support"
              icon="🎫"
              rows={[
                {
                  label: 'Open Tickets',
                  value: acc.open_tickets_count != null ? (
                    <span className={acc.open_tickets_count >= 5 ? 'text-red-600 font-bold' : ''}>
                      {acc.open_tickets_count}
                    </span>
                  ) : '—',
                },
                {
                  label: 'Urgent Tickets',
                  value: acc.urgent_open_tickets_count != null ? (
                    <span className={acc.urgent_open_tickets_count >= 3 ? 'text-red-600 font-bold' : acc.urgent_open_tickets_count >= 1 ? 'text-amber-600 font-semibold' : ''}>
                      {acc.urgent_open_tickets_count}
                    </span>
                  ) : '—',
                },
                {
                  label: 'SLA Breaches (90d)',
                  value: acc.sla_breaches_90d != null ? (
                    <span className={acc.sla_breaches_90d >= 3 ? 'text-red-600 font-bold' : acc.sla_breaches_90d >= 1 ? 'text-amber-600 font-semibold' : 'text-green-600'}>
                      {acc.sla_breaches_90d}
                    </span>
                  ) : '—',
                },
                { label: 'Support Tier', value: acc.support_tier },
                { label: 'Last QBR', value: acc.last_qbr_date ?? '—' },
              ]}
            />

            {/* Leads signals */}
            <SignalCard
              title="Leads & Pipeline"
              icon="🔗"
              rows={[
                { label: 'Open Leads', value: acc.open_leads_count },
                { label: 'Avg Lead Score', value: acc.avg_lead_score != null ? `${acc.avg_lead_score.toFixed(0)} / 100` : '—' },
                { label: 'Last Lead Activity', value: acc.last_lead_activity_date ?? 'No recent activity' },
              ]}
            />

            {/* Notes */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <span>📝</span>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Notes & Sentiment</h3>
                <SentimentChip sentiment={acc.note_sentiment_hint} />
              </div>
              {[
                { label: 'Support Summary', value: acc.recent_support_summary },
                { label: 'Customer Note', value: acc.recent_customer_note },
                { label: 'Sales Note', value: acc.recent_sales_note },
              ].map(({ label, value }) => (
                <div key={label} className="mb-3 last:mb-0">
                  <p className="text-xs font-semibold text-gray-400 mb-1">{label}</p>
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {value ?? <span className="text-gray-300 italic">Insufficient qualitative data</span>}
                  </p>
                </div>
              ))}
              {acc.latest_note_date && (
                <p className="text-xs text-gray-400 mt-3">Last note: {acc.latest_note_date}</p>
              )}
            </div>

            {/* Decision recorder */}
            <DecisionRecorder accountId={acc.account_id} decisions={acc.decisions} />
          </div>

          {/* Right column — AI panel */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-gray-700">AI Analysis</h2>
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
