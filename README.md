# Tender Monitor

Config-driven web-scraping SaaS for monitoring public-procurement tenders (BTP
sector) — built for Burkina Faso and multi-country (a German client is supported).
Final-year thesis project · Burkina Institute of Technology.

## What it does

- **Two generic scraping engines** (HTML + PDF) driven entirely by configuration.
  Adding a new source is *data* (a `SiteConfig` document), **never new code**.
- **3-tier fetch engine** — httpx → Playwright → Playwright-stealth — that
  auto-escalates when a site blocks it, and remembers the winning tier per domain.
- **Multi-language extraction** (French / German / English) of references, dates,
  deadlines, authorities, and budgets (FCFA / EUR / GBP / USD).
- **Keyword filtering**, **in-app + email notifications** (max 5 recipients),
  and a per-user report schedule.
- **JWT auth** (argon2 password hashing).
- A **React + Tailwind** frontend.

## Architecture

```
frontend/  React + Vite + TypeScript + Tailwind (TanStack Query, axios)
backend/   FastAPI + pymongo AsyncMongoClient
           app/
             scrapers/  fetch (3 tiers + router) · extract (FR/DE/EN) · engines
             api/       auth · sites · tenders · users · notifications
             repositories/ · models/ · services/ · core/
docker-compose.yml  local infra: MongoDB + MailHog
```

The core idea: `SiteConfig` documents describe *how* to scrape a site (selectors,
PDF rules, locale, rate limits). The `HTMLScraper` and `PDFScraper` engines read
those documents — so onboarding a site is one API call, not a code change.

## Tech stack

Python 3.12 · FastAPI · pymongo (native async `AsyncMongoClient`) · Playwright ·
pdfplumber · APScheduler · Pydantic v2 · argon2 · loguru.
Tests: pytest + testcontainers (real MongoDB) + MailHog — **no mocks**.

## Quick start (development)

Prerequisites: **Docker Desktop**, **uv**, **Node 20+**.

```bash
# 1. Infrastructure (MongoDB + MailHog), detached
docker compose up -d

# 2. Backend  (http://localhost:8000  ·  docs at /docs)
cd backend
uv sync
uv run playwright install chromium      # first time only
uv run uvicorn app.main:app --reload

# 3. Frontend (http://localhost:5173)
cd frontend
npm install
npm run dev

# 4. (optional) seed realistic demo tenders
cd backend && uv run python -m scripts.seed_demo

# 5. (optional) seed the curated, verified tender sources into your account
cd backend && uv run python -m scripts.seed_sources your@email.com
```

### Curated sources (all verified against the live sites)

| Source | Type | Notes |
|---|---|---|
| Portail de démonstration (local) | HTML | extracts 4 tenders, no selector needed |
| ARCOP — Burkina Faso | PDF | 11 docs at `/telechargement/{id}` (scans) |
| DGMP — Mali | PDF | 541 `..._AAO_....pdf` docs (scans), capped by `MAX_PDFS_PER_RUN` |
| Quotidien des Marchés Publics — BF | PDF | 4 gazette PDFs |
| ARMP — Guinée | HTML | no tender text on the landing page → demonstrates sub-page discovery |

Open http://localhost:5173, create an account, and go to **Sources de données**.

## Testing (real infrastructure, no mocks)

```bash
cd backend
uv run pytest                 # spins up a real MongoDB container per session
uv run pytest -m "not slow"   # skip the MailHog email test
```

- MongoDB → `testcontainers`
- HTTP tiers → a real local HTTP server (real sockets)
- PDF/HTML → real fixtures (incl. a real scanned ARCOP PDF)
- Email → real SMTP caught by MailHog

## Notable real-world findings (baked into the design)

- ARCOP serves tender PDFs at `/telechargement/{id}` with
  `Content-Type: application/download` — so PDF detection uses the `%PDF-` magic
  bytes, not the URL suffix or content type.
- Those ARCOP PDFs are **scanned images** (no text layer). They are detected and
  flagged `needs_review`; structured extraction via a **vision model** is the
  documented next step (thesis fine-tuning work).

## Roadmap (post-defense)

- AI vision extraction for scanned PDFs.
- Fine-tuned local (Ollama) model for per-client tender relevance scoring.
- APScheduler cron auto-send for scheduled reports (pipeline already built;
  currently triggered via "Envoyer maintenant").

---
© 2025 Tender Monitor — Burkina Institute of Technology
