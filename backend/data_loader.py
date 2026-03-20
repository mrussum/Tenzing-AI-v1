"""CSV parsing and feature engineering for account data."""
from __future__ import annotations
import math
import os
from datetime import date
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# Fields we consider "signal" fields for confidence scoring
SIGNAL_FIELDS = [
    "arr_gbp", "mrr_current_gbp", "mrr_3m_ago_gbp", "renewal_date",
    "seats_purchased", "seats_used", "latest_nps", "avg_csat_90d",
    "open_tickets_count", "urgent_open_tickets_count", "sla_breaches_90d",
    "expansion_pipeline_gbp", "contraction_risk_gbp",
    "usage_score_current", "usage_score_3m_ago",
    "note_sentiment_hint", "recent_support_summary",
    "recent_customer_note", "recent_sales_note",
]

DATA_FILE = Path(__file__).parent.parent / "data" / "account_prioritisation_challenge_data.csv"


def _safe_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    f = _safe_float(val)
    return None if f is None else int(f)


def _safe_str(val: Any) -> Optional[str]:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    s = str(val).strip()
    return None if s == "" or s.lower() == "nan" else s


def load_accounts() -> list[dict]:
    """Load CSV, engineer features, return list of enriched account dicts."""
    df = pd.read_csv(DATA_FILE, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    today = date.today()
    accounts: list[dict] = []

    for _, row in df.iterrows():
        acc: dict[str, Any] = {}

        # ---------------------------------------------------------------
        # Raw fields
        # ---------------------------------------------------------------
        acc["account_id"] = _safe_str(row.get("account_id")) or ""
        acc["external_account_ref"] = _safe_str(row.get("external_account_ref"))
        acc["account_name"] = _safe_str(row.get("account_name")) or acc["account_id"]
        acc["website"] = _safe_str(row.get("website"))
        acc["industry"] = _safe_str(row.get("industry"))
        acc["segment"] = _safe_str(row.get("segment"))
        acc["region"] = _safe_str(row.get("region"))
        acc["account_status"] = _safe_str(row.get("account_status"))
        acc["lifecycle_stage"] = _safe_str(row.get("lifecycle_stage"))
        acc["account_owner"] = _safe_str(row.get("account_owner"))
        acc["csm_owner"] = _safe_str(row.get("csm_owner"))
        acc["support_tier"] = _safe_str(row.get("support_tier"))
        acc["billing_frequency"] = _safe_str(row.get("billing_frequency"))
        acc["billing_currency"] = _safe_str(row.get("billing_currency"))

        # Dates
        acc["contract_start_date"] = _safe_str(row.get("contract_start_date"))
        acc["renewal_date"] = _safe_str(row.get("renewal_date"))
        acc["last_qbr_date"] = _safe_str(row.get("last_qbr_date"))
        acc["latest_note_date"] = _safe_str(row.get("latest_note_date"))
        acc["last_lead_activity_date"] = _safe_str(row.get("last_lead_activity_date"))

        # Commercial
        acc["arr_gbp"] = _safe_float(row.get("arr_gbp"))
        acc["mrr_current_gbp"] = _safe_float(row.get("mrr_current_gbp"))
        acc["mrr_3m_ago_gbp"] = _safe_float(row.get("mrr_3m_ago_gbp"))
        acc["expansion_pipeline_gbp"] = _safe_float(row.get("expansion_pipeline_gbp"))
        acc["contraction_risk_gbp"] = _safe_float(row.get("contraction_risk_gbp"))
        acc["overdue_amount_gbp"] = _safe_float(row.get("overdue_amount_gbp"))

        # Health
        acc["seats_purchased"] = _safe_int(row.get("seats_purchased"))
        acc["seats_used"] = _safe_int(row.get("seats_used"))
        acc["usage_score_current"] = _safe_float(row.get("usage_score_current"))
        acc["usage_score_3m_ago"] = _safe_float(row.get("usage_score_3m_ago"))
        acc["latest_nps"] = _safe_float(row.get("latest_nps"))
        acc["avg_csat_90d"] = _safe_float(row.get("avg_csat_90d"))

        # Support
        acc["open_tickets_count"] = _safe_int(row.get("open_tickets_count"))
        acc["urgent_open_tickets_count"] = _safe_int(row.get("urgent_open_tickets_count"))
        acc["sla_breaches_90d"] = _safe_int(row.get("sla_breaches_90d"))

        # Leads
        acc["open_leads_count"] = _safe_int(row.get("open_leads_count"))
        acc["avg_lead_score"] = _safe_float(row.get("avg_lead_score"))

        # Qualitative
        acc["note_sentiment_hint"] = _safe_str(row.get("note_sentiment_hint"))
        acc["recent_support_summary"] = _safe_str(row.get("recent_support_summary"))
        acc["recent_customer_note"] = _safe_str(row.get("recent_customer_note"))
        acc["recent_sales_note"] = _safe_str(row.get("recent_sales_note"))

        # ---------------------------------------------------------------
        # Null field count for confidence scoring
        # ---------------------------------------------------------------
        null_count = sum(1 for f in SIGNAL_FIELDS if acc.get(f) is None)
        acc["null_field_count"] = null_count
        if null_count > 6:
            acc["confidence"] = "Low"
        elif null_count > 3:
            acc["confidence"] = "Medium"
        else:
            acc["confidence"] = "High"

        # ---------------------------------------------------------------
        # Computed signals
        # ---------------------------------------------------------------

        # MRR trend
        if acc["mrr_current_gbp"] and acc["mrr_3m_ago_gbp"] and acc["mrr_3m_ago_gbp"] != 0:
            acc["mrr_trend"] = (acc["mrr_current_gbp"] - acc["mrr_3m_ago_gbp"]) / acc["mrr_3m_ago_gbp"]
        else:
            acc["mrr_trend"] = None

        # Seat utilisation
        if acc["seats_purchased"] and acc["seats_used"] and acc["seats_purchased"] > 0:
            acc["seat_utilisation"] = acc["seats_used"] / acc["seats_purchased"]
        else:
            acc["seat_utilisation"] = None

        # Days to renewal
        if acc["renewal_date"]:
            try:
                renewal = date.fromisoformat(acc["renewal_date"])
                acc["days_to_renewal"] = (renewal - today).days
            except ValueError:
                acc["days_to_renewal"] = None
        else:
            acc["days_to_renewal"] = None

        accounts.append(acc)

    return accounts
