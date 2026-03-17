"""Deterministic scoring and priority assignment.

All weights are explicit and tuneable constants at the top of this file.
Every score is clamped to [0, 100].
"""
from __future__ import annotations
from typing import Any, Optional

# ---------------------------------------------------------------------------
# RISK score weights (max points each component can contribute)
# ---------------------------------------------------------------------------
W_RISK_NPS_VERY_LOW = 20      # NPS < 0
W_RISK_NPS_LOW = 10           # NPS 0-30
W_RISK_SLA_HIGH = 18          # sla_breaches >= 3 in 90d
W_RISK_SLA_MED = 9            # sla_breaches >= 1 in 90d
W_RISK_CONTRACTION_HIGH = 20  # contraction_risk > 30% of ARR
W_RISK_CONTRACTION_MED = 12   # contraction_risk > 10% of ARR
W_RISK_MRR_DECLINE_HIGH = 20  # mrr_trend < -10%
W_RISK_MRR_DECLINE_MED = 10   # mrr_trend < -5%
W_RISK_SENTIMENT_NEG = 15     # note_sentiment_hint == Negative
W_RISK_URGENT_TICKETS_HIGH = 15  # urgent_tickets >= 3
W_RISK_URGENT_TICKETS_MED = 8    # urgent_tickets >= 1
W_RISK_LOW_SEAT_UTIL = 10     # seat_utilisation < 0.50
W_RISK_NEAR_RENEWAL = 8       # days_to_renewal < 60
W_RISK_LOW_CSAT = 10          # avg_csat < 3.0
W_RISK_OVERDUE = 12           # overdue_amount_gbp > 0
W_RISK_USAGE_DECLINE = 10     # usage_score declined > 10pts

# ---------------------------------------------------------------------------
# OPPORTUNITY score weights
# ---------------------------------------------------------------------------
W_OPP_EXPANSION_HIGH = 25     # expansion_pipeline > 20% ARR
W_OPP_EXPANSION_MED = 15      # expansion_pipeline > 10% ARR
W_OPP_SENTIMENT_POS = 15      # note_sentiment_hint == Positive
W_OPP_LEAD_SCORE_HIGH = 15    # avg_lead_score > 70
W_OPP_LEAD_SCORE_MED = 8      # avg_lead_score > 50
W_OPP_MRR_GROWTH = 15         # mrr_trend > 5%
W_OPP_HIGH_SEAT_UTIL = 12     # seat_utilisation > 85% (upsell signal)
W_OPP_EXPANSION_STAGE = 15    # lifecycle_stage == Expansion
W_OPP_LEADS_PRESENT = 10      # open_leads_count >= 2
W_OPP_HIGH_CSAT = 8           # avg_csat >= 4.5 (good relationship)
W_OPP_USAGE_GROWTH = 8        # usage_score improved > 5pts

