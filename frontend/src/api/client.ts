import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: BASE_URL,
})

// Attach JWT from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ---------------------------------------------------------------------------
// Types (mirrors backend Pydantic models)
// ---------------------------------------------------------------------------

export interface AccountSummary {
  account_id: string
  account_name: string
  segment?: string
  region?: string
  industry?: string
  account_status?: string
  lifecycle_stage?: string
  account_owner?: string
  csm_owner?: string
  support_tier?: string
  arr_gbp?: number
  renewal_date?: string
  days_to_renewal?: number
  mrr_current_gbp?: number
  mrr_trend?: number
  seat_utilisation?: number
  risk_score: number
  opportunity_score: number
  health_score: number
  priority: string
  confidence: string
  note_sentiment_hint?: string
  expansion_pipeline_gbp?: number
  contraction_risk_gbp?: number
  latest_nps?: number
  avg_csat_90d?: number
}

export interface AIRisk { risk: string; evidence: string }
export interface AIOpportunity { opportunity: string; evidence: string }
export interface AIAction { action: string; owner: string }

export interface AIAnalysis {
  priority: string
  priority_reasoning: string
  top_risks: AIRisk[]
  top_opportunities: AIOpportunity[]
  recommended_actions: AIAction[]
  confidence: string
  error?: string
}

export interface Decision {
  id: string
  account_id: string
  text: string
  decided_by?: string
  timestamp: string
}

export interface AccountDetail extends AccountSummary {
  external_account_ref?: string
  website?: string
  billing_frequency?: string
  billing_currency?: string
  contract_start_date?: string
  mrr_3m_ago_gbp?: number
  overdue_amount_gbp?: number
  last_qbr_date?: string
  seats_purchased?: number
  seats_used?: number
  usage_score_current?: number
  usage_score_3m_ago?: number
  open_tickets_count?: number
  urgent_open_tickets_count?: number
  sla_breaches_90d?: number
  open_leads_count?: number
  avg_lead_score?: number
  last_lead_activity_date?: string
  latest_note_date?: string
  recent_support_summary?: string
  recent_customer_note?: string
  recent_sales_note?: string
  ai_analysis?: AIAnalysis
  decisions: Decision[]
  null_field_count: number
}

export interface PortfolioKPIs {
  total_arr_gbp: number
  accounts_at_risk: number
  expansion_opportunities: number
  avg_health_score: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  paused_count: number
}

export interface PortfolioSummary {
  kpis: PortfolioKPIs
  briefing?: string
  generated_at?: string
}

export interface FilterOptions {
  regions: string[]
  segments: string[]
  lifecycle_stages: string[]
  owners: string[]
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export const authLogin = async (username: string, password: string) => {
  const res = await api.post<{ access_token: string; token_type: string }>(
    '/auth/login/json',
    { username, password }
  )
  localStorage.setItem('access_token', res.data.access_token)
  return res
}

export const authLogout = () => {
  localStorage.removeItem('access_token')
  return api.post('/auth/logout')
}

export const fetchCurrentUser = () =>
  api.get<{ username: string }>('/auth/me').then((r) => r.data)

export const fetchAccounts = (params?: {
  region?: string
  segment?: string
  lifecycle_stage?: string
  owner?: string
}) => api.get<AccountSummary[]>('/accounts', { params }).then((r) => r.data)

export const fetchAccount = (id: string) =>
  api.get<AccountDetail>(`/accounts/${id}`).then((r) => r.data)

export const fetchAccountAnalysis = (id: string, refresh = false) =>
  api.get<AIAnalysis>(`/accounts/${id}/analysis`, { params: { refresh } }).then((r) => r.data)

export const fetchPortfolioSummary = (withAi = false) =>
  api.get<PortfolioSummary>('/portfolio/summary', { params: { with_ai: withAi } }).then((r) => r.data)

export const postDecision = (accountId: string, text: string, decidedBy?: string) =>
  api.post<Decision>(`/accounts/${accountId}/decisions`, { text, decided_by: decidedBy }).then((r) => r.data)

export const fetchFilterOptions = () =>
  api.get<FilterOptions>('/filters/options').then((r) => r.data)
