# Submission Write-Up
## Tenzing AI — Account Prioritisation Tool

---

## 1. Architecture Decisions

### Separation of deterministic scoring and AI reasoning

The most important architectural decision was treating the scoring layer and the AI layer as two distinct, complementary systems rather than delegating everything to the LLM.

**Deterministic scoring** (Python, no API calls) runs at startup and produces three composite scores (risk, opportunity, health) and a priority label for every account. This layer is fast, free, auditable, and produces consistent results. It also means the portfolio table is always populated even if the Anthropic API key is absent or rate-limited.

**AI reasoning** (Claude Sonnet 4) is invoked lazily — only when a user explicitly requests analysis on an individual account, or triggers the leadership briefing. Claude's job is to synthesise the qualitative notes with the quantitative signals and produce defensible natural-language reasoning that a deterministic formula cannot generate. This is where it genuinely adds value: interpreting a CSM note in the context of an NPS of −23 and an upcoming renewal requires language understanding.

This split also controls cost. Sixty API calls per page load would be unacceptable in a production prototype; one per account on demand is fine.

### In-memory state as a deliberate choice

The brief specified "no database required." Rather than adding SQLite as a crutch, the prototype embraces in-memory state explicitly: the CSV is loaded and enriched once on startup, AI analyses are cached in a dict keyed by `account_id`, and decisions are stored in a list per account. The trade-off is that restarts clear the cache — acceptable for a prototype, and noted as a "build next" item.

### Single CSV as source of truth

No data transformation pipeline, no ETL layer. The CSV is parsed once by `data_loader.py` using pandas, and all feature engineering (MRR trend, seat utilisation, days to renewal, null field counting) happens in a single pass. This keeps the data lineage trivially auditable.

### API design — AI on demand, not on load

The account detail endpoint (`GET /accounts/{id}`) returns all structured signals immediately. A separate endpoint (`GET /accounts/{id}/analysis`) triggers the Claude call and caches the result. The frontend requests analysis only when the user clicks "Generate AI Analysis." This pattern means the app is fully usable and provides real signal value even in environments where the API key is unavailable or rate limits are hit.

---

## 2. How Prioritisation Works

### Three composite scores

Every account receives three scores, each on a 0–100 scale:

**Risk score** measures churn and contraction probability. Inputs include: NPS (weighted heavily because it is a leading indicator of churn), SLA breach frequency (operational signal of product or support failure), MRR trend (the actual financial signal), contraction risk as a proportion of ARR, sentiment from CSM/sales notes, urgent ticket count, seat utilisation below 50% (low stickiness), CSAT, overdue invoices, and usage score decline. Raw points are passed through a logistic sigmoid so the score remains spread across the full 0–100 range — an account needs multiple severe signals simultaneously to approach 90+.

**Opportunity score** measures expansion probability. Inputs include: expansion pipeline as a proportion of ARR (the most direct signal), positive sentiment, high lead scores, MRR growth momentum, seat utilisation above 85% (capacity pressure creates natural upsell conversations), lifecycle stage of Expansion, and usage score improvement.

**Health score** reflects overall account wellbeing. It uses a baseline of 50 with additive modifiers — positive signals raise it, negative signals lower it. CSAT and NPS are the primary drivers because they directly measure customer satisfaction. MRR stability, usage trend, and support load are secondary factors.

### Priority assignment rules (explicit, not ML)

Priority tiers are assigned by deterministic rules, not by thresholding a single composite score. This was a deliberate choice: it makes every priority decision explainable to a non-technical audience.

```
CRITICAL:  (days_to_renewal < 60d  AND  risk_score > 70)
           OR  contraction_risk_gbp > £50,000
           OR  (sentiment = Negative  AND  urgent_tickets > 2)

HIGH:      risk_score > 50
           OR  (days_to_renewal < 90d  AND  health_score < 50)
           OR  (sla_breaches ≥ 3  AND  NPS < 0)

MEDIUM:    risk_score > 25
           OR  opportunity_score > 40

LOW:       none of the above

PAUSED:    account_status = Paused (segregated, not scored)
```

Each rule involves at least two distinct signals. The thresholds were chosen to reflect real business judgement: a £50K contraction is material regardless of other signals; renewal within 60 days with high risk demands immediate action; negative sentiment combined with multiple urgent tickets represents an escalating customer relationship, not a single incident.

Paused accounts are excluded from the active scoring distribution so they do not distort averages or inflate at-risk counts.

### Confidence scoring for imperfect data