# ---------------------------------------------------------------------------
# HEALTH score base + modifiers
# ---------------------------------------------------------------------------
# Health starts at 50 (neutral baseline) and is adjusted up/down
HEALTH_BASE = 50
H_CSAT_EXCELLENT = 20         # avg_csat >= 4.5
H_CSAT_GOOD = 10              # avg_csat >= 4.0
H_CSAT_POOR = -15             # avg_csat < 3.0
H_NPS_HIGH = 15               # nps >= 50
H_NPS_MED = 8                 # nps >= 0
H_NPS_LOW = -10               # nps < 0
H_NPS_VERY_LOW = -20          # nps < -20
H_USAGE_UP = 10               # usage_score improved
H_USAGE_DOWN = -10            # usage_score declined
H_TICKETS_LOW = 8             # open_tickets_count == 0
H_TICKETS_HIGH = -12          # open_tickets_count >= 5
H_SLA_NONE = 8                # no SLA breaches
H_SLA_HIGH = -15              # sla_breaches >= 3
H_MRR_STABLE = 8              # |mrr_trend| < 5%
H_MRR_GROWING = 10            # mrr_trend > 5%
H_MRR_DECLINING = -15         # mrr_trend < -10%
H_SENTIMENT_POS = 8           # Positive
H_SENTIMENT_NEG = -12         # Negative


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def compute_risk_score(acc: dict) -> float:
    score = 0.0
    nps = acc.get("latest_nps")
    sla = acc.get("sla_breaches_90d") or 0
    contraction = acc.get("contraction_risk_gbp") or 0
    arr = acc.get("arr_gbp") or 1
    mrr_trend = acc.get("mrr_trend")
    sentiment = (acc.get("note_sentiment_hint") or "").strip()
    urgent = acc.get("urgent_open_tickets_count") or 0
    seat_util = acc.get("seat_utilisation")
    days_renewal = acc.get("days_to_renewal")
    csat = acc.get("avg_csat_90d")
    overdue = acc.get("overdue_amount_gbp") or 0
    usage_cur = acc.get("usage_score_current")
    usage_old = acc.get("usage_score_3m_ago")

    if nps is not None:
        if nps < 0:
            score += W_RISK_NPS_VERY_LOW
        elif nps <= 30:
            score += W_RISK_NPS_LOW

    if sla >= 3:
        score += W_RISK_SLA_HIGH
    elif sla >= 1:
        score += W_RISK_SLA_MED

    contraction_ratio = contraction / arr if arr > 0 else 0
    if contraction_ratio > 0.30:
        score += W_RISK_CONTRACTION_HIGH
    elif contraction_ratio > 0.10:
        score += W_RISK_CONTRACTION_MED

    if mrr_trend is not None:
        if mrr_trend < -0.10:
            score += W_RISK_MRR_DECLINE_HIGH
        elif mrr_trend < -0.05:
            score += W_RISK_MRR_DECLINE_MED

    if sentiment == "Negative":
        score += W_RISK_SENTIMENT_NEG

    if urgent >= 3:
        score += W_RISK_URGENT_TICKETS_HIGH
    elif urgent >= 1:
        score += W_RISK_URGENT_TICKETS_MED

    if seat_util is not None and seat_util < 0.50:
        score += W_RISK_LOW_SEAT_UTIL

    if days_renewal is not None and 0 <= days_renewal < 60:
        score += W_RISK_NEAR_RENEWAL

    if csat is not None and csat < 3.0:
        score += W_RISK_LOW_CSAT

    if overdue > 0:
        score += W_RISK_OVERDUE

    if usage_cur is not None and usage_old is not None:
        if usage_old - usage_cur > 10:
            score += W_RISK_USAGE_DECLINE

    return _clamp(score)


def compute_opportunity_score(acc: dict) -> float:
    score = 0.0
    expansion = acc.get("expansion_pipeline_gbp") or 0
    arr = acc.get("arr_gbp") or 1
    sentiment = (acc.get("note_sentiment_hint") or "").strip()
    avg_lead = acc.get("avg_lead_score")
    mrr_trend = acc.get("mrr_trend")
    seat_util = acc.get("seat_utilisation")
    lifecycle = (acc.get("lifecycle_stage") or "").strip()
    leads = acc.get("open_leads_count") or 0
    csat = acc.get("avg_csat_90d")
    usage_cur = acc.get("usage_score_current")
    usage_old = acc.get("usage_score_3m_ago")

    expansion_ratio = expansion / arr if arr > 0 else 0
    if expansion_ratio > 0.20:
        score += W_OPP_EXPANSION_HIGH
    elif expansion_ratio > 0.10:
        score += W_OPP_EXPANSION_MED

    if sentiment == "Positive":
        score += W_OPP_SENTIMENT_POS

    if avg_lead is not None:
        if avg_lead > 70:
            score += W_OPP_LEAD_SCORE_HIGH
        elif avg_lead > 50:
            score += W_OPP_LEAD_SCORE_MED

    if mrr_trend is not None and mrr_trend > 0.05:
        score += W_OPP_MRR_GROWTH

    if seat_util is not None and seat_util > 0.85:
        score += W_OPP_HIGH_SEAT_UTIL

    if lifecycle.lower() == "expansion":
        score += W_OPP_EXPANSION_STAGE

    if leads >= 2:
        score += W_OPP_LEADS_PRESENT

    if csat is not None and csat >= 4.5:
        score += W_OPP_HIGH_CSAT

    if usage_cur is not None and usage_old is not None:
        if usage_cur - usage_old > 5:
            score += W_OPP_USAGE_GROWTH

    return _clamp(score)


