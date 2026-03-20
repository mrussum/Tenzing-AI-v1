"""Deterministic scoring and priority assignment.

All weights are explicit and tuneable constants defined at the top of this file.
Scores are normalised through a sigmoid function so they remain meaningfully
spread across 0-100 rather than saturating at the ceiling when multiple bad
signals coincide.

Sigmoid mid-points are calibrated so that:
  - An account with 3 moderate risk signals → risk_score ≈ 50
  - An account with 5-6 severe risk signals → risk_score ≈ 90+
  - A purely healthy account with no risk signals → risk_score ≈ 5-15
"""
from __future__ import annotations
import math
from typing import Any, Optional

# ---------------------------------------------------------------------------
# RISK score weights
# Each weight represents raw points. Sigmoid normalisation converts the raw
# sum to a 0-100 score, so weights express *relative* importance, not direct
# percentages — raise/lower any weight to re-tune without re-calibrating others.
# ---------------------------------------------------------------------------
W_RISK_NPS_VERY_LOW      = 20  # NPS < 0
W_RISK_NPS_LOW           = 10  # NPS 0-30
W_RISK_SLA_HIGH          = 18  # sla_breaches_90d >= 3
W_RISK_SLA_MED           =  9  # sla_breaches_90d >= 1
W_RISK_CONTRACTION_HIGH  = 20  # contraction_risk > 30% of ARR
W_RISK_CONTRACTION_MED   = 12  # contraction_risk > 10% of ARR
W_RISK_MRR_DECLINE_HIGH  = 20  # mrr_trend < -10%
W_RISK_MRR_DECLINE_MED   = 10  # mrr_trend < -5%
W_RISK_SENTIMENT_NEG     = 15  # note_sentiment_hint == Negative
W_RISK_URGENT_HIGH       = 15  # urgent_open_tickets >= 3
W_RISK_URGENT_MED        =  8  # urgent_open_tickets >= 1
W_RISK_LOW_SEAT_UTIL     = 10  # seat_utilisation < 0.50
W_RISK_NEAR_RENEWAL      =  8  # 0 <= days_to_renewal < 60
W_RISK_LOW_CSAT          = 10  # avg_csat < 3.0
W_RISK_OVERDUE           = 12  # overdue_amount_gbp > 0
W_RISK_USAGE_DECLINE     = 10  # usage_score fell > 10 pts

# Sigmoid calibration for risk:
#   raw ≈ 45 (3 moderate signals) → normalised ≈ 50
#   raw ≈ 90 (6 severe signals)   → normalised ≈ 88
_RISK_SIGMOID_MID   = 45.0
_RISK_SIGMOID_STEEP = 18.0

# ---------------------------------------------------------------------------
# OPPORTUNITY score weights
# ---------------------------------------------------------------------------
W_OPP_EXPANSION_HIGH     = 25  # expansion_pipeline > 20% ARR
W_OPP_EXPANSION_MED      = 15  # expansion_pipeline > 10% ARR
W_OPP_SENTIMENT_POS      = 15  # Positive sentiment
W_OPP_LEAD_SCORE_HIGH    = 15  # avg_lead_score > 70
W_OPP_LEAD_SCORE_MED     =  8  # avg_lead_score > 50
W_OPP_MRR_GROWTH         = 15  # mrr_trend > 5%
W_OPP_HIGH_SEAT_UTIL     = 12  # seat_utilisation > 85%
W_OPP_EXPANSION_STAGE    = 15  # lifecycle_stage == Expansion
W_OPP_LEADS_PRESENT      = 10  # open_leads_count >= 2
W_OPP_HIGH_CSAT          =  8  # avg_csat >= 4.5
W_OPP_USAGE_GROWTH       =  8  # usage_score improved > 5 pts

# Sigmoid calibration for opportunity:
#   raw ≈ 40 (strong pipeline + positive sentiment) → normalised ≈ 55
#   raw ≈ 70 (4 strong signals)                     → normalised ≈ 83
_OPP_SIGMOID_MID   = 35.0
_OPP_SIGMOID_STEEP = 18.0

# ---------------------------------------------------------------------------
# HEALTH score — uses a baseline + additive modifiers (different pattern)
# ---------------------------------------------------------------------------
HEALTH_BASE        =  50  # neutral starting point

