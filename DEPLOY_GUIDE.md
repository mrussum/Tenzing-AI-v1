# Deployment Guide
## Steps you need to complete before submitting

This guide covers everything that requires a human with access to a browser and
your Anthropic API key. Follow in order — the whole process takes about 20 minutes.

---

## Prerequisites

Before starting, make sure you have:
- [ ] An Anthropic API key (from https://console.anthropic.com)
- [ ] A GitHub account (the repo is already pushed)
- [ ] A Render account (free tier is fine) — https://render.com
- [ ] A Vercel account (free tier is fine) — https://vercel.com

---

## Part 1 — Deploy the Backend to Render

The repo contains a `render.yaml` Blueprint file that pre-fills all the
configuration for you — no form-filling required.

### 1.1 Use the Blueprint (recommended)

1. Go to https://dashboard.render.com and click **New → Blueprint**
2. Connect your GitHub account if prompted, then select the `Tenzing-AI-v1` repo
3. Render reads `render.yaml` and shows you the service it will create — click **Apply**
4. You'll be prompted for the one secret value:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your actual key) |

5. Click **Apply** to start the deploy.

> **Why this is better:** All service settings (name, build command, start command,
> Python version, root directory) are now in the repo. Redeploying from scratch takes
> 30 seconds instead of re-filling a form.

### 1.4 Wait for the first deploy

Render will build and start the service. This takes 2–4 minutes. Watch the log output — you should see:

```
INFO:     Loaded 60 accounts
INFO:     Uvicorn running on http://0.0.0.0:XXXXX
```

### 1.5 Copy your backend URL

Once deployed, Render shows a URL like:

```
https://tenzing-ai-backend.onrender.com
```

**Save this URL** — you need it in Part 2.

### 1.6 Test it

Open `https://tenzing-ai-backend.onrender.com/health` in your browser.
You should see:
```json
{"status": "ok", "accounts_loaded": 60, "ai_analyses_cached": 0}
```

If you see this, the backend is working.

> **Note on cold starts:** Render's free tier spins down after 15 minutes of inactivity.
> The first request after sleep takes ~30 seconds. This is normal for the free tier.
> Upgrade to Starter ($7/month) to eliminate cold starts for the demo.

---

## Part 2 — Deploy the Frontend to Vercel

### 2.1 Import the project

1. Go to https://vercel.com/new
2. Click **Import Git Repository** and connect your GitHub account if not already connected
3. Select `Tenzing-AI-v1` from the list

### 2.2 Configure the build

Vercel should auto-detect Vite. Override any defaults as follows:

| Field | Value |
|---|---|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 2.3 Add the environment variable

In the **Environment Variables** section, add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://tenzing-ai-backend.onrender.com` |

(Replace with your actual Render URL from Step 1.5.)

Click **Deploy**.

### 2.4 Wait for the build

This takes about 1–2 minutes. Once complete, Vercel gives you a URL like:

```
https://tenzing-ai-v1.vercel.app
```

### 2.5 Test the full app

1. Open the Vercel URL
2. Log in with `admin` / `tenzing2024`
3. Confirm the portfolio table loads with 60 accounts
4. Click any account and click **Generate AI Analysis**
5. Go to **Leadership Brief** and click **Generate AI Briefing**

If all three work, you're ready to submit.

---

## Part 3 — Fix CORS (if needed)

If the frontend shows network errors or a blank screen:

1. Open the browser DevTools → Console
2. Look for a CORS error mentioning your Render URL

If you see this, go back to your Render service → **Environment Variables** and add:

| Key | Value |
|---|---|
| `ALLOWED_ORIGIN` | `https://tenzing-ai-v1.vercel.app` |

The backend currently allows `*` (all origins), so this should not be needed.
If it persists, check that `VITE_API_URL` has no trailing slash.

---

## Part 4 — Prepare Your Submission

The brief asks for:

1. ✅ **Link to a working prototype** — your Vercel URL
2. ✅ **Repository** — your GitHub repo URL
3. ✅ **Short write-up** — `SUBMISSION.md` in the repo root

### What to send

Your submission email / form should include:

```
Prototype:   https://tenzing-ai-v1.vercel.app
Repository:  https://github.com/mrussum/Tenzing-AI-v1
Write-up:    https://github.com/mrussum/Tenzing-AI-v1/blob/claude/account-prioritization-tool-J6H74/SUBMISSION.md
```

Adjust the URLs to match yours.

### Include demo credentials in your submission

Add a short note:
```
Login: admin / tenzing2024
```

---

## Troubleshooting

### "Failed to load accounts" on the portfolio page

The frontend cannot reach the backend. Check:
1. `VITE_API_URL` is set correctly in Vercel (no trailing slash)
2. The Render service is running (check the Render dashboard)
3. Wait 30 seconds and refresh — Render free tier may be cold-starting

### AI analysis fails with "ANTHROPIC_API_KEY not set"

The environment variable wasn't picked up. Go to Render → your service → **Environment** tab
and verify the key is present. Then go to **Manual Deploy → Deploy latest commit** to restart.

### Render build fails

Check the build log. Common causes:
- Python version mismatch: add a `runtime.txt` file containing `python-3.11.0` in the `backend/` directory
- Dependency conflict: all packages in `requirements.txt` have pinned versions, so this should not occur

### Vercel build fails

Check the build log. Common causes:
- Wrong root directory: make sure it is set to `frontend`, not the repo root
- TypeScript error: run `cd frontend && npm run build` locally first to catch any errors

---

## Optional: Custom Domain

If you want a more professional URL for the demo:

1. In Vercel → your project → **Settings → Domains**
2. Add a domain you own, or use Vercel's free `*.vercel.app` subdomain (already assigned)

For Render, the free tier URL is `*.onrender.com`. Custom domains require a paid plan.
