"""Pydantic models for the account prioritisation API."""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Computed / enriched account signals
# ---------------------------------------------------------------------------

class AccountSignals(BaseModel):
    """Deterministic computed signals — derived from raw CSV fields."""
    mrr_trend: Optional[float] = None          # (current-3m)/3m
    seat_utilisation: Optional[float] = None   # used/purchased
    days_to_renewal: Optional[int] = None
    risk_score: float = 0.0
    opportunity_score: float = 0.0
    health_score: float = 0.0
    confidence: str = "High"                   # High | Medium | Low
    null_field_count: int = 0


# ---------------------------------------------------------------------------
# AI-generated analysis
# ---------------------------------------------------------------------------

class AIRisk(BaseModel):
    risk: str
    evidence: str


class AIOpportunity(BaseModel):
    opportunity: str
    evidence: str


class AIAction(BaseModel):
    action: str
    owner: str


class AIAnalysis(BaseModel):
    priority: str                               # Critical | High | Medium | Low
    priority_reasoning: str
    top_risks: list[AIRisk] = []
    top_opportunities: list[AIOpportunity] = []
    recommended_actions: list[AIAction] = []
    confidence: str = "Medium"                 # High | Medium | Low
    raw_response: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Decision recording
# ---------------------------------------------------------------------------

class DecisionCreate(BaseModel):
    text: str
    decided_by: Optional[str] = None


class Decision(BaseModel):
    id: str
    account_id: str
    text: str
    decided_by: Optional[str]
    timestamp: datetime


# ---------------------------------------------------------------------------
# Full account detail
# ---------------------------------------------------------------------------

class AccountSummary(BaseModel):
    """Lightweight row for the portfolio table."""
    account_id: str
    account_name: str
    segment: Optional[str]
    region: Optional[str]
    industry: Optional[str]
    account_status: Optional[str]
    lifecycle_stage: Optional[str]
    account_owner: Optional[str]
    csm_owner: Optional[str]
    support_tier: Optional[str]
    arr_gbp: Optional[float]
    renewal_date: Optional[str]
    days_to_renewal: Optional[int]
    mrr_current_gbp: Optional[float]
    mrr_trend: Optional[float]
    seat_utilisation: Optional[float]
    risk_score: float
    opportunity_score: float
    health_score: float
    priority: str
    confidence: str
    note_sentiment_hint: Optional[str]
    expansion_pipeline_gbp: Optional[float]
    contraction_risk_gbp: Optional[float]
    latest_nps: Optional[float]
    avg_csat_90d: Optional[float]


class AccountDetail(AccountSummary):
    """Full account data for the detail page."""
    # Raw commercial
    external_account_ref: Optional[str]
    website: Optional[str]
    billing_frequency: Optional[str]
    billing_currency: Optional[str]
    contract_start_date: Optional[str]
    mrr_3m_ago_gbp: Optional[float]
    overdue_amount_gbp: Optional[float]
    last_qbr_date: Optional[str]

    # Raw health
    seats_purchased: Optional[int]
    seats_used: Optional[int]
    usage_score_current: Optional[float]
    usage_score_3m_ago: Optional[float]

    # Raw support
    open_tickets_count: Optional[int]
    urgent_open_tickets_count: Optional[int]
    sla_breaches_90d: Optional[int]

    # Raw leads
    open_leads_count: Optional[int]
    avg_lead_score: Optional[float]
    last_lead_activity_date: Optional[str]

    # Qualitative
    latest_note_date: Optional[str]
    recent_support_summary: Optional[str]
    recent_customer_note: Optional[str]
    recent_sales_note: Optional[str]

    # AI analysis (loaded on demand)
    ai_analysis: Optional[AIAnalysis] = None

    # Decisions
    decisions: list[Decision] = []

    # Raw null count
    null_field_count: int = 0


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

class PortfolioKPIs(BaseModel):
    total_arr_gbp: float
    accounts_at_risk: int        # risk_score > 50
    expansion_opportunities: int  # opportunity_score > 50
    avg_health_score: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    paused_count: int


class PortfolioSummary(BaseModel):
    kpis: PortfolioKPIs
    briefing: Optional[str] = None
    generated_at: Optional[datetime] = None
