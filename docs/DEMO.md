# Demo script — Tender Monitor defense

**Duration:** ~7 minutes. **Goal:** show the thesis contribution (config-driven,
two-engine, multi-language scraping) working end to end.

## Before the jury arrives

```bash
docker compose up -d                                   # Mongo + MailHog
cd backend && uv run uvicorn app.main:app --reload     # terminal 1
cd frontend && npm run dev                              # terminal 2
cd backend && uv run python -m scripts.seed_demo       # populate demo tenders
```

Open two browser tabs:
- **http://localhost:5173** — the app
- **http://localhost:8025** — MailHog inbox (for the email step)

Sanity check: the sidebar badge reads **"API connectée"** (green).

---

## 1. Sign in (30s)

- Go to the app → **Créer un compte** → `demo@tender.bf` / `Passw0rd123`.
- Land on the **Tableau de bord** — 4 stat cards + recent tenders (the seeded data).
- *Say:* "Every screen reads live from the FastAPI backend and MongoDB."

## 2. The core idea — add a source with zero code (2 min) ⭐

- Go to **Sources de données** → **+ Ajouter une source**.
- Name: `Portail démo`, URL: `http://localhost:5173/demo-appels-offres.html`,
  type: *Détection automatique* → **Ajouter**.
- On the new source row, click **Tester**.
- *Result:* a preview lists 4 extracted tenders (title, référence, échéance,
  montant) — **not saved**, just a dry run. No selector was configured — the
  engine auto-detected the tender blocks.
- Now click **Lancer le scan** → "4 appel(s) d'offres enregistré(s)". This one
  **persists** them.
- Go to **Appels d'offres** → the 4 new tenders are in the list; click one to see
  its full detail.
- *Say:* "I wrote no code for this site. The engine is generic; the site is a
  configuration document. This is the thesis's core contribution."

## 3. Smart discovery — the 'wrong page' case (1 min)

- Add another source pointing at a site **root** (e.g. `https://www.arcop.bf`).
- Click **Tester** → 0 tenders, but the system **suggests sub-pages** it found
  (appels-offres, avis, téléchargements…).
- *Say:* "Users paste a homepage; the system guides them to the tenders page."

## 4. Multi-language + keyword filtering (1 min)

- Go to **Appels d'offres**. Scroll — note French, **German** (EUR), and
  **English** (GBP) tenders. *Say:* "One parser, three languages — I already have
  a German client."
- Filter box: type `éclairage` → **Filtrer**. Only lighting tenders remain, with
  the matched keyword highlighted. Try `Beleuchtung` (German for lighting).

## 5. Alerts — real email (1.5 min)

- **Paramètres** → add keyword `route`, add your email under *destinataires* →
  **Enregistrer**. (Show the max-5 cap by trying a 6th — it's blocked.)
- **Alertes** → **Envoyer maintenant**.
- Switch to the **MailHog tab (:8025)** → the report email is there, listing the
  matching tenders. *Say:* "Real SMTP delivery, verified in tests with MailHog."

## 6. A real portal + the honest AI slide (1.5 min) ⭐

Tip: set `MAX_PDFS_PER_RUN=5` in `backend/.env` before the demo so this is fast.

- **Sources** → add `https://dgmp.gouv.ml` (Mali, DGMP) → type **PDF**.
- Click **Lancer le scan**. The engine finds the real `..._AAO_....pdf` tender
  documents (AAO = Avis d'Appel d'Offres) and imports them.
- Go to **Appels d'offres**: they appear, all flagged **« À vérifier »**.
- *Say:* "These are real Malian tender notices. They're **scanned images** — no
  text layer — exactly like Burkina's ARCOP. My system detects that and flags
  them instead of inventing data."
- *Then:* "Structured extraction of those scans, and per-client relevance
  scoring, are my next step — a fine-tuned local model. The seam is already in
  the code."

**Why this lands:** you show real data from **two countries**, an honest failure
mode, and a concrete research plan. That's a thesis, not a toy.

### Verified findings you can quote
- `marchespublics.ci`, `armpguinee.org`, `bceao.int`: HTML pages carry **no tender
  text** → the system extracts **nothing** (no fabricated results) and instead
  **suggests the right sub-pages**.
- `dgmp.gouv.ml` (541 PDFs) and `arcop.bf`: tender PDFs are **scans** → flagged
  for AI extraction.

---

## If something fails

- **Badge red / API offline** → is `uvicorn` running? is `docker compose` up?
- **Login 500** → Mongo not reachable; `docker compose ps` should show `tm-mongo`
  healthy.
- **Test returns nothing on the demo page** → confirm the frontend dev server is
  running (the page is served at `:5173/demo-appels-offres.html`).
- **No email in MailHog** → did you add a destinataire email in Paramètres and
  set at least one keyword that matches a seeded tender (e.g. `route`)?

## One-line pitch

> "Tender Monitor turns adding a scraping source from a coding task into a
> configuration task — two generic engines, multi-language, with real-time email
> alerts — and it already serves a client in another country."
