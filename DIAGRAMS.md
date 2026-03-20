# Diagrams
## Tenzing AI — Account Prioritisation Tool

All diagrams are written in [Mermaid](https://mermaid.js.org/) and render natively on GitHub.

---

## 1. System Architecture

How the major components connect across the frontend, backend, AI layer, and deployment infrastructure.

```mermaid
graph TB
    subgraph Client["Frontend — React + TypeScript  (Vercel)"]
        Login["Login"]
        Portfolio["Portfolio"]
        AccountDetail["Account Detail"]
        Briefing["Leadership Briefing"]
    end

    subgraph Server["Backend — FastAPI  (Render)"]
        AUTH["auth.py\nJWT issue + verify"]
        LOADER["data_loader.py\nCSV parse + feature engineering"]
        SCORER["scoring.py\nRisk · Opportunity · Health + Priority"]
        API["main.py\nREST endpoints + in-memory cache"]
        AIMOD["ai_service.py\nPrompt builder + response parser"]
    end

    subgraph External["External"]
        CSV[("CSV\n60 accounts")]
        CLAUDE["Anthropic API\nClaude Sonnet 4"]
    end

    Login      -->|"POST /auth/login/json"| AUTH
    Portfolio  -->|"GET /accounts"| API
    AccountDetail -->|"GET /accounts/{id}"| API
    AccountDetail -->|"GET /accounts/{id}/analysis"| AIMOD
    Briefing   -->|"GET /portfolio/summary?with_ai=true"| AIMOD

    CSV    --> LOADER
    LOADER --> SCORER
    SCORER --> API
    AUTH   --> API
    AIMOD  --> CLAUDE
    AIMOD  --> API
```

---

## 2. Data Flow

How a raw CSV record becomes a scored, prioritised, AI-analysed account in the UI.

```mermaid
flowchart LR
    CSV[("CSV\n60 accounts")] --> Parse

    subgraph data_loader.py
        Parse["pandas read_csv\ntype coercion\nnull detection"]
        Parse --> Derive["Derive features\n─────────────\nmrr_trend\nseat_utilisation\ndays_to_renewal\nnull_field_count\nconfidence label"]
    end

    subgraph scoring.py
        Derive --> RS["Risk Score\n16 weighted signals\n→ logistic sigmoid\n→ 0–100"]
        Derive --> OS["Opportunity Score\n11 weighted signals\n→ logistic sigmoid\n→ 0–100"]
        Derive --> HS["Health Score\nbaseline 50\n± additive modifiers\n→ clamp 0–100"]
        RS & OS & HS --> PR["Priority Rules\nCritical / High / Medium / Low / Paused"]
        PR --> SORT["Sort\npriority tier → risk desc → ARR desc"]
    end

    subgraph main.py
        SORT --> MEM["_accounts\nin-memory list"]
    end

    subgraph ai_service.py
        MEM --> CTX["Build JSON context\n(all signals + notes)"]
        CTX --> CL["Claude Sonnet 4"]
        CL --> AIA["AIAnalysis\npriority · reasoning\nrisks · opportunities · actions"]
        AIA --> CACHE["_ai_cache\ndict keyed by account_id"]
    end

    MEM   --> UI["React Frontend"]
    CACHE --> UI
```

---

## 3. Prioritisation Decision Tree

The exact logic inside `scoring.py → assign_priority()`. Every branch cites ≥ 2 independent signals.

```mermaid
flowchart TD
    START(["Account enriched\nwith scores"]) --> PAUSED

    PAUSED{{"account_status\n= Paused?"}}
    PAUSED -->|Yes| P["⏸ PAUSED\nExcluded from active scoring"]
    PAUSED -->|No| C1

    C1{{"days_to_renewal < 60\nAND risk_score > 70?"}}
    C1 -->|Yes| CRIT["🔴 CRITICAL"]
    C1 -->|No| C2

    C2{{"contraction_risk\n> £50,000?"}}
    C2 -->|Yes| CRIT
    C2 -->|No| C3

    C3{{"sentiment = Negative\nAND urgent_tickets > 2?"}}
    C3 -->|Yes| CRIT
    C3 -->|No| H1

    H1{{"risk_score > 50?"}}
    H1 -->|Yes| HIGH["🟠 HIGH"]
    H1 -->|No| H2

    H2{{"days_to_renewal < 90\nAND health_score < 50?"}}
    H2 -->|Yes| HIGH
    H2 -->|No| H3

    H3{{"SLA breaches ≥ 3\nAND NPS < 0?"}}
    H3 -->|Yes| HIGH
    H3 -->|No| M1

    M1{{"risk_score > 25?"}}
    M1 -->|Yes| MED["🟡 MEDIUM"]
    M1 -->|No| M2

    M2{{"opportunity_score > 40?"}}
    M2 -->|Yes| MED
    M2 -->|No| LOW["🟢 LOW"]
```

---

## 4. AI Analysis — Sequence Diagram

The request lifecycle for per-account AI analysis, including the server-side cache.

```mermaid
sequenceDiagram
    participant U  as User
    participant FE as Frontend (React)
    participant BE as Backend (FastAPI)
    participant CA as _ai_cache
    participant CL as Claude Sonnet 4

    Note over U,FE: User opens account detail page
    U  ->> FE: Navigate to /accounts/ACC-001
    FE ->> BE: GET /accounts/ACC-001
    BE -->> FE: AccountDetail (scores, signals, notes)
    FE -->> U:  Render page — deterministic scores visible immediately

    Note over U,FE: User requests AI analysis
    U  ->> FE: Click "Generate AI Analysis"
    FE ->> BE: GET /accounts/ACC-001/analysis

    BE ->> CA: Check _ai_cache["ACC-001"]

    alt Cache hit (subsequent visits)
        CA -->> BE: Cached AIAnalysis
        BE -->> FE: AIAnalysis  ← instant
    else Cache miss (first request)
        BE ->> CL: messages.create(system_prompt + account_context)
        CL -->> BE: JSON — priority, risks, opportunities, actions
        BE ->> CA: Store AIAnalysis in _ai_cache["ACC-001"]
        BE -->> FE: AIAnalysis
    end

    FE -->> U: Render priority reasoning, risks, actions
    Note over U,FE: User clicks ↻ refresh button
    U  ->> FE: Click refresh
    FE ->> BE: GET /accounts/ACC-001/analysis?refresh=true
    BE ->> CL: Fresh Claude call (bypasses cache)
    CL -->> BE: Updated AIAnalysis
    BE ->> CA: Overwrite cache entry
    BE -->> FE: Updated AIAnalysis
```

---

## 5. User Journey

The 7 steps from the brief's Example User Flow, mapped to the actual screens and API calls.

```mermaid
flowchart LR
    S(["Start"])

    S  --> L
    L  --> P
    P  --> T
    T  --> D
    D  --> R
    R  --> A
    A  --> REC
    REC --> E(["Done"])

    L["① Sign In\nLogin.tsx\nPOST /auth/login/json\n→ JWT stored"]
    P["② Portfolio Overview\nPortfolio.tsx\nKPI row + priority\ndistribution chart"]
    T["③ Prioritised Accounts\nSorted table\nCritical → High → Medium → Low\nFilters + search"]
    D["④ Drill Into Account\nAccountDetail.tsx\nCommercial · Health\nSupport · Leads · Notes"]
    R["⑤ Reasoning & Evidence\nAIPanel.tsx\npriority_reasoning\ntop_risks with evidence"]
    A["⑥ Recommended Actions\nAIPanel.tsx\n3 actions with owner\nCSM / Sales / Leadership"]
    REC["⑦ Record Decision\nDecisionRecorder.tsx\nPOST /accounts/{id}/decisions\nTimestamped + attributed"]
```

---

## 6. Deployment Topology

How the two deployed services connect to each other, the source repo, and the Anthropic API.

```mermaid
graph TB
    GH["GitHub\nmrussum/Tenzing-AI-v1\nbranch: claude/account-prioritization-tool-J6H74"]

    subgraph Render["Render  (backend)"]
        BE["FastAPI · Python 3.11\nuvicorn\nrender.yaml Blueprint\nruntime.txt pins Python version"]
    end

    subgraph Vercel["Vercel  (frontend)"]
        FE["React SPA · Vite build\nvercel.json → SPA rewrite rule\nVITE_API_URL env var"]
    end

    ANT["Anthropic API\nClaude Sonnet 4\nclaude-sonnet-4-20250514"]
    USR(["Browser"])

    GH  -->|"auto-deploy on push\nrender.yaml Blueprint"| BE
    GH  -->|"auto-deploy on push"| FE
    FE  -->|"HTTPS REST\nBearerToken"| BE
    BE  -->|"Anthropic SDK\nANTHROPIC_API_KEY"| ANT
    USR -->|"HTTPS"| FE
```