Every account receives a confidence indicator based on how many of the 19 key signal fields are null:
- **High confidence**: ≤ 3 null signal fields
- **Medium confidence**: 4–6 null fields
- **Low confidence**: > 6 null fields

This is displayed as a pill on every account card. The AI is explicitly instructed to acknowledge data gaps rather than fill them with assumptions. Where all three note fields (support summary, customer note, sales note) are absent, the prompt includes an explicit instruction to state "insufficient qualitative data."

---

## 3. How AI Improves the Workflow

The deterministic layer answers: *which accounts are risky, and by how much?*
Claude answers: *why does this account feel risky, what specifically should happen, and who should do it?*

The three concrete improvements AI provides:

**1. Qualitative synthesis**
The CSV contains free-text notes from CSMs and sales reps. A scoring formula cannot interpret "The main sponsor raised concern about low adoption in key teams and requested an executive review" — but Claude can, and can cross-reference it against an NPS of −31 and an upcoming renewal to produce a coherent, specific risk statement.

**2. Action specificity**
Generic dashboards tell you *an account is risky*. Claude tells you: "CSM should schedule an executive sponsor call within 2 weeks, citing the NPS decline and SLA breach pattern, and propose a remediation timeline before the Q3 renewal planning begins." The actions name the owner (CSM/Sales/Leadership), the specific signal driving urgency, and the timing.

**3. Cross-account pattern detection**
The portfolio briefing prompt sends Claude summarised data for all 60 accounts and asks it to identify cross-cutting themes — e.g. "three Enterprise EU accounts share SLA breach patterns," or "accounts in the Renewal stage with negative sentiment are concentrated in the US region." This is analysis that would take a CSM team hours to produce manually.

**What AI does not do:**
Claude does not produce the priority label in isolation. The deterministic score provides an anchor that prevents the model from being swayed by positive note tone on a genuinely risky account. If the deterministic layer says Critical, that information is in the prompt context.

---

## 4. Trade-offs

| Decision | Trade-off |
|---|---|
| In-memory state | Zero infrastructure complexity, but restarts clear AI analysis cache and recorded decisions. Acceptable for a prototype. |
| Lazy AI loading | Users must click to trigger AI analysis. Avoids unexpected latency/cost, but means the first account drill-down is slower than subsequent ones. |
| Sigmoid normalisation | Scores are more spread across 0–100, improving visual discrimination. The sigmoid midpoints are calibrated heuristically — they would need validation against historical churn data in production. |
| Deterministic priority rules | Fully explainable to non-technical stakeholders and auditable. But rules need manual updates as business conditions change; a logistic regression model trained on historical outcomes would be more adaptive. |
| Two data points for MRR trend | Using only current and 3-month-ago MRR means a single anomalous month can create a misleading trend. More granular monthly data would improve this signal significantly. |
| Portfolio briefing cache | The briefing is generated once per server process. Stale if accounts change. A `POST /portfolio/briefing/refresh` endpoint would address this. |
| No email / Slack notifications | Leadership would benefit from push alerts when accounts cross into Critical. This was out of scope but is the highest-impact "build next" item. |

---

## 5. What I Would Build Next

**In order of business impact:**

1. **Push alerts** — webhook or email notification when an account transitions to Critical. This is the gap between "a dashboard you visit" and "a system that finds you."

2. **Persistent storage** — swap the in-memory dict for SQLite or Postgres. Enables AI analysis history, decision audit trail, and score change tracking over time. Two days of work.

3. **Score trend tracking** — store weekly snapshots of risk/opportunity/health scores and display trend arrows. An account that has moved from Low to High over 8 weeks is more alarming than one that was always High.

4. **Bulk AI analysis** — a background job that pre-warms the AI cache for the top 20 Critical/High accounts overnight, so analysts arrive to ready-to-read analyses each morning.

5. **Data validation layer** — currently, null fields are flagged but accepted. A validation layer would highlight accounts where data hasn't been updated in >90 days, prompting CRM hygiene.

6. **Model feedback loop** — record which AI recommendations led to recorded decisions, and eventually use this signal to fine-tune the prompt or the scoring weights. The decision recorder is already in place as the data collection mechanism.

7. **Role-based access** — CSMs see their own accounts; Sales sees pipeline-relevant data; Leadership sees the full portfolio. The JWT infrastructure is already in place.

---

*Built with Python 3.11, FastAPI, React 18, TypeScript, Tailwind CSS, and Anthropic Claude Sonnet 4.*
