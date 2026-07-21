# CLAUDE.md

Guidance for Claude Code working in this repo. Read before touching code.

## What this is

Tender Monitor — config-driven web-scraping SaaS that monitors public-procurement
(BTP/construction) tenders across French/German/English-speaking countries.
Solo final-year CS thesis project + BIT accelerator startup. French UI.

**Thesis contribution (protect this):** exactly **two generic engines** —
`HTMLScraper` and `PDFScraper` — driven entirely by `SiteConfig` documents in
MongoDB. **Adding a source is DATA (a `SiteConfig` document), never new Python
code.** Any change that requires per-site code to onboard a site breaks the core
claim. Reject it or flag it.

## Architecture

```
frontend/  React + Vite + TypeScript + Tailwind v4 (@theme tokens) + TanStack Query + axios
backend/   FastAPI + pymongo AsyncMongoClient
           app/
             core/          config, db, logging, indexes, security, scheduler
             models/        Pydantic v2 + Mongo (PyObjectId, MongoModel base, enums)
             repositories/  generic BaseRepository[T] + per-collection repos
             scrapers/
               fetch/       3 tiers (httpx -> Playwright -> stealth) + TierRouter auto-escalation
               extract/     field_parser (FR/DE/EN), html_extractor, pdf_extractor, candidate
               engines/     base, html_scraper, pdf_scraper, registry
               orchestrator.py  run_scrape(site_id, db, dry_run=)
             api/           health, auth, sites, tenders, users, notifications, notification_schedule
             services/      content_type_detector, keyword_*, notification_*, link_discovery, notifiers/
           scripts/         seed_demo, seed_sources, clear_demo, init_indexes
docker-compose.yml  local infra: MongoDB + MailHog
```

`SiteConfig` describes HOW to scrape (selectors, PDF rules, locale, timezone, rate
limits). Engines read those docs. Onboarding a site = one API call.

## Locked tech decisions — do NOT swap

- **pymongo `AsyncMongoClient`** (native async, pymongo>=4.9). **NOT Motor.**
- **argon2-cffi** for password hashing. **NOT bcrypt.**
- **Pydantic v2**, **Python 3.12** (project-local via `uv`; venv at `backend/.venv`).
- **pdfplumber**, PDFs streamed **in-memory only — NEVER written to disk** (25MB cap).
- **Playwright + playwright-stealth 2.x** (`Stealth().use_async`).
- Package manager: **`uv`** (on PATH at `C:\Users\HP\.local\bin`).

## Testing — NO MOCKS (hard rule)

Real infrastructure only:
- MongoDB via **testcontainers** (real container per session)
- HTTP fetch tiers via a **real local HTTP server** (real sockets), not VCR
- HTML/PDF via **real fixtures** (incl. a real scanned ARCOP PDF)
- SMTP via **MailHog** (testcontainers)

```bash
cd backend
uv run pytest                 # full, real Mongo container
uv run pytest -m "not slow"   # skip MailHog email test
```

Never introduce `unittest.mock` / monkeypatched network. If a test seems to need a
mock, use a real fixture or local server instead.

## Commands

```bash
docker compose up -d                                   # Mongo + MailHog (repo root)
cd backend && uv sync && uv run playwright install chromium   # first time
cd backend && uv run uvicorn app.main:app --reload     # API :8000, docs /docs
cd frontend && npm install && npm run dev              # UI :5173
cd backend && uv run python -m scripts.seed_demo               # 10 demo tenders
cd backend && uv run python -m scripts.seed_sources you@email  # 5 curated sources
cd backend && uv run python -m scripts.clear_demo             # remove demo tenders only
cd frontend && npx tsc --noEmit -p tsconfig.app.json          # frontend typecheck
```

## Environment gotchas (Windows)

- **Bash tool has NO network** (getaddrinfo fails). **PowerShell tool HAS network.**
  Use PowerShell for any real-site fetch/download.
- Secrets live only in `backend/.env` (gitignored). Only `.env.example` is committed.
- `MAX_PDFS_PER_RUN=5` in `.env` for fast demos (default 20; dgmp.gouv.ml links 541).

## Git

- **User manages ALL commits/pushes.** Never run `git commit` / `git push` — only
  provide commands. Branch is `main`.

## Domain rules baked into extraction

- Dedup via unique index `(reference_number, source_site_id)` + `upsert_by_reference`.
- Candidate becomes a tender only with a hard signal (ref/date/year/currency) AND
  vocabulary; menu items / date-as-reference / absurd budgets are rejected.
- PDF detection uses `%PDF-` magic bytes, not URL suffix or Content-Type
  (ARCOP serves PDFs at `/telechargement/{id}` as `application/download`).
- Scanned PDFs (no text layer) are detected, flagged `needs_review`, and NOT
  fabricated. Vision extraction is the documented next step, not a current feature.
- Multi-language: `field_parser` handles FR/DE/EN + FCFA/EUR/GBP/USD. A German
  client already exists — keep German + EUR working, not just French + FCFA.

## Roadmap (post-defense, do not build without ask)

1. Deterministic 1-level crawl (follow `discover_tender_links` candidates).
2. Vision extraction of scanned PDFs (Ollama VLM on Hetzner).
3. Prompt-based relevance scoring + 👍/👎 feedback UI.
4. LLM onboarding agent (config-time, human-validated).
5. Fine-tune local model for scoring.

**Two-speed principle:** AI runs at *configuration time* (cold path,
human-validated, writes `SiteConfig`), NOT at *scrape time* (hot path stays
deterministic — zero LLM calls). This preserves the thesis contribution.