H_CSAT_EXCELLENT   =  20  # avg_csat >= 4.5
H_CSAT_GOOD        =  10  # avg_csat >= 4.0
H_CSAT_POOR        = -15  # avg_csat < 3.0
H_NPS_HIGH         =  15  # nps >= 50
H_NPS_MED          =   8  # nps 0-49
H_NPS_LOW          = -10  # nps < 0
H_NPS_VERY_LOW     = -20  # nps < -20
H_USAGE_UP         =  10  # usage_score improved > 3 pts
H_USAGE_DOWN       = -10  # usage_score fell > 3 pts
H_TICKETS_LOW      =   8  # 0 open tickets
H_TICKETS_HIGH     = -12  # 5+ open tickets
H_SLA_NONE         =   8  # 0 SLA breaches
H_SLA_HIGH         = -15  # 3+ SLA breaches
H_MRR_GROWING      =  10  # mrr_trend > 5%
H_MRR_STABLE       =   8  # |mrr_trend| < 5%
H_MRR_DECLINING    = -15  # mrr_trend < -10%
H_SENTIMENT_POS    =   8  # Positive
H_SENTIMENT_NEG    = -12  # Negative


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _sigmoid(raw: float, mid: float, steep: float) -> float:
    """Map any raw score to (0, 100) via a logistic sigmoid.

    Benefits over a hard clamp:
    - Scores remain spread across the full range.
    - Moderate-risk accounts don't all cluster at the same value.
    - Truly catastrophic accounts approach (but don't reach) 100,
      preserving discrimination between 'bad' and 'catastrophic'.
    """
    return 100.0 / (1.0 + math.exp(-(raw - mid) / steep))


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

def compute_risk_score(acc: dict) -> float:
    raw = 0.0

    nps         = acc.get("latest_nps")
    sla         = acc.get("sla_breaches_90d") or 0
    contraction = acc.get("contraction_risk_gbp") or 0
    arr         = acc.get("arr_gbp") or 1
    mrr_trend   = acc.get("mrr_trend")
    sentiment   = (acc.get("note_sentiment_hint") or "").strip()
    urgent      = acc.get("urgent_open_tickets_count") or 0
    seat_util   = acc.get("seat_utilisation")
    days_renew  = acc.get("days_to_renewal")
    csat        = acc.get("avg_csat_90d")
    overdue     = acc.get("overdue_amount_gbp") or 0
    usage_cur   = acc.get("usage_score_current")
    usage_old   = acc.get("usage_score_3m_ago")

    if nps is not None:
        raw += W_RISK_NPS_VERY_LOW if nps < 0 else (W_RISK_NPS_LOW if nps <= 30 else 0)

    raw += W_RISK_SLA_HIGH if sla >= 3 else (W_RISK_SLA_MED if sla >= 1 else 0)

    cr = contraction / arr if arr > 0 else 0
    raw += W_RISK_CONTRACTION_HIGH if cr > 0.30 else (W_RISK_CONTRACTION_MED if cr > 0.10 else 0)

    if mrr_trend is not None:
        raw += W_RISK_MRR_DECLINE_HIGH if mrr_trend < -0.10 else (W_RISK_MRR_DECLINE_MED if mrr_trend < -0.05 else 0)

    if sentiment == "Negative":
        raw += W_RISK_SENTIMENT_NEG

    raw += W_RISK_URGENT_HIGH if urgent >= 3 else (W_RISK_URGENT_MED if urgent >= 1 else 0)

    if seat_util is not None and seat_util < 0.50:
        raw += W_RISK_LOW_SEAT_UTIL

    if days_renew is not None and 0 <= days_renew < 60:
        raw += W_RISK_NEAR_RENEWAL

    if csat is not None and csat < 3.0:
        raw += W_RISK_LOW_CSAT

    if overdue > 0:
        raw += W_RISK_OVERDUE

    if usage_cur is not None and usage_old is not None and (usage_old - usage_cur) > 10:
        raw += W_RISK_USAGE_DECLINE

    return round(_sigmoid(raw, _RISK_SIGMOID_MID, _RISK_SIGMOID_STEEP), 1)


def compute_opportunity_score(acc: dict) -> float:
    raw = 0.0

    expansion  = acc.get("expansion_pipeline_gbp") or 0
    arr        = acc.get("arr_gbp") or 1
    sentiment  = (acc.get("note_sentiment_hint") or "").strip()
    avg_lead   = acc.get("avg_lead_score")
    mrr_trend  = acc.get("mrr_trend")
    seat_util  = acc.get("seat_utilisation")
    lifecycle  = (acc.get("lifecycle_stage") or "").strip()
    leads      = acc.get("open_leads_count") or 0
    csat       = acc.get("avg_csat_90d")
    usage_cur  = acc.get("usage_score_current")
    usage_old  = acc.get("usage_score_3m_ago")

    er = expansion / arr if arr > 0 else 0
    raw += W_OPP_EXPANSION_HIGH if er > 0.20 else (W_OPP_EXPANSION_MED if er > 0.10 else 0)

    if sentiment == "Positive":
        raw += W_OPP_SENTIMENT_POS

    if avg_lead is not None:
        raw += W_OPP_LEAD_SCORE_HIGH if avg_lead > 70 else (W_OPP_LEAD_SCORE_MED if avg_lead > 50 else 0)

    if mrr_trend is not None and mrr_trend > 0.05:
        raw += W_OPP_MRR_GROWTH

    if seat_util is not None and seat_util > 0.85:
        raw += W_OPP_HIGH_SEAT_UTIL

    if lifecycle.lower() == "expansion":
        raw += W_OPP_EXPANSION_STAGE

    if leads >= 2:
        raw += W_OPP_LEADS_PRESENT

    if csat is not None and csat >= 4.5:
        raw += W_OPP_HIGH_CSAT

    if usage_cur is not None and usage_old is not None and (usage_cur - usage_old) > 5:
        raw += W_OPP_USAGE_GROWTH

    return round(_sigmoid(raw, _OPP_SIGMOID_MID, _OPP_SIGMOID_STEEP), 1)


