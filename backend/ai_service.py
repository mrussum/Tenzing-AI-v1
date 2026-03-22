"""Anthropic integration for per-account analysis and portfolio briefing."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

import anthropic

from models import AIAnalysis, AIAction, AIOpportunity, AIRisk

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def _build_account_context(acc: dict) -> str:
    """Serialise account data into a structured context block for Claude."""
    # Strip internal scoring artefacts; keep all business signals
    exclude = {"ai_analysis", "decisions"}
    payload = {k: v for k, v in acc.items() if k not in exclude}
    return json.dumps(payload, indent=2, default=str)


ACCOUNT_SYSTEM_PROMPT = """You are a B2B SaaS account intelligence system for a private equity portfolio company.
Your role is to analyse account signals and produce clear, defensible, data-driven assessments.
Always cite specific numbers from the data. Never hallucinate data points that are not present.
If key data is missing, acknowledge the gap rather than guessing.
You are provided the deterministic priority label. You must use exactly this label in your response.
Never reassign or modify the priority label."""

ACCOUNT_USER_TEMPLATE = """Analyse this B2B SaaS account and produce a JSON response.

ACCOUNT DATA:
{context}

DETERMINISTIC PRIORITY (do not override):
The scoring engine has classified this account as: {deterministic_priority}
This label was assigned by explicit rules based on risk score, contraction risk,
renewal timeline, and sentiment signals.
Your role is to EXPLAIN and EXTEND this classification — not reassign it.
Do not return a different priority value.

INSTRUCTIONS:
- priority must be one of: "Critical", "High", "Medium", "Low"
- priority_reasoning: 2-3 sentence explanation citing at least 2 specific data points (numbers, dates, scores)
- top_risks: array of up to 3 objects with "risk" (short label) and "evidence" (specific data-backed sentence)
- top_opportunities: array of up to 3 objects with "opportunity" (short label) and "evidence" (specific data-backed sentence)
- recommended_actions: array of exactly 3 objects with "action" (concrete specific ask) and "owner" (one of: CSM / Sales / Leadership)
- confidence: "High" if all major signals are present, "Medium" if some gaps, "Low" if >4 key fields are null

Where notes fields are null or empty, state "insufficient qualitative data" — do not invent sentiment.
Recommended actions must be specific: name the signal, the ask, and why now.

Return ONLY valid JSON. No markdown. No preamble. No trailing text."""


def analyse_account(acc: dict) -> AIAnalysis:
    """Call Claude to produce per-account priority + reasoning + actions."""
    deterministic_priority = acc.get("priority", "Medium")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return AIAnalysis(
            priority=deterministic_priority,
            priority_reasoning="AI analysis unavailable — ANTHROPIC_API_KEY not configured.",
            confidence="Low",
            error="ANTHROPIC_API_KEY not set",
        )

    context = _build_account_context(acc)

    # Flag insufficient qualitative data explicitly
    missing_notes = all(
        acc.get(f) is None
        for f in ["recent_support_summary", "recent_customer_note", "recent_sales_note"]
    )
    qualifier = "\nNote: All qualitative note fields are null for this account — state 'insufficient qualitative data' for sentiment-based assessments.\n" if missing_notes else ""

    user_prompt = ACCOUNT_USER_TEMPLATE.format(
        context=context,
        deterministic_priority=deterministic_priority,
    ) + qualifier

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ACCOUNT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()

        # Parse JSON — handle occasional markdown wrapping
        text = raw
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        data = json.loads(text)

        risks = [AIRisk(**r) if isinstance(r, dict) else AIRisk(risk=str(r), evidence="") for r in data.get("top_risks", [])]
        opps = [AIOpportunity(**o) if isinstance(o, dict) else AIOpportunity(opportunity=str(o), evidence="") for o in data.get("top_opportunities", [])]
        actions = [AIAction(**a) if isinstance(a, dict) else AIAction(action=str(a), owner="CSM") for a in data.get("recommended_actions", [])]

        # Deterministic priority is the source of truth — AI cannot override it
        return AIAnalysis(
            priority=deterministic_priority,  # enforced — not from Claude
            priority_reasoning=data.get("priority_reasoning", ""),
            top_risks=risks,
            top_opportunities=opps,
            recommended_actions=actions,
            confidence=data.get("confidence", acc.get("confidence", "Medium")),
            raw_response=raw,
            prompt_version="1.1",
        )

    except json.JSONDecodeError as e:
        logger.error("JSON parse error for %s: %s", acc.get("account_id"), e)
        return AIAnalysis(
            priority=deterministic_priority,
            priority_reasoning="AI response could not be parsed.",
            confidence="Low",
            error="AI response parsing failed.",
            raw_response=raw if "raw" in dir() else None,
            prompt_version="1.1",
        )
    except Exception as e:
        logger.error("AI error for %s: %s", acc.get("account_id"), e)
        return AIAnalysis(
            priority=deterministic_priority,
            priority_reasoning="AI analysis failed.",
            confidence="Low",
            error="AI analysis unavailable.",
            prompt_version="1.1",
        )


# ---------------------------------------------------------------------------
# Portfolio-level briefing
# ---------------------------------------------------------------------------

PORTFOLIO_SYSTEM_PROMPT = """You are a senior account intelligence analyst preparing an executive briefing
for private equity leadership. Be concise, data-driven, and identify cross-cutting patterns.
Format your response in clear sections using plain text (no markdown headers)."""

PORTFOLIO_USER_TEMPLATE = """Produce a portfolio-level leadership briefing for this B2B SaaS account portfolio.