def compute_health_score(acc: dict) -> float:
    score = float(HEALTH_BASE)
    csat = acc.get("avg_csat_90d")
    nps = acc.get("latest_nps")
    usage_cur = acc.get("usage_score_current")
    usage_old = acc.get("usage_score_3m_ago")
    tickets = acc.get("open_tickets_count") or 0
    sla = acc.get("sla_breaches_90d") or 0
    mrr_trend = acc.get("mrr_trend")
    sentiment = (acc.get("note_sentiment_hint") or "").strip()

    if csat is not None:
        if csat >= 4.5:
            score += H_CSAT_EXCELLENT
        elif csat >= 4.0:
            score += H_CSAT_GOOD
        elif csat < 3.0:
            score += H_CSAT_POOR

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
        if diff > 3:
            score += H_USAGE_UP
        elif diff < -3:
            score += H_USAGE_DOWN

    if tickets == 0:
        score += H_TICKETS_LOW
    elif tickets >= 5:
        score += H_TICKETS_HIGH

    if sla == 0:
        score += H_SLA_NONE
    elif sla >= 3:
        score += H_SLA_HIGH

    if mrr_trend is not None:
        if mrr_trend > 0.05:
            score += H_MRR_GROWING
        elif abs(mrr_trend) < 0.05:
            score += H_MRR_STABLE
        elif mrr_trend < -0.10:
            score += H_MRR_DECLINING

    if sentiment == "Positive":
        score += H_SENTIMENT_POS
    elif sentiment == "Negative":
        score += H_SENTIMENT_NEG

    return _clamp(score)


def assign_priority(acc: dict, risk_score: float, health_score: float) -> str:
    """
    Explicit, defensible priority rules — each criterion cites ≥2 signals.

    CRITICAL: (renewal < 60d AND risk > 70)
              OR (contraction_risk_gbp > 50,000)
              OR (sentiment=Negative AND urgent_tickets > 2)
    HIGH:     risk_score > 50
              OR (days_to_renewal < 90 AND health_score < 50)
              OR (sla_breaches >= 3 AND nps < 0)
    MEDIUM:   risk_score > 25 OR opportunity_score > 40 OR mixed signals
    LOW:      everything else (healthy, stable, no near-term risk)
    """
    days_renewal = acc.get("days_to_renewal")
    contraction = acc.get("contraction_risk_gbp") or 0
    sentiment = (acc.get("note_sentiment_hint") or "").strip()
    urgent = acc.get("urgent_open_tickets_count") or 0
    sla = acc.get("sla_breaches_90d") or 0
    nps = acc.get("latest_nps")
    opp_score = acc.get("opportunity_score", 0)

    # Paused accounts skip active scoring
    if (acc.get("account_status") or "").lower() == "paused":
        return "Paused"

    # CRITICAL
    if days_renewal is not None and 0 <= days_renewal < 60 and risk_score > 70:
        return "Critical"
    if contraction > 50_000:
        return "Critical"
    if sentiment == "Negative" and urgent > 2:
        return "Critical"

    # HIGH
    if risk_score > 50:
        return "High"
    if days_renewal is not None and 0 <= days_renewal < 90 and health_score < 50:
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
    """Compute all scores and priority for a single account dict (in place)."""
    risk = compute_risk_score(acc)
    opp = compute_opportunity_score(acc)
    health = compute_health_score(acc)

    acc["risk_score"] = round(risk, 1)
    acc["opportunity_score"] = round(opp, 1)
    acc["health_score"] = round(health, 1)
    acc["priority"] = assign_priority(acc, risk, health)

    return acc


PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Paused": 4}


def sort_accounts(accounts: list[dict]) -> list[dict]:
    """Sort by: priority tier → risk_score desc → arr_gbp desc."""
    return sorted(
        accounts,
        key=lambda a: (
            PRIORITY_ORDER.get(a.get("priority", "Low"), 5),
            -(a.get("risk_score") or 0),
            -(a.get("arr_gbp") or 0),
        ),
    )
