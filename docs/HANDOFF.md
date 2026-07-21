# Handoff — reprise dans VS Code / Claude Code

Contexte : session Cowork de cette nuit, urgence réelle. Dépôt des documents
déjà fait (soutenance en document-only, pas de jury). Deadline pour que
l'application soit testable par les examinateurs : **lundi 23h environ**
(corrections commencent mardi). Ce fichier résume l'état exact du code pour
reprendre la main dans VS Code sans tout réexpliquer.

## 0. Avant toute chose : `.git/index.lock`

Le dossier a été monté et manipulé depuis un environnement Cowork en parallèle
de VS Code cette nuit. Si Git se plaint d'un `index.lock` existant au premier
`git status` dans VS Code, et qu'aucun autre process Git ne tourne
réellement : supprime `.git/index.lock` à la main avant de continuer.

## 1. Git — état et stratégie de branche recommandée

`git status` montre une quantité énorme de travail non commité : quasi tout
`frontend/src` (composants, pages, lib, api client — le frontend entier a été
développé mais jamais poussé), plusieurs fichiers backend modifiés
(extracteurs, `sites.py`, `site_dto.py`...), et tout ce qui a été ajouté cette
nuit. Dernier commit sur `origin/main` : `2b2c61d` ("Phases 6-10: engines,
auth, sites/tenders/notifications APIs") — le frontend n'existe pas du tout
côté remote.

**Recommandation** (adapte si tu préfères une autre approche, mais évite de
laisser ça non commité une minute de plus vu la deadline) :

```bash
git add -A
git commit -m "Frontend complet (auth, dashboard, sources, alertes, param.)"
git push origin main
```

Ce commit rattrape uniquement le travail *déjà validé* (le frontend existant,
les correctifs d'extraction) — rien de risqué, c'est du code qui tournait déjà
localement. Une fois ce checkpoint poussé, ouvre une branche dédiée pour la
suite (scoring LLM + déploiement), pour pouvoir revenir instantanément à un
`main` qui marche si quelque chose casse cette nuit :

```bash
git checkout -b feat/llm-scoring-deploy
```

Travaille sur cette branche jusqu'à validation manuelle complète (voir
section 3), puis merge et push sur `main` avant le déploiement réel.

## 2. Ce qui a été construit cette nuit (scoring LLM)

**Décision de design** : scoring sémantique **à la demande** (bouton, pas
automatique), sur le sous-ensemble déjà filtré par mots-clés, capé à
`settings.score_max_tenders` (15) tenders par appel. Pas de nouvelle
collection Mongo, pas de cache — chaque appel relance les requêtes Ollama.
Volontairement : le "two-speed principle" du `CLAUDE.md` (l'IA ne tourne
jamais dans le hot path du scraping) reste respecté à 100%, et zéro migration
de schéma = zéro risque la veille du rendu.

Fichiers touchés :

| Fichier | Rôle |
|---|---|
| `backend/app/core/config.py` | `ollama_host`, `ollama_model` (`qwen2.5:1.5b-instruct`), `ollama_timeout_s`, `score_max_tenders` |
| `backend/.env.example` | mêmes clés documentées |
| `backend/app/models/user.py` | `company_profile: str \| None` (texte libre, max 2000) |
| `backend/app/schemas/auth_dto.py` | `UserResponse.company_profile` + `CompanyProfileUpdate` |
| `backend/app/api/users.py` | `PATCH /api/users/me/profile` |
| `backend/app/services/relevance_scorer.py` | **nouveau** — appel Ollama `/api/chat` avec **structured outputs** (JSON Schema en `format`, pas juste `"format":"json"`), parsing tolérant, fallback `(0, raison)` si injoignable/invalide, jamais d'exception propagée |
| `backend/app/schemas/tender_dto.py` | `TenderResponse.relevance_score` / `relevance_reason` (nullable) |
| `backend/app/api/tenders.py` | `POST /api/tenders/score` — boucle séquentielle sur le sous-ensemble filtré, trie par score desc |
| `backend/tests/services/test_relevance_scorer.py` | **nouveau** — 4 tests, vrai serveur HTTP local (pas de mock) qui joue le rôle d'Ollama, conforme à la philosophie "no mocks" du repo |
| `frontend/src/api/auth.ts`, `frontend/src/api/users.ts` | `company_profile` dans `UserProfile`, `updateCompanyProfile()` |
| `frontend/src/api/tenders.ts` | `relevance_score`/`relevance_reason` sur `Tender`, `scoreMyTenders()` |
| `frontend/src/pages/SettingsPage.tsx` | Card "Profil de l'entreprise" (textarea, 2000 car. max) |
| `frontend/src/pages/TendersPage.tsx` | bouton "Scorer avec l'IA", badge de pertinence coloré, tri par score |

**Non touché, volontairement** : `backend/app/scrapers/**` (moteur de
scraping, la partie la plus testée/protégée selon le `CLAUDE.md` lui-même),
rate limiting, scheduler APScheduler.

## 3. Ce qui N'EST PAS validé — priorité #1 pour la session VS Code

Le sandbox Cowork n'a pas d'accès réseau vers `ollama.com` ni les releases
GitHub (`api.github.com`, `objects.githubusercontent.com` bloqués — seul
`github.com` en HTTPS direct passe). Donc **`score_tender()` n'a jamais tourné
contre un vrai Ollama**, seulement contre un faux serveur HTTP dans les tests.
Sur ta machine, avec Ollama installé, ça doit être la toute première chose à
vérifier :

```powershell
winget install Ollama.Ollama
ollama pull qwen2.5:1.5b-instruct
```

Puis un test isolé (structured outputs, exactement le format envoyé par
`relevance_scorer.py`) :

```powershell
curl.exe -X POST http://localhost:11434/api/chat -H "Content-Type: application/json" -d '{\"model\":\"qwen2.5:1.5b-instruct\",\"messages\":[{\"role\":\"system\",\"content\":\"Tu notes la pertinence 0-100 d une annonce pour une entreprise, en francais.\"},{\"role\":\"user\",\"content\":\"Profil: entreprise BTP specialisee en voirie. Annonce: Construction d une route bitumee de 12km.\"}],\"format\":{\"type\":\"object\",\"properties\":{\"score\":{\"type\":\"integer\",\"minimum\":0,\"maximum\":100},\"reason\":{\"type\":\"string\"}},\"required\":[\"score\",\"reason\"]},\"stream\":false,\"options\":{\"temperature\":0.1}}'
```

Attendu : un JSON avec `message.content` = `{"score": <int>, "reason": "..."}`.
Si le format diffère, ou si `qwen2.5:1.5b-instruct` répond trop lentement/mal
sur ta machine (CPU only), pistes de repli à évaluer avec Claude Code :
- essayer `qwen2.5:0.5b-instruct` (plus rapide, moins fin) ou `llama3.2:1b`,
- baisser `score_max_tenders` si c'est trop lent pour rester utilisable en
  live devant les examinateurs,
- vérifier la version d'Ollama installée supporte bien les structured outputs
  (`ollama --version`) — fonctionnalité relativement récente.

Ensuite test de bout en bout applicatif :

```powershell
cd backend; uv run uvicorn app.main:app --reload
cd frontend; npm run dev
```

Login → **Paramètres** → renseigner un profil entreprise → **Appels
d'offres** → **Scorer avec l'IA**.

Aussi à lancer côté backend, la suite de tests réelle (jamais exécutée en
entier ce soir, seulement les 4 nouveaux tests via un shim Python 3.10 dans le
sandbox — **la suite officielle doit tourner sous `uv`/Python 3.12 avec Docker
pour les vrais tests testcontainers**) :

```powershell
cd backend
uv run pytest
```

## 4. Déploiement — déjà préparé, pas encore exécuté

Décision : **Hetzner**, version simple ce soir pour la démo examinateurs
(`docs/DEPLOY.md`), la même infra sera durcie plus tard pour le vrai produit
(vrai domaine, vrai SMTP, rate limiting appliqué, scheduler connecté,
sauvegardes — tout listé en bas de `docs/DEPLOY.md`).

Fichiers prêts :
- `backend/Dockerfile` — Python 3.12 + `uv` + Playwright/Chromium avec deps OS.
- `backend/.dockerignore`
- `docker-compose.prod.yml` (racine) — mongo, mailhog, ollama, backend, caddy.
- `Caddyfile` (racine) — HTTPS auto via `sslip.io` (pas de nom de domaine
  requis), reverse proxy vers le backend + MailHog.
- `backend/.env.prod.example` — à copier en `backend/.env.prod` sur le VPS et
  remplir (`JWT_SECRET` via `openssl rand -hex 32`, `CORS_ORIGINS` = URL
  Vercel exacte en JSON).
- `docs/DEPLOY.md` — runbook complet étape par étape (création VPS Hetzner,
  Docker, secrets, lancement, pull du modèle Ollama, branchement Vercel,
  checklist de vérification bout-en-bout).

**Rien de tout ça n'a encore été exécuté sur un vrai VPS** — Cowork n'a pas
d'accès SSH sortant utilisable vers une machine externe. C'est la suite
logique une fois la section 3 validée en local.

## 5. Garde-fous à respecter (déjà dans `CLAUDE.md` du repo, rappel)

- Les deux moteurs génériques (`HTMLScraper`, `PDFScraper`) pilotés par
  `SiteConfig` sont la contribution centrale de la thèse — ne jamais
  introduire de code par-site.
- Pas de mocks dans les tests (`unittest.mock` interdit) — vraie infra
  (testcontainers, vrai serveur HTTP local, MailHog) partout, y compris pour
  tout nouveau test sur le scoring.
- `pymongo AsyncMongoClient` (pas Motor), `argon2-cffi` (pas bcrypt),
  PDFs jamais écrits sur disque.
- Git : commits/push gérés par toi (Sidoine), pas par l'agent — même
  consigne pour Claude Code dans VS Code sauf si tu changes explicitement
  cette règle.

## 6. Ce qui reste volontairement hors scope ce soir

Rate limiting non appliqué, scheduler APScheduler non connecté, extraction
vision des PDF scannés (ARCOP/DGMP), nouvelles sources (Côte d'Ivoire,
Sénégal, UEMOA), cache des scores IA. Tout est documenté comme limite
assumée — cohérent avec le ton du reste de la thèse, rien à cacher aux
examinateurs là-dessus.
