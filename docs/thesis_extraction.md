# Tender Monitor — Codebase Extraction for Thesis (IMRaD)

> Factual extraction of the implemented system. Every claim is traceable to a file.
> `[NON IMPLÉMENTÉ]` marks features designed/seeded but not yet coded.
> Scope: `backend/` (FastAPI). Frontend (React) is noted only where the API contract touches it.

---

## 1. MATERIALS (→ Methodology)

Versions are the exact ones installed in `backend/.venv` (declared as lower bounds in `backend/pyproject.toml`).

| Technology | Version | Role in THIS project | Discarded alternative + why |
|---|---|---|---|
| Python | 3.12 (`requires-python >=3.12`) | Language; uses `StrEnum`/`IntEnum`, `X \| None`, `zoneinfo` | 3.11 — 3.12 gives native `StrEnum` + faster asyncio |
| FastAPI | 0.139.0 | ASGI web framework; routers, `Depends()` DI, OpenAPI at `/docs` | Flask/Django — async-native + Pydantic-integrated validation |
| Uvicorn | 0.50.1 | ASGI server (`app.main:app`) | Hypercorn — Uvicorn is the FastAPI default |
| Pydantic | 2.13.4 | Domain models + DTO validation; custom `PyObjectId` type | dataclasses/marshmallow — v2 core validation + Mongo alias mapping |
| pydantic-settings | 2.14.2 | `Settings` from env/`.env` (`app/core/config.py`) | manual `os.environ` — typed, cached, validated |
| pymongo (async) | 4.17.0 | DB driver via **`AsyncMongoClient`** (`app/core/db.py`) | **Motor** — explicitly rejected; pymongo now ships native async |
| httpx | 0.28.1 | Tier-1 fetch + PDF streaming (`AsyncClient`) | requests — no native async/streaming |
| Playwright | 1.61.0 | Tier-2 headless Chromium for JS-rendered pages | Selenium — Playwright has better async API + auto-wait |
| playwright-stealth | 2.0.3 | Tier-3 fingerprint hardening (`Stealth().use_async`) | undetected-chromedriver — pairs with Playwright |
| fake-useragent | 2.2.0 | Random realistic User-Agent per fetch | static UA string — rotation reduces trivial UA blocks |
| beautifulsoup4 | 4.15.0 | HTML parsing / CSS `select()` for extraction + link discovery | raw regex on HTML — brittle |
| lxml | 6.1.1 | Fast BS4 parser backend (`BeautifulSoup(html, "lxml")`) | html.parser — lxml is faster/more lenient |
| pdfplumber | 0.11.10 | In-memory PDF text + image extraction (`app/scrapers/extract/pdf_extractor.py`) | PyPDF2 — pdfplumber exposes `page.images` (scan detection) |
| python-jose[cryptography] | 3.5.0 | JWT encode/decode (HS256) (`app/core/security.py`) | PyJWT — jose bundles JWK/JWE headroom |
| argon2-cffi | 25.1.0 | Password hashing (**argon2**, not bcrypt) | **bcrypt** — explicitly rejected; argon2 is the modern KDF |
| aiosmtplib | 5.1.2 | Async SMTP send of report email | smtplib — blocking |
| Jinja2 | 3.1.6 | HTML+text email templating (`templates/email/`) | f-strings — autoescape + template files |
| loguru | 0.7.3 | Structured logging (JSON in prod) (`app/core/logging.py`) | stdlib logging — loguru = less boilerplate |
| APScheduler | 3.11.3 | **Declared** for cron report jobs — **not wired** (see §7) | — |
| python-anticaptcha | 2.0.0 | **Declared** for CAPTCHA solving — **not used** (gated off) | — |
| tenacity | 9.1.4 | **Declared** for retries — **no usage found** in `app/` | — |
| **Dev** pytest | 9.1.1 | Test runner; `asyncio_mode=auto` | — |
| testcontainers[mongodb] | 4.14.2 | Real MongoDB + MailHog containers in tests (no mocks) | mongomock — real DB validates indexes/upserts |
| vcrpy / pytest-vcr | 8.3.0 / 1.0.2 | HTTP record/replay cassettes (config present) | responses — VCR replays real recorded traffic |
| ruff / black / mypy | 0.15.20 / 26.5.1 / 2.1.0 | Lint / format / strict typing (`disallow_untyped_defs`) | — |

