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
_decisions: dict[str, list[dict]] = {}  # account_id → list of decision dicts
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
    token = create_access_token({"sub": user["username"]})
    return TokenResponse(access_token=token)


@app.post("/auth/login/json", response_model=TokenResponse)
async def login_json(body: LoginRequest):
    """JSON-body alternative to the form-based /auth/login (for frontend fetch)."""
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": user["username"]})
    return TokenResponse(access_token=token)


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
    """Return all accounts sorted by priority. Supports optional filter params."""
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
    with_ai: bool = False,
    current_user: str = Depends(get_current_user),
):
    """Return full account detail. Pass ?with_ai=true to include AI analysis."""
    acc = _get_account_or_404(account_id)
    detail = acc.copy()

    # Attach decisions
    detail["decisions"] = [
        Decision(**d) for d in _decisions.get(account_id, [])
    ]

    if with_ai:
        ai = analyse_account(acc)
        detail["ai_analysis"] = ai

    return AccountDetail(**{k: detail.get(k) for k in AccountDetail.model_fields})


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

@app.get("/portfolio/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    with_ai: bool = False,
    current_user: str = Depends(get_current_user),
):
    """Return KPIs + optional AI leadership briefing."""
    global _portfolio_briefing_cache, _portfolio_briefing_time

    active = [a for a in _accounts if (a.get("account_status") or "").lower() != "paused"]
    total_arr = sum(a.get("arr_gbp") or 0 for a in active)
    at_risk = sum(1 for a in active if (a.get("risk_score") or 0) > 50)
    expansion = sum(1 for a in active if (a.get("opportunity_score") or 0) > 50)
    avg_health = (
        sum(a.get("health_score") or 0 for a in active) / len(active)
        if active else 0
    )

    priority_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Paused": 0}
    for a in _accounts:
        p = a.get("priority", "Low")
        if p in priority_counts:
            priority_counts[p] += 1

    kpis = PortfolioKPIs(
        total_arr_gbp=round(total_arr, 2),
        accounts_at_risk=at_risk,
        expansion_opportunities=expansion,
        avg_health_score=round(avg_health, 1),
        critical_count=priority_counts["Critical"],
        high_count=priority_counts["High"],
        medium_count=priority_counts["Medium"],
        low_count=priority_counts["Low"],
        paused_count=priority_counts["Paused"],
    )

    briefing = None
    generated_at = None

    if with_ai:
        if _portfolio_briefing_cache is None:
            kpi_dict = kpis.model_dump()
            _portfolio_briefing_cache = generate_portfolio_briefing(_accounts, kpi_dict)
            _portfolio_briefing_time = datetime.utcnow()
        briefing = _portfolio_briefing_cache
        generated_at = _portfolio_briefing_time

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
    """Record a decision / action taken on an account."""
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
    return {"status": "ok", "accounts_loaded": len(_accounts)}


@app.get("/filters/options")
async def filter_options(current_user: str = Depends(get_current_user)):
    """Return distinct values for filter dropdowns."""
    return {
        "regions": sorted({a.get("region") for a in _accounts if a.get("region")}),
        "segments": sorted({a.get("segment") for a in _accounts if a.get("segment")}),
        "lifecycle_stages": sorted({a.get("lifecycle_stage") for a in _accounts if a.get("lifecycle_stage")}),
        "owners": sorted({
            name
            for a in _accounts
            for name in [a.get("account_owner"), a.get("csm_owner")]
            if name
        }),
    }
