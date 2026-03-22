# Tenzing AI — Use Cases, Test Specification & Coverage Status

## Table of Contents

1. [Use Cases](#1-use-cases)
2. [Test Inventory & Coverage Status](#2-test-inventory--coverage-status)
   - 2.1 [Scoring Engine — Unit Tests](#21-scoring-engine--unit-tests)
   - 2.2 [Data Loader — Unit Tests](#22-data-loader--unit-tests)
   - 2.3 [API Endpoints — Integration Tests](#23-api-endpoints--integration-tests)
   - 2.4 [AI Service — Integration Tests](#24-ai-service--integration-tests)
   - 2.5 [Frontend — End-to-End Tests](#25-frontend--end-to-end-tests)
   - 2.6 [Manual Smoke Tests (Deployment Checklist)](#26-manual-smoke-tests-deployment-checklist)
3. [Coverage Summary](#3-coverage-summary)
4. [Recommended Test Setup](#4-recommended-test-setup)

---

## 1. Use Cases

### UC-01 — Portfolio Overview

**Actor:** CSM / Portfolio Manager
**Goal:** Get an instant, ranked view of all 60 accounts so they can decide where to spend their day.

**Flow:**
1. User logs in with credentials.
2. System loads the portfolio table sorted by priority tier, then risk score, then ARR.
3. User sees KPIs at the top (total ARR, accounts at risk, expansion opportunities, average health score).
4. User applies filters (region, segment, lifecycle stage, account owner) to narrow the list.
5. User uses the search box to find a specific account by name.

**Success criteria:**
- All 60 accounts are displayed on login.
- Sorting is always: Critical → High → Medium → Low → Paused; within a tier, highest risk first, then largest ARR.
- Filters are additive (AND logic) and update the list without a page reload.
- KPIs reflect the filtered view.

---

### UC-02 — Account Risk Triage

**Actor:** CSM
**Goal:** Understand which accounts are at highest risk of churn or contraction and why.

**Flow:**
1. User clicks an account from the portfolio table.
2. System displays all signals: commercial data, MRR trend chart, health metrics, support tickets, lead pipeline, and sentiment.
3. User reads the risk score (0–100) and sees which signals are driving it.
4. User clicks "Generate AI Analysis" to get a narrative explanation and recommended actions.

**Success criteria:**
- Risk score is deterministic: the same account data always produces the same score.
- All 15 risk signals are correctly detected and weighted.
- AI analysis cites specific numbers from the account data.
- AI analysis clearly states "insufficient qualitative data" when notes are absent.
- If the AI call fails, the deterministic score and priority are still shown.

---

### UC-03 — Expansion Opportunity Identification

**Actor:** Sales / Account Executive
**Goal:** Find accounts with strong upsell or expansion signals to prioritise outreach.

**Flow:**
1. User sorts or filters the portfolio table by opportunity score.
2. User opens accounts with high opportunity scores.
3. User reviews expansion pipeline value, seat utilisation, MRR growth, and lead scores.
4. AI analysis surfaces top opportunities and suggests actions with an "owner" label (Sales/CSM/Leadership).

**Success criteria:**
- Opportunity scores correctly reflect all 11 signals.
- An account in the "Expansion" lifecycle stage receives the `W_OPP_EXPANSION_STAGE` weight.
- Opportunity score alone can elevate an account to Medium priority (but not to High or Critical).

---

### UC-04 — Renewal Risk Management

**Actor:** CSM / Revenue Operations
**Goal:** Identify accounts approaching renewal that are in poor health, so intervention can happen before the renewal date.

**Flow:**
1. System flags accounts where renewal is within 60 days AND risk score is above 70 as Critical priority.
2. System flags accounts where renewal is within 90 days AND health score is below 50 as High priority.
3. User can filter by renewal proximity and sees `days_to_renewal` on every account row.

**Success criteria:**
- Renewal proximity correctly escalates priority tier regardless of other signals.
- `days_to_renewal` is computed accurately from the renewal date field and today's date.

---

### UC-05 — Account Decision Recording

**Actor:** CSM / Account Executive
**Goal:** Log a decision or action taken on an account so the team has a shared record of what has been done.

**Flow:**
1. User opens an account detail page.
2. User types a decision in the Decision Recorder and optionally adds a "decided by" field.
3. User submits the form.
4. System saves the decision to the database and displays it immediately in the decision history.
5. Decision history persists across page reloads and sessions.

**Success criteria:**
- Decisions are persisted in PostgreSQL, not in memory.
- Decision history is ordered chronologically (newest first).
- The form resets after a successful submission.
- Submitting an empty decision is rejected (validated client-side or server-side).

---

### UC-06 — Leadership Briefing

**Actor:** Portfolio Director / Leadership
**Goal:** Get a concise, AI-generated executive summary of the portfolio to prepare for an investor or board meeting.

**Flow:**
1. User navigates to the Leadership Briefing page.
2. System displays portfolio KPIs and priority distribution chart.
3. User clicks "Generate AI Briefing".
4. System sends portfolio data to Claude and returns a structured narrative.
5. Briefing includes: 2-sentence executive summary, cross-cutting themes, top accounts needing attention, expansion opportunities, and recommended portfolio-level actions.

**Success criteria:**
- Briefing is cached: clicking "Generate" a second time returns the cached result immediately.
- Briefing is regeneratable on demand.
- KPI figures in the briefing match the values shown in the UI.

---

### UC-07 — Authentication & Access Control

**Actor:** Any user
**Goal:** Ensure only authenticated users can access account data.

**Flow:**
1. Unauthenticated users are redirected to `/login`.
2. User provides correct credentials and receives a JWT.
3. All subsequent API calls include the JWT in the Authorization header.
4. On 401 responses (expired or invalid token), the frontend clears the token and redirects to `/login`.
5. Repeated failed login attempts are rate-limited to 5 per minute.

**Success criteria:**
- All protected endpoints return 401 when called without a token.
- Rate limiting returns 429 after 5 failed login attempts per minute.
- JWT expires after 8 hours.

---

### UC-08 — Data Quality Awareness

**Actor:** CSM / Analyst
**Goal:** Know when an account's scores may be unreliable due to incomplete data.

**Flow:**
1. System computes a confidence score for each account based on how many of the 20 key signal fields are populated.
2. UI displays a "Low / Medium / High" confidence pill on the account row and detail page.
3. AI analysis notes when it lacks qualitative data.

**Success criteria:**
- Accounts with ≤ 5 populated fields out of 20 show "Low" confidence.
- Confidence score is updated if the underlying data changes.

---

## 2. Test Inventory & Coverage Status

> **Current automated test coverage: 0%**
>
> The repository contains no test files, no test configuration, and no testing dependencies. All test cases below are specified as requirements. Each row records whether the test currently exists (`Implemented`) or not (`Not implemented`), and in the case of manual tests, whether they were last verified as passing (`Passing`) or not (`Not verified`).

---

### 2.1 Scoring Engine — Unit Tests

**Framework:** pytest + pytest-cov
**File to create:** `backend/tests/test_scoring.py`

| ID | Test Case | Use Case | Status |
|---|---|---|---|
| S-01 | Risk score for account with no signals returns ≈ 8 (sigmoid of 0 raw) | UC-02 | Not implemented |
| S-02 | NPS < 0 adds W_RISK_NPS_VERY_LOW (20) to raw risk score | UC-02 | Not implemented |
| S-03 | NPS 0–30 adds W_RISK_NPS_LOW (10), not the very_low weight | UC-02 | Not implemented |
| S-04 | NPS > 30 adds 0 to risk score | UC-02 | Not implemented |
| S-05 | SLA breaches ≥ 3 adds 18 (high tier, not 9) | UC-02 | Not implemented |
| S-06 | SLA breaches = 1 adds 9 (medium tier) | UC-02 | Not implemented |
| S-07 | Contraction > 30% ARR adds 20 | UC-02 | Not implemented |
| S-08 | Contraction 10–30% ARR adds 12 | UC-02 | Not implemented |
| S-09 | MRR trend < −10% adds 20 | UC-02 | Not implemented |
| S-10 | MRR trend between −10% and −5% adds 10 | UC-02 | Not implemented |
| S-11 | Negative sentiment adds 15 to raw risk | UC-02 | Not implemented |
| S-12 | Neutral and Positive sentiments add 0 to raw risk | UC-02 | Not implemented |
| S-13 | 3+ urgent tickets adds 15; 1–2 adds 8 | UC-02 | Not implemented |
| S-14 | Seat utilisation < 50% adds 10 to risk | UC-02 | Not implemented |
| S-15 | days_to_renewal = 30 adds 8 (near renewal); days = 90 adds 0 | UC-04 | Not implemented |
| S-16 | CSAT < 3.0 adds 10 to risk | UC-02 | Not implemented |
| S-17 | Overdue amount > 0 adds 12 | UC-02 | Not implemented |
| S-18 | Usage score fell > 10 pts adds 10 | UC-02 | Not implemented |
| S-19 | Account with 3 moderate signals returns risk_score ≈ 50 (±5) | UC-02 | Not implemented |
| S-20 | Account with 6 severe signals returns risk_score ≈ 88 (±5) | UC-02 | Not implemented |
| S-21 | Expansion pipeline > 20% ARR adds 25 to raw opportunity | UC-03 | Not implemented |
| S-22 | Expansion pipeline 10–20% ARR adds 15 | UC-03 | Not implemented |
| S-23 | Positive sentiment adds 15 to opportunity | UC-03 | Not implemented |
| S-24 | avg_lead_score > 70 adds 15; 50–70 adds 8 | UC-03 | Not implemented |
| S-25 | mrr_trend > 5% adds 15 to opportunity | UC-03 | Not implemented |
| S-26 | seat_utilisation > 85% adds 12 to opportunity | UC-03 | Not implemented |
| S-27 | lifecycle_stage = "Expansion" adds 15 | UC-03 | Not implemented |
| S-28 | open_leads_count ≥ 2 adds 10 | UC-03 | Not implemented |
| S-29 | Health baseline is 50 when all signals are absent | UC-02 | Not implemented |
| S-30 | CSAT ≥ 4.5 adds +20 to health | UC-02 | Not implemented |
| S-31 | CSAT < 3.0 adds −15 to health | UC-02 | Not implemented |
| S-32 | NPS ≥ 50 adds +15; NPS < −20 adds −20 | UC-02 | Not implemented |
| S-33 | Health score is clamped to [0, 100] | UC-02 | Not implemented |
| S-34 | Paused account_status always returns "Paused" priority regardless of scores | UC-01 | Not implemented |
| S-35 | days_to_renewal < 60 AND risk_score > 70 returns "Critical" | UC-04 | Not implemented |
| S-36 | contraction_risk_gbp > 50,000 returns "Critical" | UC-02 | Not implemented |
| S-37 | Negative sentiment AND urgent_open_tickets > 2 returns "Critical" | UC-02 | Not implemented |
| S-38 | risk_score > 50 returns "High" | UC-02 | Not implemented |
| S-39 | days_to_renewal < 90 AND health_score < 50 returns "High" | UC-04 | Not implemented |
| S-40 | sla_breaches ≥ 3 AND NPS < 0 returns "High" | UC-02 | Not implemented |
| S-41 | risk_score 25–50 (no critical/high triggers) returns "Medium" | UC-02 | Not implemented |
| S-42 | opportunity_score > 40 (no risk) returns "Medium" | UC-03 | Not implemented |
| S-43 | No material signals returns "Low" | UC-02 | Not implemented |
| S-44 | Sort order: Critical before High before Medium before Low before Paused | UC-01 | Not implemented |
| S-45 | Within same priority tier, higher risk_score sorts first | UC-01 | Not implemented |
| S-46 | Within same priority tier and risk score, higher ARR sorts first | UC-01 | Not implemented |
| S-47 | Score computation is deterministic: same input always produces same output | UC-02 | Not implemented |
| S-48 | None/null values for optional fields do not raise exceptions | UC-02 | Not implemented |

---

### 2.2 Data Loader — Unit Tests

**Framework:** pytest
**File to create:** `backend/tests/test_data_loader.py`

| ID | Test Case | Use Case | Status |
|---|---|---|---|
| DL-01 | mrr_trend = (current − 3m_ago) / 3m_ago computed correctly | UC-02 | Not implemented |
| DL-02 | mrr_trend is None when either MRR field is missing | UC-08 | Not implemented |
| DL-03 | seat_utilisation = seats_used / seats_purchased computed correctly | UC-02 | Not implemented |
| DL-04 | seat_utilisation is None when seats_purchased is 0 or missing | UC-08 | Not implemented |
| DL-05 | days_to_renewal is computed correctly from renewal_date and today | UC-04 | Not implemented |
| DL-06 | days_to_renewal is None when renewal_date is missing | UC-08 | Not implemented |
| DL-07 | Confidence score decreases as more key fields are null | UC-08 | Not implemented |
| DL-08 | Accounts with ≤ 5 populated fields out of 20 have confidence = "Low" | UC-08 | Not implemented |
| DL-09 | Non-numeric values in numeric fields are coerced to None, not 0 | UC-08 | Not implemented |
| DL-10 | All 60 accounts are loaded from the CSV | UC-01 | Not implemented |

---

### 2.3 API Endpoints — Integration Tests

**Framework:** pytest + FastAPI `TestClient` (httpx)
**File to create:** `backend/tests/test_api.py`

| ID | Endpoint | Test Case | Use Case | Status |
|---|---|---|---|---|
| A-01 | GET /health | Returns `{"status": "ok", "accounts_loaded": 60}` | UC-01 | Not implemented |
| A-02 | POST /auth/login/json | Valid credentials return 200 with `access_token` | UC-07 | Not implemented |
| A-03 | POST /auth/login/json | Invalid password returns 401 | UC-07 | Not implemented |
| A-04 | POST /auth/login/json | 6th attempt within 1 minute returns 429 | UC-07 | Not implemented |
| A-05 | GET /accounts | Without token returns 401 | UC-07 | Not implemented |
| A-06 | GET /accounts | With valid token returns list of 60 accounts | UC-01 | Not implemented |
| A-07 | GET /accounts | `?region=UK` filters to UK accounts only | UC-01 | Not implemented |
| A-08 | GET /accounts | `?segment=Enterprise` filters correctly | UC-01 | Not implemented |
| A-09 | GET /accounts | Multiple filters applied together (AND logic) | UC-01 | Not implemented |
| A-10 | GET /accounts | Response is sorted by priority tier, then risk_score desc | UC-01 | Not implemented |
| A-11 | GET /accounts/{id} | Known account ID returns AccountDetail with all score fields | UC-02 | Not implemented |
| A-12 | GET /accounts/{id} | Unknown account ID returns 404 | UC-02 | Not implemented |
| A-13 | GET /accounts/{id}/analysis | Returns AIAnalysis (may be cached or freshly generated) | UC-02 | Not implemented |
| A-14 | GET /accounts/{id}/analysis | `?refresh=true` triggers a new Claude call and overwrites cache | UC-02 | Not implemented |
| A-15 | GET /accounts/{id}/analysis | Returns 503 (not 500) when Anthropic API key is missing | UC-02 | Not implemented |
| A-16 | POST /accounts/{id}/decisions | Valid body persists decision and returns 201 | UC-05 | Not implemented |
| A-17 | POST /accounts/{id}/decisions | Empty text body returns 422 | UC-05 | Not implemented |
| A-18 | GET /portfolio/summary | Returns PortfolioSummary with correct KPI totals | UC-06 | Not implemented |
| A-19 | GET /filters/options | Returns distinct values for region, segment, lifecycle_stage, owner | UC-01 | Not implemented |

---

### 2.4 AI Service — Integration Tests

**Framework:** pytest + `unittest.mock` (mock the Anthropic client)
**File to create:** `backend/tests/test_ai_service.py`

| ID | Test Case | Use Case | Status |
|---|---|---|---|
| AI-01 | `analyse_account` returns valid AIAnalysis when Claude returns well-formed JSON | UC-02 | Not implemented |
| AI-02 | `analyse_account` handles JSON wrapped in markdown code fences (strips them correctly) | UC-02 | Not implemented |
| AI-03 | `analyse_account` falls back to deterministic priority when Claude returns malformed JSON | UC-02 | Not implemented |
| AI-04 | `analyse_account` falls back gracefully when Anthropic API raises an exception | UC-02 | Not implemented |
| AI-05 | `analyse_account` does not include previous AIAnalysis fields in the prompt payload | UC-02 | Not implemented |
| AI-06 | `generate_portfolio_briefing` returns a PortfolioBriefing with all required fields | UC-06 | Not implemented |
| AI-07 | `generate_portfolio_briefing` sends only top-8 risk accounts + critical/high accounts | UC-06 | Not implemented |
| AI-08 | Second call to `analyse_account` uses cache and does not call Anthropic | UC-02 | Not implemented |
| AI-09 | Cache is bypassed when `refresh=True` | UC-02 | Not implemented |

---

### 2.5 Frontend — End-to-End Tests

**Framework:** Playwright or Cypress
**File to create:** `frontend/e2e/` directory

| ID | Test Case | Use Case | Status |
|---|---|---|---|
| E-01 | Unauthenticated visit to `/` redirects to `/login` | UC-07 | Not implemented |
| E-02 | Login with `admin / tenzing2026` redirects to portfolio page | UC-07 | Not implemented |
| E-03 | Login with wrong password shows error message (does not redirect) | UC-07 | Not implemented |
| E-04 | Portfolio page displays 60 account rows | UC-01 | Not implemented |
| E-05 | KPI cards show non-zero values for Total ARR and Average Health | UC-01 | Not implemented |
| E-06 | At least one account shows "Critical" or "High" priority badge | UC-01 | Not implemented |
| E-07 | Region filter reduces the account count | UC-01 | Not implemented |
| E-08 | Search box filters accounts by name in real time | UC-01 | Not implemented |
| E-09 | Clicking an account row navigates to `/accounts/:id` | UC-02 | Not implemented |
| E-10 | Account detail page shows Risk, Opportunity, and Health score bars | UC-02 | Not implemented |
| E-11 | "Generate AI Analysis" button is present and clickable | UC-02 | Not implemented |
| E-12 | After clicking "Generate AI Analysis", AI panel populates with text | UC-02 | Not implemented |
| E-13 | Decision Recorder form submits and decision appears in history | UC-05 | Not implemented |
| E-14 | Leadership Briefing page loads KPIs and "Generate AI Briefing" button | UC-06 | Not implemented |
| E-15 | Clicking "Generate AI Briefing" renders a non-empty briefing text | UC-06 | Not implemented |
| E-16 | Logout clears the session and redirects to `/login` | UC-07 | Not implemented |
| E-17 | Direct navigation to `/accounts/unknown-id` shows a not-found or error state | UC-02 | Not implemented |

---

### 2.6 Manual Smoke Tests (Deployment Checklist)

These tests are performed manually after each deployment. They match the checklist in `DEPLOY_GUIDE.md`.

| ID | Test Case | Use Case | Status |
|---|---|---|---|
| M-01 | `GET /health` returns `{"status": "ok", "accounts_loaded": 60}` | UC-01 | **Passing** (verified in deploy guide) |
| M-02 | Login with `admin / tenzing2026` succeeds | UC-07 | **Passing** (verified in deploy guide) |
| M-03 | Portfolio table loads with 60 accounts | UC-01 | **Passing** (verified in deploy guide) |
| M-04 | Clicking any account and generating AI analysis returns a result | UC-02 | **Passing** (verified in deploy guide) |
| M-05 | Leadership Briefing page generates an AI briefing | UC-06 | **Passing** (verified in deploy guide) |
| M-06 | Backend URL is accessible and not returning 502/503 | UC-01 | Not verified (depends on Render service state) |
| M-07 | CORS: frontend can reach backend without browser console errors | UC-01 | Not verified (depends on deployment) |

---

## 3. Coverage Summary

| Category | Total Tests Specified | Implemented | Passing | Not implemented |
|---|---|---|---|---|
| Scoring engine (unit) | 48 | 0 | 0 | 48 |
| Data loader (unit) | 10 | 0 | 0 | 10 |
| API endpoints (integration) | 19 | 0 | 0 | 19 |
| AI service (integration) | 9 | 0 | 0 | 9 |
| Frontend E2E | 17 | 0 | 0 | 17 |
| Manual smoke tests | 7 | — | 5 | 2 |
| **Total** | **110** | **0** | **5** | **105** |

**Automated test coverage: 0%**
**Manual smoke test coverage: 5 / 7 verified passing**

---

## 4. Recommended Test Setup

### Backend

Install testing dependencies:

```
pytest==8.2.2
pytest-cov==5.0.0
httpx==0.27.0          # required by FastAPI TestClient
pytest-asyncio==0.23.7
respx==0.21.1          # mock HTTP calls to Anthropic API
```

Add to `requirements.txt` (or a separate `requirements-dev.txt`):

```
# Dev / testing only
pytest==8.2.2
pytest-cov==5.0.0
httpx==0.27.0
pytest-asyncio==0.23.7
respx==0.21.1
```

Run tests:

```bash
cd backend
pytest tests/ --cov=. --cov-report=term-missing
```

Example test structure:

```python
# backend/tests/test_scoring.py
from scoring import compute_risk_score, assign_priority

def test_no_signals_produces_low_risk():
    acc = {}
    score = compute_risk_score(acc)
    assert score < 20  # sigmoid of 0 raw ≈ 8

def test_critical_priority_on_high_contraction():
    acc = {"contraction_risk_gbp": 60_000, "arr_gbp": 100_000}
    from scoring import enrich_account
    result = enrich_account(acc)
    assert result["priority"] == "Critical"
```

### Frontend

Add Playwright as a dev dependency:

```bash
cd frontend
npm install --save-dev @playwright/test
npx playwright install
```

Add to `package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test:e2e": "playwright test"
  }
}
```

Create `frontend/e2e/portfolio.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test('login and portfolio load', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'tenzing2026');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/');
  const rows = await page.locator('tbody tr').count();
  expect(rows).toBe(60);
});
```

### Priority order for implementation

Given the platform is in production use, the highest-value tests to implement first are:

1. **S-34 through S-46** (priority assignment rules) — these are the decisions CSMs rely on daily; a regression here would cause wrong accounts to be escalated.
2. **S-01 through S-20** (risk score signal weights) — scoring correctness is the core value proposition.
3. **A-02, A-05, A-06, A-16** (auth and core endpoints) — minimum integration coverage for the API.
4. **E-01 through E-06** (login and portfolio load) — smoke-level E2E coverage for the critical path.
5. **DL-01 through DL-06** (derived signals) — mrr_trend and days_to_renewal feed directly into priority rules.