---

## 2. METHODS — Architecture Decision Records

### ADR-a — Config-driven generic engines (vs. a class per site)
- **Context.** A tender-monitoring SaaS must onboard many heterogeneous portals; a subclass-per-site design makes every new source a code change, deploy, and test cycle.
- **Decision.** Exactly **two** generic engines — `HTMLScraper` and `PDFScraper` (`app/scrapers/engines/`) — driven entirely by a `SiteConfig` MongoDB document (`app/models/site_config.py`). An `EngineRegistry` (`engines/registry.py`) maps `content_type` → engine. Adding a site is one `POST /api/sites`, never Python.
- **Justification.** `SiteConfig.extraction_rules` holds CSS selectors / PDF discovery rules as *data*; the engines read them. Selectors are all optional, with smart fallbacks (`ExtractionRules.regex_fallback_enabled`, `effective_pdf_link_selector()`), so the minimal onboarding payload is `name + base_url + content_type`.
- **Consequences.** (+) Zero-code onboarding; the invariant is asserted by a test (`test_add_new_site_requires_no_python_code`). (+) Engine logic is tested once, reused for all sites. (−) Only two content shapes are expressible; anything outside HTML-DOM / linked-PDF (e.g. JSON APIs, login-walled portals) is out of scope. (−) Extraction quality depends on per-site selector tuning or the generic regex parser.

### ADR-b — 3-tier auto-escalating fetch engine
- **Context.** Target portals range from static HTML to JS-rendered SPAs to Cloudflare-protected sites; a single fetch strategy either fails on hard sites or wastes a browser on easy ones.
- **Decision.** Three tiers behind one `TierRouter.fetch()` (`app/scrapers/fetch/router.py`): Tier 1 `httpx` (`tier1_httpx.py`), Tier 2 headless Chromium (`tier2_playwright.py`), Tier 3 stealth-hardened Chromium (`tier3_stealth.py`). Pure escalation signals (`signals.py`) decide when to step up; the winning tier per domain is persisted (`DomainRateLimitState.last_working_tier`) and used as the next start point.
- **Justification.** Cost/speed increase with tier; starting cheap and escalating only on block signals (403/429/503, Cloudflare markers, body < 500 chars) minimizes browser use. Per-domain memory avoids re-escalating every run.
- **Consequences.** (+) Uniform `FetchResult` for all tiers; engines are fetch-agnostic. (+) Testable escalation (`test_router.py`, `test_signals.py`). (−) Tier 2/3 require a Chromium install (`playwright install chromium`). (−) Escalation heuristics are fixed thresholds, not learned.

### ADR-c — MongoDB (document store) via native async pymongo
- **Context.** `SiteConfig` is a nested, optional-heavy, per-site-variable schema; a rigid relational schema would need many nullable columns or join tables.
- **Decision.** MongoDB with **`AsyncMongoClient`** (pymongo ≥4.9, **not Motor**) (`app/core/db.py`). One `BaseRepository[T]` (`app/repositories/base.py`) gives typed CRUD returning validated Pydantic models. A reusable `PyObjectId` type (`app/models/objectid.py`) bridges BSON `ObjectId` ↔ Pydantic v2.
- **Justification.** Documents map 1:1 to Pydantic models; nested `ExtractionRules`/`RateLimitConfig` persist without joins. Native async pymongo removes the third-party Motor dependency.
- **Consequences.** (+) Schema evolves without migrations; indexes give the guarantees that matter (§6 dedup). (−) No referential integrity — ownership/consistency enforced in app code (`_owned_site`). (−) `base_url` stored as `str` not `HttpUrl` because `HttpUrl` is not BSON-encodable (`app/models/types.py`).

### ADR-d — Scraper as an in-process module, not a separate microservice
- **Context.** The README frames a "microservice" split; the actual deployment unit matters for the thesis.
- **Decision.** Scrapers live **in-process** inside the FastAPI app under `app/scrapers/` and are invoked synchronously through `run_scrape()` (`app/scrapers/orchestrator.py`) from the Sites API. There is **one** deployable backend service; MongoDB and MailHog are the only separate containers (`docker-compose.yml`).
- **Justification.** For a 10-day MVP, an in-process call is simpler than a message queue + worker; the repository/engine seams keep the scraper extractable later.
- **Consequences.** (+) No broker/worker infra. (−) A `POST /scrape` request blocks on the full fetch+extract (browser tiers can take seconds→minutes); no async job/queue. (−) True microservice separation is aspirational, not realized.

