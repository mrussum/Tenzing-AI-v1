# Due Diligence Checklist
## Tenzing AI — Account Prioritisation Tool

Mapped against `account_prioritisation_challenge_instructions.pdf`.
Each requirement cites the exact file(s) and component(s) that satisfy it.

---

## 1. Minimum Requirements

| # | Requirement | Status | How & Where |
|---|---|---|---|
| 1.1 | **Include authentication** | ✅ Met | JWT-based auth. `backend/auth.py` — `authenticate_user`, `create_access_token`, `get_current_user`. Login page at `frontend/src/pages/Login.tsx`. Every API endpoint is protected via `Depends(get_current_user)`. Credentials: `admin / tenzing2026`. |
| 1.2 | **Use the provided dataset** | ✅ Met | `data/account_prioritisation_challenge_data.csv` is the sole data source. Loaded and parsed in `backend/data_loader.py`. No synthetic data is injected — all 60 records come from the CSV. |
| 1.3 | **Integrate an AI API** | ✅ Met | Anthropic Claude Sonnet 4 (`claude-sonnet-4-20250514`) via the official Python SDK. Per-account analysis in `backend/ai_service.py → analyse_account()`. Portfolio briefing in `ai_service.py → generate_portfolio_briefing()`. Model constant defined at line 16 of `ai_service.py`. |
| 1.4 | **Tackle the prioritisation of accounts directly** | ✅ Met | Four-tier priority (Critical / High / Medium / Low / Paused) assigned deterministically per account. Rules in `backend/scoring.py → assign_priority()`. Accounts sorted by priority → risk score → ARR in `scoring.py → sort_accounts()`. Priority is the primary organising principle of the entire UI. |

---

## 2. Example User Flow

| # | Step | Status | How & Where |
|---|---|---|---|
| 2.1 | **Sign in** | ✅ Met | `frontend/src/pages/Login.tsx` — username/password form POSTs to `POST /auth/login/json`. JWT stored in `localStorage`. Axios interceptor auto-attaches token to every request; 401 responses redirect back to `/login`. |
| 2.2 | **View a portfolio overview** | ✅ Met | `frontend/src/pages/Portfolio.tsx` — KPI row (total ARR, accounts at risk, expansion opportunities, avg health score) sourced from `GET /portfolio/summary`. Priority distribution bar chart via `PriorityChart.tsx` (Recharts). |
| 2.3 | **See prioritised accounts** | ✅ Met | Portfolio table in `Portfolio.tsx` — all 60 accounts sorted Critical → High → Medium → Low. Each row shows priority badge, ARR, days to renewal, MRR trend, risk/opportunity/health score bars, sentiment chip, confidence pill. Filter by region, segment, lifecycle stage, owner. Free-text search. |
| 2.4 | **Drill into an account** | ✅ Met | `frontend/src/pages/AccountDetail.tsx` — full account detail page. Commercial card (ARR, MRR, renewal, billing, expansion/contraction, overdue), MRR comparison chart, health card (seats, utilisation, usage score, NPS, CSAT), support card (tickets, SLA breaches), leads card, notes card. |
| 2.5 | **View reasoning and supporting evidence** | ✅ Met | `frontend/src/components/AIPanel.tsx` — `priority_reasoning` field is 2-3 sentences citing specific data points. `top_risks` array: each risk has a label + evidence sentence. `top_opportunities` array: same structure. All evidence is grounded in data from the CSV — Claude is explicitly instructed not to invent data (`ai_service.py` lines 36-38, 53-54). |
| 2.6 | **See recommended next actions** | ✅ Met | `AIPanel.tsx` renders `recommended_actions` — exactly 3 per account. Each action is concrete (names the signal, the ask, and timing) and labelled with an owner: CSM, Sales, or Leadership. Owner displayed as a colour-coded pill. |
| 2.7 | **Save or record decisions** | ✅ Met | `frontend/src/components/DecisionRecorder.tsx` — decision entry form on every account detail page. POSTs to `POST /accounts/{id}/decisions`. Returns a `Decision` object (id, account_id, text, decided_by, timestamp). Decisions are persisted in-memory (`_decisions` dict in `main.py`) and returned with each account detail response. |

