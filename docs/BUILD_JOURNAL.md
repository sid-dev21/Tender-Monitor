# Build journal — Tender Monitor

A narrative of what was built, the problems hit along the way, and the design
choices (with the alternatives rejected). Useful for the thesis "engineering
decisions" chapter and for onboarding.

---

## 1. What we built

A config-driven web-scraping SaaS that monitors public-procurement (BTP) tenders
across French/German/English-speaking countries.

**Backend (FastAPI + pymongo AsyncMongoClient):**
- Generic `BaseRepository[T]`, `PyObjectId` annotated type, `MongoModel` base.
- **3-tier fetch engine** — httpx -> Playwright -> Playwright-stealth — with a
  `TierRouter` that auto-escalates when a site blocks it and remembers the winning
  tier per domain.
- **Two generic engines** — `HTMLScraper`, `PDFScraper` — driven only by
  `SiteConfig` documents. Onboarding a site = one API call, no code.
- **Multi-language extraction** (FR/DE/EN) of reference, dates, deadline, authority,
  budget (FCFA/EUR/GBP/USD) via a single `field_parser`.
- **Auto-block detection** in `html_extractor` — pasting a bare URL with no selector
  still extracts all tender blocks.
- **Sub-page discovery** (`link_discovery`) — when a landing page has no tenders,
  suggest the right sub-pages.
- Dedup via unique index `(reference_number, source_site_id)` + `upsert_by_reference`.
- **JWT auth** (argon2), sites/tenders/notifications APIs, keyword filtering.
- **Email notifications** (max 5 recipients) via aiosmtplib + Jinja2, verified
  against MailHog.
