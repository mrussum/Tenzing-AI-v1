"""FastAPI application — account prioritisation tool."""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

load_dotenv()

from auth import authenticate_user, create_access_token, get_current_user
from data_loader import load_accounts
from database import Base, engine, get_db
from db_models import DBAIAnalysisCache, DBDecision, DBPortfolioBriefingCache
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

LOGIN_RATE_LIMIT = "5/minute"


def _real_client_ip(request: Request) -> str:
    """Read the real client IP, accounting for Render's load balancer proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host


limiter = Limiter(key_func=_real_client_ip)

# ---------------------------------------------------------------------------
# In-memory state (read-only accounts list; write state lives in DB)
# ---------------------------------------------------------------------------

_accounts: list[dict] = []


def _load_and_enrich() -> list[dict]:
    raw = load_accounts()
    enriched = [enrich_account(acc) for acc in raw]
    return sort_accounts(enriched)


def _get_account_or_404(account_id: str, current_user: str) -> dict:
    """Fetch account from in-memory list and assert caller is authorised.

    Currently all accounts belong to "admin". When multi-user is introduced,
    add an owner_user_id column to accounts and check:
        if account["owner_user_id"] != current_user: raise 403
    """
    for acc in _accounts:
        if acc["account_id"] == account_id:
            # Phase 4 IDOR guard — extend this when real multi-user is added
            if current_user != "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
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
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Read allowed origins from environment — defaults to localhost for dev
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


async def _prewarm_ai_analyses(db_session_factory):
    """Pre-compute AI analysis for Critical and High accounts at startup.
    Runs in background — does not block app startup.
    Low priority accounts are analysed lazily on first user request.
    """
    priority_accounts = [
        a for a in _accounts
        if a.get("priority") in ("Critical", "High")
    ]
    logger.info(
        "Pre-warming AI analysis for %d Critical/High accounts...",
        len(priority_accounts)
    )
    from database import SessionLocal
    db = SessionLocal()
    try:
        for acc in priority_accounts:
            account_id = acc.get("account_id")
            # Skip if already cached
            from db_models import DBAIAnalysisCache
            existing = db.query(DBAIAnalysisCache).filter_by(
                account_id=account_id
            ).first()
            if existing:
                continue
            try:
                from ai_service import analyse_account
                analysis = analyse_account(acc)
                payload = analysis.model_dump_json()
                db.add(DBAIAnalysisCache(
                    account_id=account_id,
                    payload=payload,
                    created_at=datetime.utcnow()
                ))
                db.commit()
                logger.info("Pre-warmed analysis for %s (%s)",
                           acc.get("account_name"), acc.get("priority"))
                # Small delay to avoid rate limiting
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.warning("Pre-warm failed for %s: %s", account_id, e)
    finally:
        db.close()
    logger.info("AI pre-warm complete")


@app.on_event("startup")
async def startup_event():
    global _accounts
    # Create tables if they don't exist (idempotent; alembic handles real migrations)
    Base.metadata.create_all(bind=engine)
    logger.info("Loading and scoring accounts...")
    _accounts = _load_and_enrich()
    logger.info("Loaded %d accounts", len(_accounts))

    # Pre-warm AI for Critical/High accounts in background
    # Only if API key is present — skip silently otherwise
    if os.environ.get("ANTHROPIC_API_KEY"):
        asyncio.create_task(_prewarm_ai_analyses(None))
        logger.info("AI pre-warm task scheduled for Critical/High accounts")
    else:
        logger.warning("ANTHROPIC_API_KEY not set — AI pre-warm skipped")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token({"sub": user["username"]}))


@app.post("/auth/login/json")
@limiter.limit(LOGIN_RATE_LIMIT)
async def login_json(request: Request, body: LoginRequest):
    """JSON-body login for the React frontend. Returns JWT in response body."""
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/logout")
async def logout():
    return {"ok": True}


@app.get("/auth/me")
async def me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}


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
    db: Session = Depends(get_db),
):
    """Full account detail. AI analysis is fetched separately via /accounts/{id}/analysis."""
    acc = _get_account_or_404(account_id, current_user)
    detail = acc.copy()

    db_decisions = db.query(DBDecision).filter_by(account_id=account_id).all()
    detail["decisions"] = [
        Decision(
            id=d.id,
            account_id=d.account_id,
            text=d.text,
            decided_by=d.decided_by,
            timestamp=d.timestamp,
        )
        for d in db_decisions
    ]

    cached = db.query(DBAIAnalysisCache).filter_by(account_id=account_id).first()
    detail["ai_analysis"] = AIAnalysis(**json.loads(cached.payload)) if cached else None

    return AccountDetail(**{k: detail.get(k) for k in AccountDetail.model_fields})


@app.get("/accounts/{account_id}/analysis", response_model=AIAnalysis)
async def get_account_analysis(
    account_id: str,
    refresh: bool = False,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch (or generate) AI analysis for a single account.
    Results are persisted in PostgreSQL so they survive redeploys.
    Pass ?refresh=true to force a fresh Claude call.
    """
    acc = _get_account_or_404(account_id, current_user)

    cached = db.query(DBAIAnalysisCache).filter_by(account_id=account_id).first()
    if cached and not refresh:
        return AIAnalysis(**json.loads(cached.payload))

    logger.info("Generating AI analysis for %s", account_id)
    analysis = analyse_account(acc)

    payload = analysis.model_dump_json()
    if cached:
        cached.payload = payload
        cached.created_at = datetime.utcnow()
    else:
        db.add(DBAIAnalysisCache(account_id=account_id, payload=payload, created_at=datetime.utcnow()))
    db.commit()

    return analysis


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

@app.get("/portfolio/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    with_ai: bool = False,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        cached = db.query(DBPortfolioBriefingCache).filter_by(id=1).first()
        if cached is None:
            briefing_text = generate_portfolio_briefing(_accounts, kpis.model_dump())
            now = datetime.utcnow()
            db.add(DBPortfolioBriefingCache(id=1, briefing=briefing_text, generated_at=now))
            db.commit()
            briefing, generated_at = briefing_text, now
        else:
            briefing, generated_at = cached.briefing, cached.generated_at

    return PortfolioSummary(kpis=kpis, briefing=briefing, generated_at=generated_at)


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

@app.post("/accounts/{account_id}/decisions", response_model=Decision)
async def record_decision(
    account_id: str,
    body: DecisionCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_account_or_404(account_id, current_user)
    now = datetime.utcnow()
    decision = DBDecision(
        id=str(uuid.uuid4()),
        account_id=account_id,
        text=body.text,
        decided_by=body.decided_by or current_user,
        timestamp=now,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return Decision(
        id=decision.id,
        account_id=decision.account_id,
        text=decision.text,
        decided_by=decision.decided_by,
        timestamp=decision.timestamp,
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "ok"}


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