### ADR-e — Job scheduling & persistence
- **Context.** Users configure a report cadence (daily/weekly at HH:MM in a timezone).
- **Decision.** The **schedule is persisted** as a `NotificationSchedule` document (one per user, unique `user_id` index) with `frequency/time/timezone/job_id/last_sent_at` (`app/models/schedule.py`), configured via `POST /api/notification-schedule`. Delivery is currently triggered **manually** by `POST /api/notifications/send-now`. `last_sent_at` is the watermark bounding "new tenders since last report" (`NotificationService.build_matching`).
- **Justification.** Persisting schedule + watermark first lets the notification pipeline be built and tested end-to-end (MailHog) independently of the cron trigger.
- **Consequences.** (+) Report generation is fully working and testable now. (−) **The APScheduler cron that would auto-fire reports is `[NON IMPLÉMENTÉ]`** — `job_id` is stored but no scheduler instantiates a job (§7). Scrapes are likewise only API-triggered, never scheduled.

### ADR-f — CAPTCHA handling: opt-in and gated
- **Context.** Some portals present CAPTCHAs; automated solving has cost and ethical/legal weight.
- **Decision.** CAPTCHA solving is **opt-in and disabled by default**: `CAPTCHA_ENABLED=false`, `CAPTCHA_API_KEY`, `CAPTCHA_MAX_COST_PER_RUN` in `Settings` (`app/core/config.py`); `python-anticaptcha` is a declared dependency; `FetchResult.captcha_detected` is a reserved flag.
- **Justification.** Keeping it gated documents the design intent and cost ceiling without shipping solving behavior for the defense, and avoids paid API calls in tests (`captcha` pytest marker skipped by default).
- **Consequences.** (+) No cost/legal exposure by default. (−) The feature is config + a dependency only — **no detection or solving code exists**; `captcha_detected` is never set (§7, §8).

### ADR-g — Multi-language regex/PDF extraction
- **Context.** Notices arrive as HTML blocks or (often scanned) PDFs, in French, German, and English, with locale-specific dates and currencies (FCFA/EUR/GBP/USD).
- **Decision.** A per-language `field_parser` (`app/scrapers/extract/field_parser.py`) with month tables and keyword/label sets per `Language` (fr/de/en). HTML: CSS selectors first, regex parser fills gaps (`html_extractor.py`). PDF: `pdfplumber` text → same parser; **scanned** PDFs (text < 20 chars with images) are flagged `is_scanned`/`needs_review` rather than fabricated (`pdf_extractor.py`). PDF detection uses `%PDF-` magic bytes, not URL/Content-Type.
- **Justification.** Real ARCOP PDFs are served as `application/download` with no `.pdf` suffix and are image scans, so byte-level detection + honest flagging is required. `Language` is chosen from the site's `locale` (`Language.from_locale`).
- **Consequences.** (+) One parser, three languages, four currencies; robust to messy real files. (+) Confidence rule: ≥4 core fields ⇒ `PARSED`, else `NEEDS_REVIEW` (`candidate.py`). (−) Regex heuristics miss non-standard layouts. (−) Scanned-PDF structured extraction is deferred to a future vision model (a documented seam, not code).

---

## 3. ARCHITECTURE & DATA FLOW (→ Implementation)

