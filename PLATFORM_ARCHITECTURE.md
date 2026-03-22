# Tenzing AI — Platform Architecture & Account Prioritisation Logic

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Account Prioritisation Logic](#2-account-prioritisation-logic)
   - 2.1 [Computed Signals](#21-computed-signals)
   - 2.2 [Risk Score](#22-risk-score)
   - 2.3 [Opportunity Score](#23-opportunity-score)
   - 2.4 [Health Score](#24-health-score)
   - 2.5 [Priority Assignment](#25-priority-assignment)
   - 2.6 [Portfolio Sort Order](#26-portfolio-sort-order)
3. [AI Layer](#3-ai-layer)
4. [System Architecture](#4-system-architecture)
5. [Key Architecture Decisions](#5-key-architecture-decisions)
6. [Data Flow](#6-data-flow)
7. [Security](#7-security)

---

## 1. Platform Overview

Tenzing AI is a B2B SaaS account intelligence platform built for private equity portfolio management. It ingests raw account data (commercial, health, support, lead, and qualitative signals) across a portfolio of 60 accounts and surfaces a ranked, prioritised view of where CSM and sales teams should focus their attention.

The platform operates on two layers:

- **Deterministic layer** — transparent, fully auditable scoring rules that run in milliseconds and produce consistent results regardless of AI availability.
- **AI layer** — Claude-powered analysis that provides narrative reasoning, contextualises signals against qualitative notes, and generates recommended actions. This layer is lazy-loaded and cached; it supplements but never replaces the deterministic scores.

**Tech stack:**

| Layer | Technology |
|---|---|
| Backend API | Python 3.11, FastAPI |
| Scoring engine | Pure Python (no ML dependencies) |
| AI | Anthropic Claude (claude-sonnet-4-20250514) |
| Database | PostgreSQL (decisions + AI cache) |
| ORM | SQLAlchemy 2.x + Alembic migrations |
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS with custom Tenzing palette |
| HTTP client | Axios with request/response interceptors |
| Auth | JWT (HS256), bcrypt password hashing |
| Rate limiting | SlowAPI (5 login attempts/minute) |
| Deployment | Backend on Render, frontend on Vercel |

---

## 2. Account Prioritisation Logic

All scoring lives in `backend/scoring.py`. Weights are explicit named constants at the top of the file — any weight can be changed without touching the scoring logic or re-calibrating other weights.

### 2.1 Computed Signals

Three fields are derived from raw CSV data before any scoring takes place (`backend/data_loader.py`):

| Signal | Formula | Purpose |
|---|---|---|
| `mrr_trend` | `(mrr_current - mrr_3m_ago) / mrr_3m_ago` | Percentage MRR change over 90 days |
| `seat_utilisation` | `seats_used / seats_purchased` | Adoption proxy; both high and low extremes are signals |
| `days_to_renewal` | `(renewal_date - today).days` | Renewal proximity pressure |

A **confidence score** is also computed per account based on how many of the 20 key signal fields are populated. Accounts with sparse data surface a "Low confidence" indicator in the UI so users treat scores with appropriate scepticism.

---

### 2.2 Risk Score

The risk score reflects the probability and severity of churn or contraction. It aggregates 15 binary/threshold signals into a raw sum, then passes that sum through a sigmoid function to produce a 0–100 score.

**Signals and weights:**

| Signal | Threshold | Weight |
|---|---|---|
| NPS very low | NPS < 0 | 20 |
| NPS low | NPS 0–30 | 10 |
| SLA breaches high | ≥ 3 breaches in 90 days | 18 |
| SLA breaches moderate | ≥ 1 breach in 90 days | 9 |
| Contraction risk high | > 30% of ARR | 20 |
| Contraction risk moderate | > 10% of ARR | 12 |
| MRR decline severe | mrr_trend < −10% | 20 |
| MRR decline moderate | mrr_trend < −5% | 10 |
| Negative sentiment | note_sentiment_hint = Negative | 15 |
| Urgent tickets high | ≥ 3 urgent open tickets | 15 |
| Urgent tickets moderate | ≥ 1 urgent open ticket | 8 |
| Low seat utilisation | seat_utilisation < 50% | 10 |
| Near renewal | 0 ≤ days_to_renewal < 60 | 8 |
| Low CSAT | avg_csat_90d < 3.0 | 10 |
| Overdue invoice | overdue_amount_gbp > 0 | 12 |
| Usage decline | usage_score fell > 10 pts | 10 |

**Sigmoid normalisation:**

```
risk_score = 100 / (1 + exp(-(raw - 45) / 18))
```

Calibration reference points:
- Raw ≈ 45 (3 moderate signals firing) → score ≈ 50
- Raw ≈ 90 (5–6 severe signals firing) → score ≈ 88
- Raw ≈ 0 (no signals) → score ≈ 8

---

### 2.3 Opportunity Score

The opportunity score reflects potential for expansion, upsell, or meaningful account development. It uses the same sigmoid approach as risk, with 11 signals.

**Signals and weights:**

| Signal | Threshold | Weight |
|---|---|---|
| Expansion pipeline high | > 20% of ARR | 25 |
| Expansion pipeline moderate | > 10% of ARR | 15 |
| Positive sentiment | note_sentiment_hint = Positive | 15 |
| Lead score high | avg_lead_score > 70 | 15 |
| Lead score moderate | avg_lead_score > 50 | 8 |
| MRR growth | mrr_trend > 5% | 15 |
| High seat utilisation | seat_utilisation > 85% | 12 |
| Expansion lifecycle stage | lifecycle_stage = Expansion | 15 |
| Open leads present | open_leads_count ≥ 2 | 10 |
| High CSAT | avg_csat_90d ≥ 4.5 | 8 |
| Usage growth | usage_score improved > 5 pts | 8 |

**Sigmoid normalisation:**

```
opportunity_score = 100 / (1 + exp(-(raw - 35) / 18))
```

Calibration reference points:
- Raw ≈ 40 (strong pipeline + positive sentiment) → score ≈ 55
- Raw ≈ 70 (4 strong signals firing) → score ≈ 83

---

### 2.4 Health Score

Health uses a different pattern: a baseline of 50 with additive and subtractive modifiers. This models the intuition that health is a neutral steady-state that customer experience pushes up or down, rather than an accumulation of independent risks.

**Baseline:** 50

**Modifiers:**

| Dimension | Condition | Modifier |
|---|---|---|
| CSAT | ≥ 4.5 | +20 |
| CSAT | ≥ 4.0 | +10 |
| CSAT | < 3.0 | −15 |
| NPS | ≥ 50 | +15 |
| NPS | 0–49 | +8 |
| NPS | −20 to −1 | −10 |
| NPS | < −20 | −20 |
| Usage | improved > 3 pts | +10 |
| Usage | declined > 3 pts | −10 |
| Open tickets | 0 | +8 |
| Open tickets | ≥ 5 | −12 |
| SLA breaches | 0 | +8 |
| SLA breaches | ≥ 3 | −15 |
| MRR trend | > 5% | +10 |
| MRR trend | within ±5% | +8 |
| MRR trend | < −10% | −15 |
| Sentiment | Positive | +8 |
| Sentiment | Negative | −12 |

The result is clamped to [0, 100]. A perfectly healthy account with all positive signals can reach a theoretical maximum of 50 + 20 + 15 + 10 + 8 + 8 + 10 + 8 + 8 = 137, clamped to 100. This means the ceiling is realistically achievable, unlike a sigmoid score.

---

### 2.5 Priority Assignment

Priority is assigned by explicit rule, requiring at least two specific signals per tier. This makes every priority decision auditable and reproducible without any probabilistic inference.

```
PAUSED   → account_status = "Paused" (excluded from active scoring)

CRITICAL → (days_to_renewal < 60  AND risk_score > 70)
         OR contraction_risk_gbp > £50,000
         OR (sentiment = Negative AND urgent_open_tickets > 2)

HIGH     → risk_score > 50
         OR (days_to_renewal < 90 AND health_score < 50)
         OR (sla_breaches ≥ 3 AND NPS < 0)

MEDIUM   → risk_score > 25
         OR opportunity_score > 40

LOW      → no material risk or opportunity signal
```

Note that opportunity is only a trigger for Medium, not for High or Critical. An account can only be escalated above Medium on the basis of risk signals. This prevents revenue growth from masking an underlying retention problem.

---

### 2.6 Portfolio Sort Order

The account list is sorted by a three-key comparator:

1. **Priority tier** (Critical → High → Medium → Low → Paused)
2. **Risk score descending** (within the same tier, highest risk first)
3. **ARR descending** (within the same risk score, largest account first)

This ensures that a CSM opening the portfolio always sees the most urgent account at the top, and that within the same urgency level, higher-value accounts are surfaced before lower-value ones.

---

## 3. AI Layer

The AI layer uses Claude Sonnet to provide two types of analysis.

### Per-account analysis

Triggered on demand from the account detail page (or on first load if no cached result exists). The backend sends Claude a structured JSON payload containing all account signals (excluding any previous AI output) with a system prompt that explicitly instructs it to:

- Cite specific numbers from the data, never hallucinate figures
- State "insufficient qualitative data" if account notes are absent
- Return a structured JSON object matching the `AIAnalysis` schema

The response includes:
- An AI-assigned priority (which may agree or disagree with the deterministic priority)
- A narrative reasoning paragraph
- Top 3 risks with severity ratings
- Top 3 opportunities with potential value
- 3 recommended actions with suggested owners (CSM / Sales / Leadership)

Results are cached in PostgreSQL (`ai_analysis_cache` table). Users can force a refresh, which re-runs the Claude call and overwrites the cache.

If the Claude call fails or returns malformed JSON, the system falls back to the deterministic priority and logs the error — the UI never shows a broken state.

### Portfolio leadership briefing

Available from the Briefing page. The backend sends Claude a portfolio-level payload containing:
- KPIs (total ARR, at-risk accounts, expansion opportunities, average health)
- The top 8 accounts by risk score
- All Critical and High priority accounts

Claude returns:
- A 2-sentence executive summary
- 3–4 cross-cutting portfolio themes
- Top 3 accounts for leadership attention
- Top 3 expansion opportunities
- 3 portfolio-level recommended actions

This briefing is also cached in PostgreSQL and regenerated on demand.

**Model parameters:** claude-sonnet-4-20250514, max 1,500 tokens per account analysis, 2,000 tokens for portfolio briefing.

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Vercel (CDN)                      │
│                React + TypeScript SPA                │
│                                                      │
│  /login        → Login page                         │
│  /             → Portfolio dashboard                 │
│  /accounts/:id → Account detail                     │
│  /briefing     → Leadership briefing                 │
└────────────────────────┬────────────────────────────┘
                         │ HTTPS + JWT Bearer
                         ▼
┌─────────────────────────────────────────────────────┐
│                  Render (FastAPI)                    │
│                                                      │
│  POST /auth/login/json                               │
│  GET  /accounts                                      │
│  GET  /accounts/:id                                  │
│  GET  /accounts/:id/analysis                         │
│  POST /accounts/:id/decisions                        │
│  GET  /portfolio/summary                             │
│  GET  /filters/options                               │
└──────┬──────────────────────────┬───────────────────┘
       │                          │
       ▼                          ▼
┌─────────────┐          ┌────────────────────┐
│  In-memory  │          │    PostgreSQL       │
│  account    │          │                    │
│  list       │          │  decisions         │
│  (60 rows,  │          │  ai_analysis_cache │
│  enriched   │          │  portfolio_briefing │
│  at startup)│          │  _cache            │
└─────────────┘          └────────────────────┘
                                  │
                         (on /analysis endpoint)
                                  ▼
                         ┌────────────────────┐
                         │  Anthropic API     │
                         │  Claude Sonnet     │
                         └────────────────────┘
```

### Startup sequence

On server startup, the backend:
1. Loads the CSV from disk (`data_loader.py`)
2. Runs safe type coercion on every field
3. Computes derived signals (mrr_trend, seat_utilisation, days_to_renewal, confidence)
4. Runs the full scoring and priority pipeline over all 60 accounts
5. Stores the enriched list in memory

All subsequent API requests read from this in-memory list. There is no per-request database read for account data — only for decisions and AI cache lookups.

---

## 5. Key Architecture Decisions

### Deterministic scoring first, AI second

**Decision:** AI analysis is opt-in and layered on top of deterministic scores, not a replacement for them.

**Rationale:** Deterministic scores are instantaneous, free, consistent, and fully explainable. A CSM can look at a risk score of 78 and trace it exactly to "NPS −12, 4 SLA breaches, negative sentiment, near renewal." AI analysis is valuable for narrative context and recommendations, but it costs money, takes seconds, and can occasionally produce unexpected output. Keeping them separate means the core workflow is never blocked by AI latency or API failures.

### Sigmoid normalisation over linear scaling

**Decision:** Risk and opportunity scores are normalised through a sigmoid function rather than capped at 100 or scaled linearly.

**Rationale:** With linear scaling or a hard cap, accounts with many simultaneous signals all cluster at the ceiling, making discrimination between "bad" and "catastrophic" impossible. The sigmoid spreads scores across the full range — a truly terrible account approaches 100 but never reaches it, preserving the ability to rank within a tier. Weights still express relative importance correctly because they operate in raw-score space before normalisation.

### Health uses baseline + modifiers, not sigmoid

**Decision:** Health is computed as 50 + modifiers and clamped, while risk and opportunity use sigmoid normalisation.

**Rationale:** Health models a different concept. Risk and opportunity are accumulations of independent signals — more signals means more risk/opportunity. Health is a steady-state: a neutral account with no strong signals should score around 50. The baseline + modifier pattern captures this naturally, whereas sigmoid would require an arbitrary mid-point that fights the intuition.

### Priority by explicit rule, not score threshold alone

**Decision:** Priority tiers are assigned by named conditions (e.g. "contraction > £50k" or "negative sentiment AND urgent tickets > 2") rather than purely by score ranges.

**Rationale:** Score thresholds are opaque to users and hard to explain in a customer conversation. Named conditions let a CSM say "this account is Critical because it has £60k at risk from contraction" — a reason that makes sense to a sales VP or portfolio manager. The rules also encode domain knowledge that a score alone cannot: a renewal in 45 days with high risk is categorically different from a renewal in 200 days with the same risk score.

### In-memory account store

**Decision:** The 60 enriched accounts are held in memory on the FastAPI process, not fetched from a database on each request.

**Rationale:** The dataset is small (60 rows), fully static between deploys, and needs to be sorted and filtered on every list request. An in-memory store gives sub-millisecond read performance and zero database connection overhead for the hot path. PostgreSQL is reserved for mutable data only: decisions recorded by users, and AI analysis cache. The trade-off — losing in-memory state on a server restart — is acceptable because scores are deterministic and can be recomputed instantly on next startup.

### Lazy AI analysis with PostgreSQL caching

**Decision:** AI analysis is not computed at startup or on account list load. It is triggered per account on demand, then cached indefinitely until manually refreshed.

**Rationale:** Running Claude on all 60 accounts at startup would take ~2 minutes, cost meaningful API credits on every deploy, and block the server startup. Lazy loading means the app is usable immediately. Caching means a CSM who opens the same account multiple times in a day doesn't trigger redundant API calls. The refresh button gives users control over when to spend a fresh API call.

### JWT in localStorage (not HttpOnly cookie)

**Decision:** The JWT is stored in `localStorage` and attached to requests via an Axios request interceptor.

**Rationale:** This is a single-tenant demo platform deployed on Vercel, not a public multi-user application. LocalStorage JWT is simpler to implement across a CORS boundary (backend on Render, frontend on Vercel) without requiring SameSite cookie configuration or CORS credential handling. For a production multi-tenant deployment, migrating to HttpOnly cookies with CSRF protection would be the correct step.

### Vite proxy in development, `VITE_API_URL` in production

**Decision:** The frontend uses a Vite dev-server proxy (`/api` → `localhost:8000`) in development and a `VITE_API_URL` environment variable in production.

**Rationale:** This avoids CORS issues during local development without requiring the backend to list `localhost:3000` as an allowed origin in production. The Axios client prefixes all calls with `VITE_API_URL` (defaulting to `/api`), so the same code works in both environments with no branching.

---

## 6. Data Flow

### Account list request

```
Browser → GET /accounts?region=UK&segment=Enterprise
        → Auth middleware validates JWT
        → Filter in-memory account list by query params
        → Return sorted AccountSummary list (JSON)
```

### Account detail + AI analysis

```
Browser → GET /accounts/:id
        → Return AccountDetail (deterministic scores, decisions from DB)

Browser → GET /accounts/:id/analysis
        → Check ai_analysis_cache in PostgreSQL
        → Cache hit: return cached AIAnalysis
        → Cache miss:
            → Build signal payload (all account fields, no prior AI data)
            → POST to Anthropic API
            → Parse JSON response
            → Store in ai_analysis_cache
            → Return AIAnalysis
```

### Decision recording

```
Browser → POST /accounts/:id/decisions  { text, decided_by }
        → Validate JWT
        → Insert DBDecision row into PostgreSQL
        → Return 201 with decision record
```

---

## 7. Security

| Concern | Implementation |
|---|---|
| Authentication | JWT (HS256), 8-hour expiry, bcrypt-hashed passwords |
| Rate limiting | 5 login attempts per minute per IP (SlowAPI) |
| CORS | Origins restricted to the deployed frontend URL in production |
| Security headers | X-Content-Type-Options, X-Frame-Options, Referrer-Policy on all responses |
| SQL injection | All database access via SQLAlchemy ORM with parameterised queries |
| Secret management | JWT secret, database URL, and Anthropic API key via environment variables — never in source |
| 401 handling | Frontend Axios interceptor clears token and redirects to `/login` on any 401 response |
