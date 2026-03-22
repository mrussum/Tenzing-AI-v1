# Tenzing AI — Account Prioritisation Tool

A full-stack B2B SaaS account intelligence platform built for private equity portfolio management. Surfaces which accounts need urgent attention, where revenue is at risk, and where growth opportunities exist — powered by deterministic scoring and Claude AI analysis.

---

## Architecture Overview

```
account-prioritisation/
├── backend/               # Python 3.11 + FastAPI
│   ├── main.py            # FastAPI app, REST endpoints
│   ├── data_loader.py     # CSV parsing + feature engineering
│   ├── scoring.py         # Deterministic risk/opportunity/health scoring
│   ├── ai_service.py      # Anthropic Claude integration
│   ├── auth.py            # JWT authentication
│   ├── models.py          # Pydantic models
│   └── requirements.txt
├── frontend/              # React 18 + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── pages/         # Login, Portfolio, AccountDetail, Briefing
│   │   ├── components/    # Reusable UI components
│   │   └── api/           # Typed API client (axios + react-query)
│   └── package.json
└── data/
    └── account_prioritisation_challenge_data.csv
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key (for AI features — app works without it but AI panels will be disabled)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set your API key
cp .env.example .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

uvicorn main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install

# Point at the backend
cp .env.example .env
# .env: VITE_API_URL=http://localhost:8000

npm run dev
# Runs at http://localhost:3000
```

### Demo credentials

| Field    | Value        |
|----------|-------------|
| Username | `admin`      |
| Password | `tenzing2026`|

---

## Scoring Design

All scores are **0–100**. Weights are defined as named constants in `backend/scoring.py` and are easily tuneable.

### Risk Score (churn/contraction signals)

| Signal | Weight (pts) |
|--------|-------------|
| NPS < 0 | 20 |
| NPS 0–30 | 10 |
| SLA breaches ≥ 3 in 90d | 18 |
| SLA breaches ≥ 1 in 90d | 9 |
| Contraction risk > 30% ARR | 20 |
| Contraction risk > 10% ARR | 12 |
| MRR trend < −10% | 20 |
| MRR trend < −5% | 10 |
| Sentiment = Negative | 15 |
| Urgent open tickets ≥ 3 | 15 |
| Urgent open tickets ≥ 1 | 8 |
| Seat utilisation < 50% | 10 |
| Days to renewal < 60 | 8 |
| Avg CSAT < 3.0 | 10 |
| Overdue invoice present | 12 |
| Usage score declined > 10pts | 10 |

### Opportunity Score (expansion signals)

| Signal | Weight (pts) |
|--------|-------------|
| Expansion pipeline > 20% ARR | 25 |
| Expansion pipeline > 10% ARR | 15 |
| Sentiment = Positive | 15 |
| Avg lead score > 70 | 15 |
| Avg lead score > 50 | 8 |
| MRR trend > +5% | 15 |
| Seat utilisation > 85% (capacity signal) | 12 |
| Lifecycle stage = Expansion | 15 |
| Open leads ≥ 2 | 10 |
| Avg CSAT ≥ 4.5 | 8 |
| Usage score improved > 5pts | 8 |

### Health Score (overall account wellbeing)

Starts at baseline 50, adjusted up/down by signal modifiers. Key factors: CSAT, NPS, usage trend, support volume, SLA performance, MRR stability, sentiment.

### Priority Assignment Rules

```
CRITICAL:  (days_to_renewal < 60 AND risk_score > 70)
           OR (contraction_risk_gbp > £50,000)
           OR (sentiment = Negative AND urgent_tickets > 2)

HIGH:      risk_score > 50
           OR (days_to_renewal < 90 AND health_score < 50)
           OR (sla_breaches >= 3 AND NPS < 0)

MEDIUM:    risk_score > 25
           OR opportunity_score > 40

LOW:       everything else (healthy, stable, no near-term risk)

PAUSED:    account_status = "Paused" — excluded from active scoring
```

Every priority decision cites ≥ 2 specific data points. Paused accounts are segregated and not scored against active accounts.

---

## AI Integration

Powered by `claude-sonnet-4-20250514` via the Anthropic SDK.

### Per-Account Analysis

Each account detail page has a lazy-loaded AI panel. On request, sends Claude a structured JSON context block containing all account signals and notes. Returns:

- **Priority label** — Critical / High / Medium / Low
- **Priority reasoning** — 2–3 sentences citing specific data points
- **Top risks** — up to 3, each with label + evidence
- **Top opportunities** — up to 3, each with label + evidence
- **Recommended actions** — exactly 3, each with concrete ask + owner (CSM / Sales / Leadership)
- **Confidence** — reflects actual data completeness

Prompt design explicitly instructs Claude to:
- Cite specific numbers, never invent data
- State "insufficient qualitative data" when notes are absent
- Return only valid JSON (no markdown wrapper)

### Portfolio Leadership Briefing

Generates a cross-account narrative identifying:
1. Executive summary (2 sentences)
2. 3–4 cross-cutting themes with named accounts and data
3. Top 3 accounts requiring immediate leadership attention
4. Top 3 expansion opportunities with pipeline figures
5. 3 portfolio-level recommended actions

Briefing is cached in memory — regenerated only on explicit request.

---

## Data Quality Handling

- Accounts with > 6 null signal fields → `confidence = "Low"`
- Accounts with > 3 null signal fields → `confidence = "Medium"`
- Confidence indicator shown on every account card and detail page
- Where qualitative notes are absent, the AI is explicitly instructed to state "insufficient qualitative data" — not to hallucinate sentiment
- Paused accounts are excluded from active prioritisation calculations

---

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/auth/login` | OAuth2 form login |
| `POST` | `/auth/login/json` | JSON body login |
| `GET` | `/accounts` | List all accounts (sorted by priority). Filter: `region`, `segment`, `lifecycle_stage`, `owner` |
| `GET` | `/accounts/{id}` | Full account detail (structured signals + recorded decisions) |
| `GET` | `/accounts/{id}/analysis` | AI analysis for a single account (cached). Pass `?refresh=true` to force a new Claude call |
| `GET` | `/portfolio/summary` | KPIs. Pass `?with_ai=true` for leadership briefing |
| `POST` | `/accounts/{id}/decisions` | Record a decision on an account |
| `GET` | `/filters/options` | Distinct values for filter dropdowns |
| `GET` | `/health` | Health check |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, pandas, python-jose (JWT), passlib (bcrypt) |
| AI | Anthropic SDK — `claude-sonnet-4-20250514` |
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| Data fetching | TanStack React Query v5 |
| Routing | React Router v6 |
| Charts | Recharts (MRR trend indicators) |
| HTTP client | Axios |
| Storage | In-memory (no database required) |

---

## Deployment

### Render (backend)

1. Connect repo → New Web Service
2. Build: `pip install -r backend/requirements.txt`
3. Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Env var: `ANTHROPIC_API_KEY`

### Vercel (frontend)

1. Connect repo → New Project → `frontend` directory
2. Build: `npm run build`
3. Output: `dist`
4. Env var: `VITE_API_URL=https://your-backend.onrender.com`

### Single-process (static serving via FastAPI)

Build the frontend (`npm run build`), copy `dist/` into `backend/static/`, then add a `StaticFiles` mount and SPA catch-all route to `main.py`.