PORTFOLIO SUMMARY STATISTICS:
{stats}

TOP ACCOUNTS BY RISK (full data):
{top_risk_accounts}

CRITICAL AND HIGH PRIORITY ACCOUNTS:
{critical_high}

INSTRUCTIONS:
1. Open with a 2-sentence executive summary of the portfolio health
2. Identify 3-4 cross-cutting themes (e.g. "3 Enterprise EU accounts share SLA breach patterns") — cite account names and data
3. Flag the top 3 accounts requiring immediate leadership attention — explain why with specific data points
4. Identify the top 3 expansion opportunities — cite account names, pipeline values, and signals
5. Close with 3 recommended portfolio-level actions for the leadership team

Be specific. Cite account names, numbers, dates. Avoid generalities.
Write in a direct, professional tone suitable for a PE board briefing. Plain text, no markdown."""


def generate_portfolio_briefing(accounts: list[dict], kpis: dict) -> str:
    """Generate an AI narrative for the leadership briefing page."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "Portfolio briefing unavailable — ANTHROPIC_API_KEY not configured."

    # Sort by risk score, take top 8 for detail context
    by_risk = sorted(accounts, key=lambda a: -(a.get("risk_score") or 0))
    top_risk = by_risk[:8]

    critical_high = [a for a in accounts if a.get("priority") in ("Critical", "High")]

    # Build lightweight summaries (not full payloads — saves tokens)
    def _brief(a: dict) -> dict:
        return {
            "account_name": a.get("account_name"),
            "segment": a.get("segment"),
            "region": a.get("region"),
            "arr_gbp": a.get("arr_gbp"),
            "days_to_renewal": a.get("days_to_renewal"),
            "risk_score": a.get("risk_score"),
            "opportunity_score": a.get("opportunity_score"),
            "health_score": a.get("health_score"),
            "priority": a.get("priority"),
            "mrr_trend": round(a.get("mrr_trend") or 0, 3),
            "sla_breaches_90d": a.get("sla_breaches_90d"),
            "contraction_risk_gbp": a.get("contraction_risk_gbp"),
            "expansion_pipeline_gbp": a.get("expansion_pipeline_gbp"),
            "latest_nps": a.get("latest_nps"),
            "note_sentiment_hint": a.get("note_sentiment_hint"),
            "lifecycle_stage": a.get("lifecycle_stage"),
        }

    stats = json.dumps(kpis, indent=2, default=str)
    top_risk_str = json.dumps([_brief(a) for a in top_risk], indent=2, default=str)
    critical_high_str = json.dumps([_brief(a) for a in critical_high], indent=2, default=str)

    user_prompt = PORTFOLIO_USER_TEMPLATE.format(
        stats=stats,
        top_risk_accounts=top_risk_str,
        critical_high=critical_high_str,
    )

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=PORTFOLIO_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.error("Portfolio briefing error: %s", e)
        return "Portfolio briefing generation failed. Please try again later."