def compute_health_score(acc: dict) -> float:
    score = float(HEALTH_BASE)

    csat       = acc.get("avg_csat_90d")
    nps        = acc.get("latest_nps")
    usage_cur  = acc.get("usage_score_current")
    usage_old  = acc.get("usage_score_3m_ago")
    tickets    = acc.get("open_tickets_count") or 0
    sla        = acc.get("sla_breaches_90d") or 0
    mrr_trend  = acc.get("mrr_trend")
    sentiment  = (acc.get("note_sentiment_hint") or "").strip()

    if csat is not None:
        score += H_CSAT_EXCELLENT if csat >= 4.5 else (H_CSAT_GOOD if csat >= 4.0 else (H_CSAT_POOR if csat < 3.0 else 0))

    if nps is not None:
        if nps >= 50:
            score += H_NPS_HIGH
        elif nps >= 0:
            score += H_NPS_MED
        elif nps >= -20:
            score += H_NPS_LOW
        else:
            score += H_NPS_VERY_LOW

    if usage_cur is not None and usage_old is not None:
        diff = usage_cur - usage_old
        score += H_USAGE_UP if diff > 3 else (H_USAGE_DOWN if diff < -3 else 0)

    score += H_TICKETS_LOW if tickets == 0 else (H_TICKETS_HIGH if tickets >= 5 else 0)
    score += H_SLA_NONE    if sla == 0   else (H_SLA_HIGH    if sla >= 3    else 0)

    if mrr_trend is not None:
        score += H_MRR_GROWING if mrr_trend > 0.05 else (H_MRR_STABLE if abs(mrr_trend) < 0.05 else (H_MRR_DECLINING if mrr_trend < -0.10 else 0))

    score += H_SENTIMENT_POS if sentiment == "Positive" else (H_SENTIMENT_NEG if sentiment == "Negative" else 0)

    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# Priority assignment
# ---------------------------------------------------------------------------

def assign_priority(acc: dict, risk_score: float, health_score: float) -> str:
    """
    Explicit, rule-based priority — every tier cites ≥ 2 specific signals.

    CRITICAL: (days_to_renewal < 60  AND risk_score > 70)
              OR contraction_risk_gbp > £50,000
              OR (sentiment = Negative AND urgent_open_tickets > 2)

    HIGH:     risk_score > 50
              OR (days_to_renewal < 90 AND health_score < 50)
              OR (sla_breaches >= 3 AND NPS < 0)

    MEDIUM:   risk_score > 25
              OR opportunity_score > 40

    LOW:      no material risk or opportunity signal
    PAUSED:   account_status = Paused (excluded from active scoring)
    """
    if (acc.get("account_status") or "").lower() == "paused":
        return "Paused"

    days_renew  = acc.get("days_to_renewal")
    contraction = acc.get("contraction_risk_gbp") or 0
    sentiment   = (acc.get("note_sentiment_hint") or "").strip()
    urgent      = acc.get("urgent_open_tickets_count") or 0
    sla         = acc.get("sla_breaches_90d") or 0
    nps         = acc.get("latest_nps")
    opp_score   = acc.get("opportunity_score", 0)

    # CRITICAL
    if days_renew is not None and 0 <= days_renew < 60 and risk_score > 70:
        return "Critical"
    if contraction > 50_000:
        return "Critical"
    if sentiment == "Negative" and urgent > 2:
        return "Critical"

    # HIGH
    if risk_score > 50:
        return "High"
    if days_renew is not None and 0 <= days_renew < 90 and health_score < 50:
        return "High"
    if sla >= 3 and nps is not None and nps < 0:
        return "High"

    # MEDIUM
    if risk_score > 25:
        return "Medium"
    if opp_score > 40:
        return "Medium"

    return "Low"


def enrich_account(acc: dict) -> dict:
    risk   = compute_risk_score(acc)
    opp    = compute_opportunity_score(acc)
    health = compute_health_score(acc)

    acc["risk_score"]        = risk
    acc["opportunity_score"] = opp
    acc["health_score"]      = health
    acc["priority"]          = assign_priority(acc, risk, health)
    return acc


PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Paused": 4}


def sort_accounts(accounts: list[dict]) -> list[dict]:
    """Priority tier → risk_score desc → arr_gbp desc."""
    return sorted(
        accounts,
        key=lambda a: (
            PRIORITY_ORDER.get(a.get("priority", "Low"), 5),
            -(a.get("risk_score") or 0),
            -(a.get("arr_gbp") or 0),
        ),
    )
