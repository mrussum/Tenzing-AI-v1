"""Tests for deterministic scoring and priority assignment.

Run with: pytest tests/test_scoring.py -v
All tests must pass with no external dependencies.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring import (
    compute_risk_score,
    compute_opportunity_score,
    compute_health_score,
    assign_priority,
    enrich_account,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def base_account(**kwargs) -> dict:
    """Return a minimal valid account dict with all signal fields null by default.
    Override specific fields via kwargs. This keeps each test focused."""
    defaults = {
        "account_id": "TEST-001",
        "account_name": "Test Account",
        "account_status": "Active",
        "lifecycle_stage": "Customer",
        "arr_gbp": 100_000,
        "mrr_current_gbp": None,
        "mrr_3m_ago_gbp": None,
        "mrr_trend": None,
        "expansion_pipeline_gbp": None,
        "contraction_risk_gbp": None,
        "overdue_amount_gbp": None,
        "seats_purchased": None,
        "seats_used": None,
        "seat_utilisation": None,
        "usage_score_current": None,
        "usage_score_3m_ago": None,
        "latest_nps": None,
        "avg_csat_90d": None,
        "open_tickets_count": None,
        "urgent_open_tickets_count": None,
        "sla_breaches_90d": None,
        "open_leads_count": None,
        "avg_lead_score": None,
        "note_sentiment_hint": None,
        "days_to_renewal": None,
        "opportunity_score": 0,
    }
    defaults.update(kwargs)
    return defaults


# ── Risk score tests ──────────────────────────────────────────────────────────

class TestRiskScore:

    def test_all_null_fields_returns_low_score(self):
        acc = base_account()
        score = compute_risk_score(acc)
        assert score < 20, f"All-null account should score low risk, got {score}"

    def test_negative_nps_increases_risk(self):
        low = compute_risk_score(base_account(latest_nps=50))
        high = compute_risk_score(base_account(latest_nps=-10))
        assert high > low, "Negative NPS should produce higher risk than positive NPS"

    def test_high_sla_breaches_increases_risk(self):
        low  = compute_risk_score(base_account(sla_breaches_90d=0))
        high = compute_risk_score(base_account(sla_breaches_90d=3))
        assert high > low, "High SLA breaches should produce higher risk"

    def test_high_contraction_risk_increases_risk(self):
        # > 30% of ARR = £30,000 contraction on £100k ARR
        low  = compute_risk_score(base_account(contraction_risk_gbp=5_000))
        high = compute_risk_score(base_account(contraction_risk_gbp=35_000))
        assert high > low

    def test_mrr_decline_increases_risk(self):
        low  = compute_risk_score(base_account(mrr_trend=0.05))
        high = compute_risk_score(base_account(mrr_trend=-0.15))
        assert high > low, "MRR decline should raise risk"

    def test_positive_mrr_trend_does_not_raise_risk(self):
        neutral = compute_risk_score(base_account())
        positive = compute_risk_score(base_account(mrr_trend=0.10))
        # Positive MRR should not raise risk above the null baseline
        assert positive <= neutral + 5  # small tolerance

    def test_negative_sentiment_increases_risk(self):
        low  = compute_risk_score(base_account(note_sentiment_hint="Positive"))
        high = compute_risk_score(base_account(note_sentiment_hint="Negative"))
        assert high > low

    def test_urgent_tickets_increase_risk(self):
        low  = compute_risk_score(base_account(urgent_open_tickets_count=0))
        high = compute_risk_score(base_account(urgent_open_tickets_count=3))
        assert high > low

    def test_near_renewal_increases_risk(self):
        far  = compute_risk_score(base_account(days_to_renewal=180))
        near = compute_risk_score(base_account(days_to_renewal=30))
        assert near > far

    def test_score_bounded_0_to_100(self):
        # Worst possible account — all bad signals
        worst = base_account(
            latest_nps=-50,
            sla_breaches_90d=5,
            contraction_risk_gbp=80_000,
            mrr_trend=-0.30,
            note_sentiment_hint="Negative",
            urgent_open_tickets_count=5,
            avg_csat_90d=1.0,
            overdue_amount_gbp=5_000,
            days_to_renewal=20,
            seat_utilisation=0.30,
            usage_score_current=20,
            usage_score_3m_ago=50,
        )
        score = compute_risk_score(worst)
        assert 0 <= score <= 100, f"Score out of bounds: {score}"

    def test_overdue_amount_increases_risk(self):
        no_overdue = compute_risk_score(base_account(overdue_amount_gbp=0))
        overdue    = compute_risk_score(base_account(overdue_amount_gbp=5_000))
        assert overdue > no_overdue


# ── Opportunity score tests ───────────────────────────────────────────────────

class TestOpportunityScore:

    def test_all_null_returns_low_score(self):
        score = compute_opportunity_score(base_account())
        assert score < 25

    def test_large_pipeline_increases_opportunity(self):
        low  = compute_opportunity_score(base_account(expansion_pipeline_gbp=5_000))
        high = compute_opportunity_score(base_account(expansion_pipeline_gbp=25_000))
        assert high > low

    def test_positive_sentiment_increases_opportunity(self):
        neutral  = compute_opportunity_score(base_account(note_sentiment_hint="Neutral"))
        positive = compute_opportunity_score(base_account(note_sentiment_hint="Positive"))
        assert positive > neutral

    def test_expansion_lifecycle_stage_increases_opportunity(self):
        customer  = compute_opportunity_score(base_account(lifecycle_stage="Customer"))
        expansion = compute_opportunity_score(base_account(lifecycle_stage="Expansion"))
        assert expansion > customer

    def test_mrr_growth_increases_opportunity(self):
        flat    = compute_opportunity_score(base_account(mrr_trend=0.0))
        growing = compute_opportunity_score(base_account(mrr_trend=0.10))
        assert growing > flat

    def test_high_seat_utilisation_increases_opportunity(self):
        low  = compute_opportunity_score(base_account(seat_utilisation=0.50))
        high = compute_opportunity_score(base_account(seat_utilisation=0.90))
        assert high > low

    def test_score_bounded_0_to_100(self):
        best = base_account(
            expansion_pipeline_gbp=30_000,
            note_sentiment_hint="Positive",
            avg_lead_score=90,
            mrr_trend=0.15,
            seat_utilisation=0.95,
            lifecycle_stage="Expansion",
            open_leads_count=4,
            avg_csat_90d=5.0,
            usage_score_current=80,
            usage_score_3m_ago=70,
        )
        score = compute_opportunity_score(best)
        assert 0 <= score <= 100


# ── Health score tests ────────────────────────────────────────────────────────

class TestHealthScore:

    def test_baseline_with_no_signals_is_above_50(self):
        # Null open_tickets_count and sla_breaches_90d are coerced to 0 (via `or 0`),
        # which triggers the "0 tickets" and "0 SLA breaches" positive modifiers (+8 each).
        # So the true null-field baseline is 50 + 8 + 8 = 66.
        score = compute_health_score(base_account())
        assert score == 66.0, f"Null-field baseline health should be 66 (50 + 8 tickets + 8 SLA), got {score}"

    def test_excellent_csat_raises_health(self):
        baseline = compute_health_score(base_account())
        good     = compute_health_score(base_account(avg_csat_90d=4.8))
        assert good > baseline

    def test_poor_csat_lowers_health(self):
        baseline = compute_health_score(base_account())
        poor     = compute_health_score(base_account(avg_csat_90d=2.0))
        assert poor < baseline

    def test_high_nps_raises_health(self):
        baseline = compute_health_score(base_account())
        good     = compute_health_score(base_account(latest_nps=60))
        assert good > baseline

    def test_negative_nps_lowers_health(self):
        baseline = compute_health_score(base_account())
        bad      = compute_health_score(base_account(latest_nps=-30))
        assert bad < baseline

    def test_score_bounded_0_to_100(self):
        worst = base_account(
            avg_csat_90d=1.0,
            latest_nps=-50,
            usage_score_current=20,
            usage_score_3m_ago=60,
            open_tickets_count=8,
            sla_breaches_90d=4,
            mrr_trend=-0.20,
            note_sentiment_hint="Negative",
        )
        score = compute_health_score(worst)
        assert 0 <= score <= 100


# ── Priority assignment tests ─────────────────────────────────────────────────

class TestPriorityAssignment:

    def test_critical_high_risk_near_renewal(self):
        acc = base_account(days_to_renewal=45)
        assert assign_priority(acc, risk_score=75, health_score=40) == "Critical"

    def test_critical_large_contraction(self):
        acc = base_account(contraction_risk_gbp=60_000)
        assert assign_priority(acc, risk_score=30, health_score=50) == "Critical"

    def test_critical_negative_sentiment_urgent_tickets(self):
        acc = base_account(
            note_sentiment_hint="Negative",
            urgent_open_tickets_count=3,
        )
        assert assign_priority(acc, risk_score=40, health_score=50) == "Critical"

    def test_not_critical_below_risk_threshold(self):
        # Risk score 69 is below 70 — should not be Critical even with near renewal
        acc = base_account(days_to_renewal=55)
        result = assign_priority(acc, risk_score=69, health_score=40)
        assert result != "Critical", f"Expected not Critical, got {result}"

    def test_not_critical_renewal_just_outside_window(self):
        # 60 days is the boundary — 60 itself should NOT trigger Critical
        acc = base_account(days_to_renewal=60)
        result = assign_priority(acc, risk_score=80, health_score=30)
        assert result != "Critical"

    def test_high_risk_score_above_50(self):
        acc = base_account()
        assert assign_priority(acc, risk_score=55, health_score=60) == "High"

    def test_high_near_renewal_low_health(self):
        acc = base_account(days_to_renewal=80)
        assert assign_priority(acc, risk_score=30, health_score=45) == "High"

    def test_high_sla_breaches_negative_nps(self):
        acc = base_account(sla_breaches_90d=3, latest_nps=-5)
        assert assign_priority(acc, risk_score=40, health_score=50) == "High"

    def test_medium_moderate_risk(self):
        acc = base_account()
        assert assign_priority(acc, risk_score=35, health_score=60) == "Medium"

    def test_medium_high_opportunity(self):
        acc = base_account(opportunity_score=50)
        assert assign_priority(acc, risk_score=20, health_score=65) == "Medium"

    def test_low_all_healthy(self):
        acc = base_account(days_to_renewal=180, opportunity_score=10)
        assert assign_priority(acc, risk_score=15, health_score=75) == "Low"

    def test_paused_returns_paused_not_scored(self):
        acc = base_account(account_status="Paused", contraction_risk_gbp=80_000)
        assert assign_priority(acc, risk_score=85, health_score=30) == "Paused"

    def test_paused_not_critical_even_with_critical_signals(self):
        # Paused accounts must never appear as Critical in the active queue
        acc = base_account(
            account_status="Paused",
            days_to_renewal=20,
            note_sentiment_hint="Negative",
            urgent_open_tickets_count=5,
            contraction_risk_gbp=100_000,
        )
        result = assign_priority(acc, risk_score=95, health_score=10)
        assert result == "Paused"

    def test_all_null_fields_does_not_crash(self):
        acc = base_account()
        # Remove arr_gbp to test division guard
        acc["arr_gbp"] = None
        try:
            result = assign_priority(acc, risk_score=0, health_score=50)
            assert result in ("Critical", "High", "Medium", "Low", "Paused")
        except Exception as e:
            assert False, f"assign_priority raised exception on null fields: {e}"

    def test_enrich_account_adds_all_scores(self):
        acc = base_account(
            mrr_current_gbp=10_000,
            mrr_3m_ago_gbp=9_000,
            seats_purchased=100,
            seats_used=80,
        )
        # Manually add derived fields that data_loader would compute
        acc["mrr_trend"] = (10_000 - 9_000) / 9_000
        acc["seat_utilisation"] = 80 / 100
        acc["days_to_renewal"] = 120
        enriched = enrich_account(acc)
        assert "risk_score" in enriched
        assert "opportunity_score" in enriched
        assert "health_score" in enriched
        assert "priority" in enriched
        assert enriched["priority"] in ("Critical", "High", "Medium", "Low", "Paused")