---

## 3. Evaluation Criteria

| # | Criterion | Status | How & Where |
|---|---|---|---|
| 3.1 | **Clarity and defensibility of prioritisation logic** | ✅ Met | Every priority decision cites ≥ 2 explicit signals. Rules are deterministic and readable prose in `scoring.py → assign_priority()`. Priority tiers are documented in `README.md` (lines 125–142) and explained in depth in `SUBMISSION.md` (Section 2). Weights are named constants at the top of `scoring.py`, not magic numbers. |
| 3.2 | **Quality of AI integration and whether it improves decisions** | ✅ Met | AI is additive, not a replacement for deterministic scoring. Claude receives all account signals plus the deterministic priority as context, then synthesises qualitative notes with quantitative signals — something a formula cannot do. Per-account analysis (`/accounts/{id}/analysis`) is cached server-side (`_ai_cache` in `main.py`). Portfolio briefing identifies cross-account patterns. Explained in `SUBMISSION.md` Section 3. |
| 3.3 | **Architecture decisions** | ✅ Met | Covered in `SUBMISSION.md` Section 1: deterministic/AI separation, lazy AI loading, in-memory state as a deliberate choice, single CSV as source of truth, dedicated `/analysis` endpoint design. `render.yaml` version-controls deployment config. `frontend/vercel.json` handles SPA routing. |
| 3.4 | **Handling of imperfect operational data** | ✅ Met | Three-tier confidence scoring (High / Medium / Low) based on null field count per account — `backend/data_loader.py → _confidence()`. Displayed as a pill on every account card and detail page via `ConfidencePill.tsx`. Claude is explicitly instructed: "state 'insufficient qualitative data' — do not invent sentiment" (`ai_service.py` line 53). Accounts with all three note fields null trigger an additional prompt qualifier (lines 72-76). Paused accounts excluded from active scoring distribution. |
| 3.5 | **Quality of reasoning explanations** | ✅ Met | Prompt engineering in `ai_service.py` `ACCOUNT_USER_TEMPLATE` (lines 40-56): priority_reasoning must cite ≥ 2 specific data points; each risk/opportunity must include evidence; actions must "name the signal, the ask, and why now". System prompt instructs Claude to "always cite specific numbers" and "never hallucinate data points". |
| 3.6 | **UX clarity for leadership use** | ✅ Met | Colour-coded priority badges, score bars (risk = red gradient, opportunity = blue, health = green), MRR trend arrow chips, sentiment chips, confidence pills. Portfolio KPIs at a glance. `PriorityChart.tsx` gives instant visual distribution. MRR comparison chart (`MRRChart.tsx`) on account detail. Table has sticky headers, row highlighting for Critical accounts, renewal date colour coding (red < 60d, amber < 90d). |
| 3.7 | **Trade-offs and overall system thinking** | ✅ Met | `SUBMISSION.md` Section 4: trade-off table covering 7 explicit decisions (in-memory state, lazy AI, sigmoid normalisation, deterministic rules, 2-point MRR trend, briefing cache, no notifications). Section 5: "What I Would Build Next" with 7 items ordered by business impact. |

---

## 4. Not Being Evaluated (confirming we haven't over-invested)

| # | Item | Our approach |
|---|---|---|
| 4.1 | **Pixel-perfect design** | Tailwind CSS with a clean, functional design system. No custom CSS animations, no bespoke illustration work, no design system beyond what Tailwind provides. |
| 4.2 | **Extensive data cleaning** | `data_loader.py` does lightweight type coercion and null handling in a single pass. No imputation, no outlier removal, no normalisation pipeline. |
| 4.3 | **Production-hardening beyond reasonable scope** | In-memory state (no DB), single hardcoded user, `allow_origins=["*"]` CORS, no rate limiting, no audit logging. These are documented trade-offs, not oversights. |