### End-to-end scrape flow (source web page → stored Tender)
```
Client (React) ── POST /api/sites/{id}/scrape ─▶ app/api/sites.py: scrape_site()
  1. _owned_site(): SiteConfigRepo.find_by_id → ownership check (404 if not owner)
  2. orchestrator.run_scrape(site_id, db, dry_run=False)
       └ build_registry(db): TierRouter(RateLimitStateRepo) + EngineRegistry(TenderRepo, ScraperRunRepo)
       └ EngineRegistry.engine_for(site.content_type)  →  HTMLScraper | PDFScraper
  3. Engine._collect(site):
       └ TierRouter.fetch(base_url, site):
            _starting_tier(domain)  ← DomainRateLimitState.last_working_tier
            run tier → FetchResult ; signals.should_escalate(status, headers, html)?
               yes → escalate 1→2→3 ; no → _remember(domain, tier)
       └ HTML: html_extractor.extract(html, rules, Language.from_locale(locale), base_url)
            per block: CSS selectors → parse_fields() fallback → noise filter → TenderCandidate
         PDF: _find_pdf_urls(html)  (selector | regex pattern | default a[href$=".pdf"])
            cap at MAX_PDFS_PER_RUN ; per URL: stream_to_bytes → looks_like_pdf(%PDF-)
            → pdf_extractor.extract() → parse_fields() OR flag is_scanned
       └ BaseScraperEngine._to_tender(candidate, site, tier): reference = ref_number OR document_url
  4. _save(): TenderRepo.upsert_by_reference() per tender
       └ upsert on (reference_number, source_site_id): $setOnInsert key+created_at,
         $set mutable fields, $inc times_seen  (unique index enforces dedup)
  5. _finish_run(): ScraperRunRepo.insert(ScraperRun{tenders_found, tier_used, errors})
  6. Response: ScrapeRunResponse{tenders_found, errors}
```
Dry-run variant (`POST /sites/{id}/test`) runs steps 1–3 via `engine.preview()` (no `_save`, no run record); if 0 tenders, it calls `link_discovery.discover_tender_links()` and returns `suggested_links`.

### Components (single responsibility)
| Component | File | Responsibility |
|---|---|---|
| `Settings` | `core/config.py` | Typed env config (singleton, `lru_cache`) |
| `db` module | `core/db.py` | Single `AsyncMongoClient` lifecycle + `get_db()` |
| `ensure_indexes` | `core/indexes.py` | Idempotent index creation (incl. dedup unique index) |
| `security` | `core/security.py` | argon2 hashing + JWT create/decode |
| `BaseRepository[T]` | `repositories/base.py` | Typed CRUD → Pydantic models |
| `TenderRepo` | `repositories/tender_repo.py` | Dedup upsert by (reference, site) |
| `TierRouter` | `scrapers/fetch/router.py` | Tier selection, escalation, per-domain memory |
| `signals` | `scrapers/fetch/signals.py` | Pure block-detection predicates |
| `HTMLScraper`/`PDFScraper` | `scrapers/engines/` | Fetch+extract+persist per content type |
| `EngineRegistry` | `scrapers/engines/registry.py` | `content_type` → engine dispatch |
| `field_parser` | `scrapers/extract/field_parser.py` | Multi-language field regex extraction |
| `html_extractor`/`pdf_extractor` | `scrapers/extract/` | DOM/PDF → `TenderCandidate` |
| `orchestrator` | `scrapers/orchestrator.py` | Wire deps + `run_scrape()` entry point |
| `content_type_detector` | `services/content_type_detector.py` | Auto HTML vs PDF heuristic |
| `link_discovery` | `services/link_discovery.py` | Suggest tender sub-pages |
| `keyword_normalizer`/`keyword_matcher` | `services/` | Accent-insensitive keyword filtering |
| `NotificationService` + `email` | `services/` | Build report, in-app insert, SMTP send, advance watermark |
| `AuthService` | `services/auth_service.py` | Register / authenticate |
| API routers | `api/*.py` | HTTP surface (auth, users, sites, tenders, notifications, schedule, health) |

---

## 4. INPUTS FOR UML DIAGRAMS (→ Implementation)

### 4.1 Class diagram — MongoDB documents (from Pydantic models)

All documents extend `MongoModel` → `{ id: ObjectId (_id), created_at: datetime, updated_at: datetime }`.

**User** (`users`)
- `email: EmailStr` (unique), `hashed_password: str`, `keywords: list[str]` (≤50), `notification_emails: list[EmailStr]` (≤5), `in_app_notifications_enabled: bool`, `is_active: bool`

**SiteConfig** (`site_configs`)
- `name: str`, `base_url: str(HttpUrl)`, `content_type: ContentType{html,pdf}`, `is_active: bool`, `locale: str?`, `timezone: str?`, `created_by_user_id: ObjectId → User`
- embeds `ExtractionRules` { list/title/reference/date/deadline/budget/authority `_selector: str?`, `pdf_link_selector: str?`, `pdf_url_pattern: str?`, `regex_fallback_enabled: bool` }
- embeds `RateLimitConfig` { `min_delay_ms`, `max_delay_ms`, `daily_cap: int` }

