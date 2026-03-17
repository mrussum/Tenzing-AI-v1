"""FastAPI application — account prioritisation tool."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

load_dotenv()

from auth import authenticate_user, create_access_token, get_current_user
from data_loader import load_accounts
from models import (
    AccountDetail,
    AccountSummary,
    AIAnalysis,
    Decision,
    DecisionCreate,
    LoginRequest,
    PortfolioKPIs,
    PortfolioSummary,
    TokenResponse,
)
from scoring import enrich_account, sort_accounts
from ai_service import analyse_account, generate_portfolio_briefing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

_accounts: list[dict] = []
_decisions: dict[str, list[dict]] = {}          # account_id → list of decision dicts
_ai_cache: dict[str, AIAnalysis] = {}           # account_id → cached AI analysis
_portfolio_briefing_cache: Optional[str] = None
_portfolio_briefing_time: Optional[datetime] = None


def _load_and_enrich() -> list[dict]:
    raw = load_accounts()
    enriched = [enrich_account(acc) for acc in raw]
    return sort_accounts(enriched)


def _get_account_or_404(account_id: str) -> dict:
    for acc in _accounts:
        if acc["account_id"] == account_id:
            return acc
    raise HTTPException(status_code=404, detail=f"Account {account_id!r} not found")


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Account Prioritisation API",
    description="Tenzing AI — B2B SaaS account intelligence",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    global _accounts
    logger.info("Loading and scoring accounts...")
    _accounts = _load_and_enrich()
    logger.info("Loaded %d accounts", len(_accounts))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token({"sub": user["username"]}))


@app.post("/auth/login/json", response_model=TokenResponse)
async def login_json(body: LoginRequest):
    """JSON-body login for the React frontend."""
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    return TokenResponse(access_token=create_access_token({"sub": user["username"]}))


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@app.get("/accounts", response_model=list[AccountSummary])
async def list_accounts(
    region: Optional[str] = None,
    segment: Optional[str] = None,
    lifecycle_stage: Optional[str] = None,
    owner: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    results = _accounts
    if region:
        results = [a for a in results if (a.get("region") or "").lower() == region.lower()]
    if segment:
        results = [a for a in results if (a.get("segment") or "").lower() == segment.lower()]
    if lifecycle_stage:
        results = [a for a in results if (a.get("lifecycle_stage") or "").lower() == lifecycle_stage.lower()]
    if owner:
        results = [
            a for a in results
            if (a.get("account_owner") or "").lower() == owner.lower()
            or (a.get("csm_owner") or "").lower() == owner.lower()
        ]
    return [AccountSummary(**{k: a.get(k) for k in AccountSummary.model_fields}) for a in results]


@app.get("/accounts/{account_id}", response_model=AccountDetail)
async def get_account(
    account_id: str,
    current_user: str = Depends(get_current_user),
):
    """Full account detail. AI analysis is fetched separately via /accounts/{id}/analysis."""
    acc = _get_account_or_404(account_id)
    detail = acc.copy()
    detail["decisions"] = [Decision(**d) for d in _decisions.get(account_id, [])]
    detail["ai_analysis"] = _ai_cache.get(account_id)
    return AccountDetail(**{k: detail.get(k) for k in AccountDetail.model_fields})


@app.get("/accounts/{account_id}/analysis", response_model=AIAnalysis)
async def get_account_analysis(
    account_id: str,
    refresh: bool = False,
    current_user: str = Depends(get_current_user),
):
    """
    Fetch (or generate) AI analysis for a single account.
    Results are cached in memory for the lifetime of the server process.
    Pass ?refresh=true to force a fresh Claude call (e.g. after adding notes).
    """
    acc = _get_account_or_404(account_id)

    if account_id in _ai_cache and not refresh:
        return _ai_cache[account_id]

    logger.info("Generating AI analysis for %s", account_id)
    analysis = analyse_account(acc)
    _ai_cache[account_id] = analysis
    return analysis


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

@app.get("/portfolio/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    with_ai: bool = False,
    current_user: str = Depends(get_current_user),
):
    global _portfolio_briefing_cache, _portfolio_briefing_time

    active = [a for a in _accounts if (a.get("account_status") or "").lower() != "paused"]
    total_arr  = sum(a.get("arr_gbp") or 0 for a in active)
    at_risk    = sum(1 for a in active if (a.get("risk_score") or 0) > 50)
    expansion  = sum(1 for a in active if (a.get("opportunity_score") or 0) > 50)
    avg_health = sum(a.get("health_score") or 0 for a in active) / len(active) if active else 0

    p_counts: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Paused": 0}
    for a in _accounts:
        p = a.get("priority", "Low")
        if p in p_counts:
            p_counts[p] += 1

    kpis = PortfolioKPIs(
        total_arr_gbp=round(total_arr, 2),
        accounts_at_risk=at_risk,
        expansion_opportunities=expansion,
        avg_health_score=round(avg_health, 1),
        critical_count=p_counts["Critical"],
        high_count=p_counts["High"],
        medium_count=p_counts["Medium"],
        low_count=p_counts["Low"],
        paused_count=p_counts["Paused"],
    )

    briefing, generated_at = None, None
    if with_ai:
        if _portfolio_briefing_cache is None:
            _portfolio_briefing_cache = generate_portfolio_briefing(_accounts, kpis.model_dump())
            _portfolio_briefing_time = datetime.utcnow()
        briefing, generated_at = _portfolio_briefing_cache, _portfolio_briefing_time

    return PortfolioSummary(kpis=kpis, briefing=briefing, generated_at=generated_at)


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

@app.post("/accounts/{account_id}/decisions", response_model=Decision)
async def record_decision(
    account_id: str,
    body: DecisionCreate,
    current_user: str = Depends(get_current_user),
):
    _get_account_or_404(account_id)
    decision = {
        "id": str(uuid.uuid4()),
        "account_id": account_id,
        "text": body.text,
        "decided_by": body.decided_by or current_user,
        "timestamp": datetime.utcnow(),
    }
    _decisions.setdefault(account_id, []).append(decision)
    return Decision(**decision)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "accounts_loaded": len(_accounts),
        "ai_analyses_cached": len(_ai_cache),
    }


@app.get("/filters/options")
async def filter_options(current_user: str = Depends(get_current_user)):
    return {
        "regions":          sorted({a.get("region")         for a in _accounts if a.get("region")}),
        "segments":         sorted({a.get("segment")        for a in _accounts if a.get("segment")}),
        "lifecycle_stages": sorted({a.get("lifecycle_stage") for a in _accounts if a.get("lifecycle_stage")}),
        "owners": sorted({
            name
            for a in _accounts
            for name in [a.get("account_owner"), a.get("csm_owner")]
            if name
        }),
    }