---

## 5. Submission Requirements

| # | Requirement | Status | Notes |
|---|---|---|---|
| 5.1 | **Link to a working prototype** | ⏳ Pending | Requires deployment to Render + Vercel. Full instructions in `DEPLOY_GUIDE.md`. Once deployed, URL will be your Vercel domain (e.g. `https://tenzing-ai-v1.vercel.app`). |
| 5.2 | **Repository** | ✅ Ready | Pushed to GitHub on branch `claude/account-prioritization-tool-J6H74`. Includes all source code, `render.yaml`, `runtime.txt`, `vercel.json`, `.env.example` files. |
| 5.3 | **Short write-up — architecture decisions** | ✅ Met | `SUBMISSION.md` Section 1 — covers deterministic/AI separation, in-memory state choice, single CSV source of truth, lazy AI endpoint design. |
| 5.3 | **Short write-up — how prioritisation works** | ✅ Met | `SUBMISSION.md` Section 2 — three composite scores, sigmoid normalisation, explicit priority tier rules with thresholds, confidence scoring. |
| 5.3 | **Short write-up — how AI improves the workflow** | ✅ Met | `SUBMISSION.md` Section 3 — qualitative synthesis, action specificity, cross-account pattern detection, what AI does not do. |
| 5.3 | **Short write-up — trade-offs** | ✅ Met | `SUBMISSION.md` Section 4 — 7-row trade-off table, each decision explained. |
| 5.3 | **Short write-up — what you would build next** | ✅ Met | `SUBMISSION.md` Section 5 — 7 items ordered by business impact: push alerts, persistence, score trend tracking, bulk AI pre-warming, data validation, feedback loop, RBAC. |

---

## 6. Dataset Requirements

| # | Requirement | Status | How & Where |
|---|---|---|---|
| 6.1 | **60 synthetic account records used** | ✅ Met | `data_loader.py` loads all rows from `data/account_prioritisation_challenge_data.csv`. Health check at `GET /health` reports `accounts_loaded: 60`. |
| 6.2 | **Signals from accounts, leads, support, revenue, notes** | ✅ Met | All five signal domains consumed: account metadata (segment, region, lifecycle), lead signals (open_leads_count, avg_lead_score, last_lead_activity_date), support (open_tickets_count, urgent_open_tickets_count, sla_breaches_90d), revenue (arr_gbp, mrr_current/3m_ago, expansion_pipeline, contraction_risk, overdue_amount), notes (recent_support_summary, recent_customer_note, recent_sales_note, note_sentiment_hint). |
| 6.3 | **May derive features** | ✅ Met | `data_loader.py` derives: `mrr_trend` (% change), `seat_utilisation` (seats_used / seats_purchased), `days_to_renewal` (from renewal_date), `null_field_count` (across 19 key signal fields). |
| 6.4 | **Source data remains the basis** | ✅ Met | No synthetic enrichment, no external API calls for data. All scoring is derived from the CSV fields or features derived from them. |
| 6.5 | **Nulls and mixed-signal accounts handled** | ✅ Met | Null-safe throughout `scoring.py` (`acc.get(field) or 0` / `if field is not None`). Confidence indicator surfaces data quality to the user. AI prompt explicitly handles the all-nulls-notes case. |

---

## 7. One Outstanding Item

| Item | Action needed |
|---|---|
| **README.md API table** (line 196) still references `?with_ai=true` on `GET /accounts/{id}` | Minor inconsistency — this endpoint no longer returns AI data; that's now `GET /accounts/{id}/analysis`. Does not affect the app (frontend doesn't use this), but worth updating before sharing the repo. |

---

*Last updated: 2026-03-20. All code items verified against the current state of branch `claude/account-prioritization-tool-J6H74`.*