**Tender** (`tenders`)
- `title`, `reference_number: str`, `publication_date/deadline: datetime?`, `contracting_authority: str?`, `sector: str?`, `estimated_budget: float?`, `currency: str="XOF"`, `document_url: str?`
- `source_site_id: ObjectId → SiteConfig`, `extraction_type: ContentType`, `scrape_tier_used: ScrapeTier?`, `raw_text: str?`
- `status: TenderStatus{parsed,needs_review}`, `times_seen: int`
- `keywords_matched: list[str]`, `matched_users: list[MatchedUser{user_id→User, keywords[]}]`
- **Dedup key:** unique (`reference_number`, `source_site_id`)

**ScraperRun** (`scraper_runs`) — `site_id → SiteConfig`, `start_time`, `end_time?`, `tenders_found: int`, `tier_used: ScrapeTier?`, `errors: list[str]`

**NotificationSchedule** (`notification_schedules`) — `user_id → User` (unique), `frequency{daily,weekly}`, `time: "HH:MM"`, `timezone: IANA`, `is_active`, `last_sent_at?`, `job_id?`

**InAppNotification** (`in_app_notifications`) — `user_id → User`, `tender_ids: list[ObjectId → Tender]`, `seen: bool`

**DomainRateLimitState** (`domain_rate_limit_state`) — `domain: str` (unique), `current_delay_ms`, `consecutive_successes`, `blocked_until?`, `last_request_at?`, `requests_today`, `requests_reset_date?`, `last_working_tier: ScrapeTier?`

**Relationships (cardinalities)**
- User `1 ──< ` SiteConfig (`created_by_user_id`)
- User `1 ──1 ` NotificationSchedule
- User `1 ──< ` InAppNotification
- SiteConfig `1 ──< ` Tender (`source_site_id`)
- SiteConfig `1 ──< ` ScraperRun (`site_id`)
- InAppNotification `>──< ` Tender (embedded `tender_ids`)
- Tender `>──< ` User (embedded `matched_users`) — *populated by matcher at query time, not persisted by scraper*
- DomainRateLimitState — keyed by domain string, no FK (derived from `base_url` host)

### 4.2 Use case diagram (from API endpoints)

**Actor: Unauthenticated visitor** — Register; Login; Refresh token.
**Actor: Authenticated user** —
- Manage sources: create (auto-detect type), list, get, update, delete, **Test (dry-run)**, **Scrape (persist)**
- Browse tenders: list all (keyword filter), list "mine" (saved keywords)
- Manage profile: view me, set keywords, set notification emails
- Manage alerts: get/set schedule, list/mark-seen in-app notifications, **Send report now**

**Actor: System / scheduler (aspirational)** — auto-run scheduled scrapes & reports → `[NON IMPLÉMENTÉ]`.
**Actor: MongoDB / SMTP (MailHog/Gmail)** — supporting external systems.
**Actor: Target portal websites** — scraped sources (ARCOP, DGMP, …).

### 4.3 Sequence diagram — API-triggered scrape
```
User→Frontend        : click "Lancer le scan"
Frontend→SitesAPI    : POST /api/sites/{id}/scrape  (Bearer access token)
SitesAPI→deps        : get_current_user() → decode JWT → UserRepo.find_by_id
SitesAPI→SiteRepo    : _owned_site() find_by_id + ownership check
SitesAPI→Orchestrator: run_scrape(site_id, db, dry_run=False)
Orchestrator→Registry: engine_for(site.content_type)
Registry→Engine      : HTMLScraper|PDFScraper._collect(site)
Engine→TierRouter    : fetch(base_url, site)
TierRouter→RateRepo  : find_by_domain(domain) → starting tier
TierRouter→Tier(n)   : fetch_tierN() → FetchResult
TierRouter→signals   : should_escalate()?  [loop 1→2→3 until ok]
TierRouter→RateRepo  : apply($set last_working_tier)
Engine→Extractor     : html_extractor/pdf_extractor → [TenderCandidate]
Engine→TenderRepo    : upsert_by_reference() per tender  [dedup, $inc times_seen]
Engine→RunRepo       : insert(ScraperRun{found, tier, errors})
Engine→Orchestrator  : ScrapeResult
Orchestrator→SitesAPI: result
SitesAPI→Frontend    : 200 ScrapeRunResponse{tenders_found, errors}
```
(PDF variant inserts, between fetch and extract: `_find_pdf_urls` → cap → per-URL `httpx.stream` → `looks_like_pdf`.)