- Per-user report schedule (APScheduler pipeline built; triggered via "Envoyer
  maintenant" for the demo).

**Frontend (React + Vite + TS + Tailwind v4):**
- Login/Register, Dashboard, Tenders (with detail modal), Sites (Test + Scan +
  discovery), Notifications, Settings. French UI.
- Silent-refresh axios interceptor (single-flight) for expired access tokens.

**Testing (no mocks):** testcontainers Mongo, real local HTTP server for tiers,
real HTML/PDF fixtures (incl. a real scanned ARCOP PDF), MailHog for SMTP.

**Infra:** docker-compose (Mongo + MailHog) for dev; app servers run locally with
hot reload. Seed scripts for demo tenders and 5 curated real sources.

---

## 2. Difficulties hit, and how we solved them

### Environment / tooling
- **Python 3.14 wheel risk** — pinned project-local **Python 3.12** via `uv`.
- **Bash tool has no network** (getaddrinfo fails); **PowerShell tool does** — all
  real-site fetches moved to PowerShell; fetch-tier tests use a real local HTTP
  server instead of network calls.
- Docker Desktop needs a restart after reboot; `uv` had to be added to PATH in some
  terminals (`C:\Users\HP\.local\bin`).

### Database
- **Unique dedup index failed on startup** — `E11000 null,null`: a collection with
  duplicate null keys can't take a unique index. Dropped the dev DB and rebuilt.
  Lesson baked in: ensure indexes before inserting, or backfill keys first.

### Auth
- **"Invalid or expired token" on save** — access token is 15 min and the frontend
  never refreshed. Added an axios response interceptor with single-flight silent
  refresh via `/api/auth/refresh` + `lib/tokens.ts`.
- **React crash "Objects are not valid as a React child"** — FastAPI 422 `detail`
  is an array, not a string. Added `errorMessage()` helper + French messages.

### Scraping correctness (surfaced by testing against REAL sites)
Six real bugs, all fixed and covered by tests:
1. Reference regex matched "no" inside words ("dénonciations" -> `ref="nciations"`)
   — tightened `_GENERIC_REFERENCE` to require `n°/no./nr.`, no bare "no".
2. Dates parsed as references (`14/05/2026`) — added `_is_date_like()` guard.
3. Absurd budgets (`15.0`) — added `_MIN_PLAUSIBLE_BUDGET=1000.0`.
4. Menu items parsed as tenders ("Ecrivez-nous") — `_looks_like_tender()` now needs
   vocabulary AND a hard signal (ref/date/year/currency); `_is_noise()` rejects
   candidates with no reference/deadline/budget.
5. Corrupt 0-page PDF not flagged — scanned detection now triggers on
   `len(full_text) < threshold` alone (covers 0-page/corrupt files).
6. No PDF-per-run cap — dgmp.gouv.ml links **541** PDFs. Added `MAX_PDFS_PER_RUN`.

### Product / UX feedback from the user
- **Logo white-box on navy** ("if you have to make a white space around the logo,
  it's not clean") — raster logo on light surfaces only; gold-on-navy wordmark on
  dark surfaces.
- **Mocked data / no detail view** — removed mocks, wired live reads, added tender
  detail modal.
- **"No link to the source"** — `html_extractor` now sets `document_url`; UI shows
  source domain + "Ouvrir la source".
- **PDF "Test" saved nothing** — Test is a dry run; added a `/scrape` endpoint +
  "Lancer le scan" button that persists, plus auto-block detection.

### The honest hard finding
Against real sites: HTML portals (marchespublics.ci, armpguinee.org, bceao.int)
carry **no tender text** on the landing page -> system returns 0 (no fabrication) +
suggests sub-pages. PDF portals (arcop.bf, dgmp.gouv.ml) serve **scanned image
PDFs** -> detected, flagged `needs_review`, deferred to AI. Framed as a thesis
strength (honest failure mode + roadmap), not a gap.

---

## 3. Design decisions and the alternatives rejected

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Async Mongo driver | pymongo `AsyncMongoClient` | Motor | Native async in pymongo>=4.9; Motor now legacy |
| Site onboarding | `SiteConfig` documents read by 2 engines | one scraper class per site | Core thesis claim: adding a site is data, not code |
| Password hashing | argon2-cffi | bcrypt | Modern, memory-hard; bcrypt 72-byte truncation |
| Anti-bot | 3 tiers + auto-escalation + per-domain memory | always launch a browser | httpx is ~100x cheaper; escalate only when blocked |
| PDF handling | stream in-memory, 25MB cap | write to disk | Privacy + no temp-file cleanup; safe in containers |
| PDF detection | `%PDF-` magic bytes | URL `.pdf` suffix / Content-Type | ARCOP serves PDFs at `/telechargement/{id}` as `application/download` |
| Tests | real infra (testcontainers, MailHog, real sockets) | mocks | Mocks hide the real bugs — every scraping bug above came from a real site |
| Scanned PDFs | detect + flag `needs_review` | OCR guess now / fabricate | Honest failure mode; vision model is future work |
| AI placement | config-time (cold path) | scrape-time (hot path) | Keeps scrape deterministic, cheap, testable; protects thesis contribution |
| Captcha (Tier 4) | deferred, `captcha_enabled=false` | build now | Not needed for target sites; keep the seam |

### The big strategic call: "train an LLM vs build an agent"
Decided on a **two-speed architecture**. AI runs at **configuration time**
(human-validated, writes a `SiteConfig`), never at **scrape time** (stays a
deterministic, zero-LLM hot path). Three separate problems, three separate tools:
- (A) finding the listing page = crawl/agent,
- (B) reading scanned PDFs = pre-trained vision model,
- (C) relevance scoring = prompt now, fine-tune later.
Intended infra: Hetzner server + Ollama model.

---

## 4. Roadmap (post-defense, ordered by value/effort)

1. Deterministic 1-level crawl (follow `discover_tender_links` candidates, keep what
   yields tenders) — no AI, best ratio.
2. Vision extraction of scanned PDFs (pre-trained VLM via Ollama on Hetzner ->
   structured JSON; runs once per doc thanks to dedup).
3. Prompt-based relevance scoring + 👍/👎 feedback UI (starts collecting training
   data).
4. LLM onboarding agent for hard sites (config-time, human-validated).
5. Fine-tune local Ollama model for scoring (last — cost/privacy optimization).

---

## 5. Status at time of writing (2026-07-14)

- 59 backend tests passing (real Mongo container).
- 5 curated sources seeded and verified against live sites.
- `MAX_PDFS_PER_RUN=5` set in `backend/.env` for demo speed.
- No in-progress code task; next recommended step is roadmap #1 (1-level crawl),
  pending user go-ahead.