---

## 5. API REFERENCE (from routers)

Base prefix `/api`. All non-auth/health routes require `Authorization: Bearer <access>` (`get_current_user`).

| Method + Route | Role | Input | Response |
|---|---|---|---|
| `GET /health` | Liveness + Mongo ping | — | `{status, mongo}` |
| `POST /api/auth/register` | Create account | `{email, password(≥10, alpha+digit)}` | 201 `UserResponse` / 409 if exists |
| `POST /api/auth/login` | Get tokens | `{email, password}` | `TokenResponse{access, refresh, token_type}` / 401 |
| `POST /api/auth/refresh` | Rotate access token | `{refresh_token}` | `TokenResponse` / 401 |
| `GET /api/users/me` | Current profile | — | `UserResponse` |
| `PATCH /api/users/me/keywords` | Replace keywords (normalized, capped) | `{keywords: [str]}` | `UserResponse` |
| `PATCH /api/users/me/notification-emails` | Set recipients (≤5) | `{emails: [EmailStr]}` | `UserResponse` / 422 if >5 |
| `POST /api/sites` | Create source (auto-detect type if omitted) | `SiteCreateRequest{name, base_url, content_type?, extraction_rules?, rate_limit_config?, locale?, timezone?}` | 201 `SiteResponse` |
| `GET /api/sites` | List own sources | — | `[SiteResponse]` |
| `GET /api/sites/{id}` | Get one (owned) | — | `SiteResponse` / 404 |
| `PATCH /api/sites/{id}` | Update (owned) | `SiteUpdateRequest` (all optional) | `SiteResponse` |
| `DELETE /api/sites/{id}` | Delete (owned) | — | 204 |
| `POST /api/sites/{id}/test` | **Dry-run** preview, no persist; suggests sub-pages if empty | — | `SiteTestResponse{count, tenders[], suggested_links[]}` |
| `POST /api/sites/{id}/scrape` | **Real** scrape, persists (dedup) | — | `ScrapeRunResponse{tenders_found, errors}` |
| `GET /api/tenders` | List recent tenders, optional keyword filter | `?keywords=csv&limit≤500` | `[TenderResponse]` |
| `GET /api/tenders/mine` | Tenders matching user's saved keywords | `?limit≤500` | `[TenderResponse]` |
| `GET /api/notifications` | In-app inbox | `?unseen_only=bool` | `[InAppNotificationResponse]` |
| `PATCH /api/notifications/{id}/mark-seen` | Mark one seen (owned) | — | `InAppNotificationResponse` / 404 |
| `POST /api/notifications/send-now` | Build+deliver report now (in-app + email) | — | `SendNowResponse{sent, count, emailed}` |
| `GET /api/notification-schedule` | Get schedule | — | `ScheduleResponse` / 404 |
| `POST /api/notification-schedule` | Create/update schedule (one per user) | `ScheduleRequest{frequency, time, timezone, is_active}` | `ScheduleResponse` |

---

## 6. NOTABLE ALGORITHMS (→ Implementation)

- **Deduplication (upsert by identity).** `TenderRepo.upsert_by_reference` (`repositories/tender_repo.py`): identity = (`reference_number`, `source_site_id`). Mongo `update_one(..., upsert=True)` with `$setOnInsert` (key + `created_at`), `$set` (mutable fields), `$inc times_seen`. A unique index (`core/indexes.py`) makes it race-safe; `created_at` and keyword-match fields are never overwritten. Reference falls back to `document_url` for scanned PDFs (`base.py:_to_tender`).

- **Tier escalation + memory.** `TierRouter.fetch` (`fetch/router.py`): starts at `last_working_tier` (per-domain, `DomainRateLimitState`) or Tier 1; runs the tier, feeds `should_escalate(status, headers, body)` (`fetch/signals.py`), and steps 1→2→3 until a clean response or exhaustion; remembers the winner.

- **Block detection (pure).** `signals.should_escalate`: escalate if status ∈ {403,429,503}, or Cloudflare markers appear in headers/first-4000-chars of body, or body < 500 chars ("empty/JS-required"). No I/O ⇒ unit-testable.

- **Field parsing (multi-language).** `field_parser.parse_fields` (`extract/field_parser.py`): per-`Language` month tables + keyword sets. Reference via labeled patterns then a strict generic `N°/No./Nr.` fallback that rejects date-like tokens; deadline = date within 80 chars after a deadline keyword; budget = amount adjacent to a currency token, parsed by `_parse_amount` (handles `250 000 000`, `1.234.567,89`, `1,234,567.89`), rejecting amounts < 1000. Only fills still-`None` fields (selectors win).

- **HTML block auto-detection.** `html_extractor` (`extract/html_extractor.py`): if no `list_selector`, tries fallback selectors (`article`, `[class*=tender|avis|offre|appel|marche]`, `li`); a block is a tender if it has procurement vocabulary **and** a hard signal (`N°` / date / year / currency, `_SIGNAL_RE`). Noise filter drops blocks with no reference/deadline/budget; whole-page fallback demands ≥2 fields.

- **Scanned-PDF detection.** `pdf_extractor.extract`: `pdfplumber` sums page text + `page.images`; if extracted text < 20 chars ⇒ `TenderCandidate(is_scanned=True)` → `needs_review`. `looks_like_pdf` checks `%PDF-` in first 1024 bytes (not URL/Content-Type); in-memory `BytesIO` only, 25 MB cap, never writes disk.

- **Content-type auto-detection.** `content_type_detector.detect_content_type` (`services/`): PDF if the URL body starts with `%PDF-` or Content-Type is `application/pdf`; else parse links and return PDF when ≥30% match `\.pdf | /telechargement/ | /download`.

- **Keyword matching (accent-insensitive).** `keyword_normalizer.normalize` NFKD-strips accents, lowercases, collapses whitespace; `keyword_matcher.matched_keywords` substring-matches normalized keywords against `title + raw_text` (so `ecole` matches `école`, `éclairage`↔`eclairage`).

- **Link discovery.** `link_discovery.discover_tender_links` (`services/`): scans anchors for accent-free procurement keywords (fr/de/en incl. `telechargement`), keeps up to 8 same-host http(s) links — surfaced when a dry-run finds nothing.

- **PDF batch cap.** `PDFScraper._collect`: if discovered PDF URLs > `MAX_PDFS_PER_RUN` (default 20), record `pdf_limit_reached` error and process only the first N (dgmp.gouv.ml links 541).

---

## 7. STATUS (→ Results & Discussion)

**Functional and tested** (real MongoDB via testcontainers; see test list):
- Auth: register/login/me/refresh, weak-password reject, duplicate-email 409, protected-route 401 (`tests/api/test_auth.py`).
- Sites CRUD + ownership isolation + content-type auto-detect + dry-run preview (`tests/api/test_sites.py`).
- Engines end-to-end: HTML scrape+save, PDF stream+save, **dedup on second run**, zero-code new-site invariant (`tests/engines/test_engines.py`).
- Fetch tiers: Tier 1 fetch/block/connection-error; Tier 2 renders JS that Tier 1 can't; router stays/escalates/starts-at-remembered (`tests/scrapers/`).
- Escalation signals (`tests/scrapers/test_signals.py`).
- Multi-language field parsing fr/de/en + amount variants + needs_review threshold (`tests/extract/test_field_parser.py`).
- PDF extractor incl. **a real ARCOP scan flagged**, and a no-disk-write assertion (`tests/extract/test_pdf_extractor.py`).
- HTML extractor block detection (`tests/extract/test_html_extractor.py`).
- Tender dedup at repo + unique-index level (`tests/repositories/test_tender_repo.py`).
- Keyword normalize/match + query filtering (`tests/api/test_keywords.py`).
- Notifications: in-app flow, max-5 emails, schedule create/update, **email delivered to real MailHog** (`tests/api/test_notifications.py`, `slow` marker).
- Link discovery (`tests/api/test_link_discovery.py`).

**Implemented but not covered by automated tests:**
- Tier 3 stealth fetch (`tier3_stealth.py`) — no dedicated test.
- `content_type_detector` — exercised only indirectly via `test_create_autodetects_html`.
- JWT refresh-token expiry/timezone edge cases; email HTML/text template rendering visually.
- The Sites `scrape` path against *live* remote portals (only local-HTTP-server fixtures are tested; live sites gated behind `RUN_INTEGRATION`).

**`[NON IMPLÉMENTÉ]` (designed/seeded, not coded):**
- **Adaptive rate limiting.** `RateLimitConfig` (per-site delays/cap) and `DomainRateLimitState.{current_delay_ms, consecutive_successes, blocked_until, requests_today, requests_reset_date}` exist, but **no code sleeps, backs off, or enforces a daily cap** — no `asyncio.sleep`/delay logic anywhere. Only `last_working_tier` is read/written. The `rate_limit/` package is empty.
- **Scheduler (APScheduler).** Dependency + `NotificationSchedule.job_id` + `ScheduleRepo.find_all_active` exist, but **no scheduler is instantiated**; reports and scrapes fire only via API calls.
- **CAPTCHA detection/solving.** Config flags + `python-anticaptcha` dep + `FetchResult.captcha_detected` exist; **no detection or solving code**; flag never set.
- **AI vision extraction of scanned PDFs** and **per-client relevance scoring** — roadmap only; scanned PDFs flagged `needs_review` as the seam.
- **`matched_users` / persisted keyword indexing on tenders** — matching is computed at query/notification time; the scraper never writes `keywords_matched`/`matched_users` (the `keywords_matched` index is unused for now).

**Test approach:** `pytest` + `asyncio_mode=auto`; **no mocks** for externals — real MongoDB and MailHog via `testcontainers`; real HTML/PDF fixtures (incl. a real ARCOP scan); a real threaded local HTTP server (`tests/conftest.py::LocalServer`) with a browser-gated route to prove Tier 1→2 escalation; VCR cassette config present for HTTP replay; markers `integration`/`slow`/`captcha` for opt-in/slow paths.

---

## 8. LIMITATIONS & TECHNICAL DEBT (→ Discussion)

1. **Rate limiting is data-only.** Politeness delays and daily caps are configured and modeled but never applied — the scraper hits target sites as fast as the network allows. Real risk of IP blocks / ToS issues at scale (`models/rate_limit.py`, `models/site_config.py`).
2. **No scheduler.** "Daily/weekly report" and unattended scraping are configured but require a manual `send-now`/`scrape` call. The core selling point (automatic monitoring) is not yet autonomous (§7).
3. **Synchronous, blocking scrape endpoint.** `POST /scrape` runs fetch (possibly two browser launches) + N PDF downloads inline; a slow site blocks the request and can hit client/proxy timeouts. No job queue, no progress, no cancellation (`api/sites.py`, `orchestrator.py`).
4. **Playwright launches a fresh browser per fetch.** Tier 2/3 do `chromium.launch()`/`close()` every call — heavy for multi-PDF or multi-site runs; no browser pooling (`tier2_playwright.py`, `tier3_stealth.py`).
5. **Extraction heuristics are fragile.** Generic block detection and regex field parsing depend on procurement vocabulary + fixed patterns; unusual layouts, tables, or non-fr/de/en notices silently under-extract (→ `needs_review`). `sector` is never populated by any parser.
6. **CAPTCHA is a stub.** `captcha_detected` never set; a real challenge simply looks like a block and exhausts tiers.
7. **`tenacity` declared but unused** — no retry/backoff on transient network errors; a single failed fetch just records an error and moves on.
8. **No pagination / listing crawl.** Engines scrape only the configured `base_url` page; multi-page tender listings beyond page 1 are not followed (only sub-page *suggestions* exist, not automatic crawling).
9. **Auth hardening gaps.** Default `JWT_SECRET` is a placeholder; no refresh-token revocation/rotation store, no rate limiting on login, no account lockout.
10. **Ownership/consistency in app code only.** MongoDB has no FKs; deleting a `SiteConfig` leaves its `Tender`/`ScraperRun` documents orphaned (no cascade).
11. **Scan-limited coverage for the target region.** The two flagship real sources (ARCOP, DGMP) serve **scanned** PDFs, so for those the system currently stores `needs_review` stubs, not structured tenders — the headline extraction value depends on the deferred vision model.
12. **`MAX_PDFS_PER_RUN` truncation is silent to data.** Beyond the cap, remaining tenders are skipped for the run (only an `errors` string records it); no resume/continuation.
13. **README vs. reality drift.** README calls the scraper a "microservice" and lists APScheduler auto-send as built; both are in-process/aspirational — worth aligning before submission.
```
