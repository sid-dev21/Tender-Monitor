# Déploiement — checklist pour la nuit (Hetzner/DigitalOcean)

Objectif : backend + Mongo + Ollama + MailHog tournent sur un VPS, accessibles en
HTTPS, et le frontend Vercel pointe dessus. Compte à rebours avant lundi 23h —
suis les étapes dans l'ordre, ne saute rien côté sécurité (JWT_SECRET, CORS).

## ⚠️ -1. Commit + push AVANT tout (2 min) — bloquant

`git status` montre que la quasi-totalité du frontend, `link_discovery.py`,
les scripts (`seed_demo.py`, `seed_sources.py`, `clear_demo.py`) et tout ce qui
a été ajouté ce soir (scoring LLM, Dockerfile, compose, Caddyfile) ne sont
**pas commités**. Le dernier commit sur `origin/main` s'arrête aux Phases
6-10 backend seul. Si tu clones le repo sur le VPS maintenant, tu déploies une
app sans frontend et sans scoring.

```bash
cd "C:\Users\HP\Desktop\final_grade_project"
git add -A
git commit -m "Frontend complet, scoring LLM (Ollama), config déploiement"
git push origin main
```

Vérifie ensuite que `git status` est propre et que le commit apparaît bien sur
GitHub avant de passer à l'étape 0.

## 0. Choisir et créer le VPS (10-15 min)

**Hetzner Cloud** (recommandé — cf. `CLAUDE.md`, c'était déjà le plan) :
1. https://console.hetzner.cloud → créer un compte → ajouter une carte.
2. Nouveau projet → **Add Server** :
   - Image : **Ubuntu 24.04**
   - Type : **CX22** (2 vCPU / 4 Go) minimum, idéalement **CX32** (4 vCPU / 8 Go)
     si tu veux de la marge pour Ollama — un modèle 1.5B tient dans 4 Go mais
     c'est juste.
   - Region : Falkenstein/Nuremberg (peu importe, pas de client latence-sensible
     ce soir).
   - SSH key : colle ta clé publique (`cat ~/.ssh/id_ed25519.pub` en local ; si
     tu n'en as pas, `ssh-keygen -t ed25519` d'abord).
3. Note l'**IP publique** une fois le serveur créé (ex. `65.21.12.34`).

**DigitalOcean** (alternative) : Create → Droplet → Ubuntu 24.04 → Basic
(2 vCPU/4 Go mini) → ajoute ta clé SSH → note l'IP.

## 1. Connexion + Docker (5 min)

```bash
ssh root@<IP_DU_VPS>

# Docker + Compose plugin (script officiel, marche sur Ubuntu 24.04)
curl -fsSL https://get.docker.com | sh
docker compose version   # vérifie que le plugin est bien là
```

## 2. Cloner le repo (2 min)

```bash
apt-get update && apt-get install -y git
git clone <URL_DE_TON_REPO> tender-monitor
cd tender-monitor
```

Si le repo est privé sur GitHub, utilise un token (`git clone
https://<token>@github.com/toi/repo.git`) ou une clé de déploiement — pas le
temps ce soir de configurer du SSH côté GitHub si ce n'est pas déjà fait.

## 3. Domaine gratuit (0 min — aucune action DNS)

Pas de nom de domaine → on utilise **sslip.io**, qui résout
`<ip-avec-tirets>.sslip.io` vers l'IP elle-même. Exemple pour `65.21.12.34` :

```
DOMAIN=65-21-12-34.sslip.io
```

Retiens cette valeur, tu la réutilises à l'étape 5.

## 4. Configurer les secrets (3 min)

```bash
cp backend/.env.prod.example backend/.env.prod

# Génère un vrai secret JWT :
openssl rand -hex 32
# → colle le résultat dans backend/.env.prod à la place de JWT_SECRET=...

nano backend/.env.prod
```

Dans `backend/.env.prod`, mets à jour :
- `JWT_SECRET` — la valeur générée ci-dessus.
- `CORS_ORIGINS` — l'URL **exacte** de ton frontend Vercel, en JSON :
  `CORS_ORIGINS=["https://ton-app.vercel.app"]`. Sans ça, le navigateur des
  examinateurs bloquera tous les appels API (CORS).

## 5. Lancer la stack (5-10 min, le build Docker prend du temps la 1ère fois)

```bash
export DOMAIN=65-21-12-34.sslip.io   # ta valeur de l'étape 3
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps    # tout doit être "running"/"healthy"
```

Le build de `backend` installe Playwright + Chromium (~2-3 min) — normal que
ce soit plus long que d'habitude.

## 6. Télécharger le modèle Ollama (2-5 min selon la taille)

```bash
docker compose -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:1.5b-instruct
```

Vérifie qu'il répond :

```bash
curl http://localhost:11434/api/tags
```

## 7. Vérifier le backend en HTTPS

```bash
curl https://65-21-12-34.sslip.io/api/health
```

→ doit renvoyer un `200`. Si Caddy n'a pas encore fini de provisionner le
certificat Let's Encrypt (30-60s au premier lancement), réessaie une fois.

Vérifie aussi MailHog : ouvre `https://mail.65-21-12-34.sslip.io` dans un
navigateur — tu dois voir l'inbox MailHog (vide au début).

## 8. Seed des sources de démo (optionnel mais recommandé)

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.seed_sources ton-email@exemple.com
```

(Remplace par l'email du compte que les examinateurs utiliseront, ou crée le
compte d'abord via l'UI puis relance cette commande.)

## 9. Pointer le frontend Vercel vers le backend

Dans le dashboard Vercel du projet :
**Settings → Environment Variables** → `VITE_API_URL` =
`https://65-21-12-34.sslip.io` → **Redeploy** (un simple changement de env var
ne prend effet qu'après un redeploy — clique **Redeploy** sur le dernier
déploiement, pas besoin de push de code).

## 10. Vérification de bout en bout

- [ ] Ouvrir l'URL Vercel → créer un compte → login fonctionne.
- [ ] **Paramètres** → renseigner le profil entreprise + mots-clés → enregistrer.
- [ ] **Sources** → ajouter une source, **Tester**, **Lancer le scan**.
- [ ] **Appels d'offres** → cliquer **Scorer avec l'IA** → les scores
      apparaissent en quelques secondes/dizaines de secondes.
- [ ] **Alertes** → **Envoyer maintenant** → vérifier l'email dans
      `https://mail.<domaine>.sslip.io`.
- [ ] Onglet réseau du navigateur : aucune erreur CORS.

## Si ça casse

- `docker compose -f docker-compose.prod.yml logs -f backend` — logs du
  backend en direct.
- `docker compose -f docker-compose.prod.yml logs -f caddy` — si le certificat
  HTTPS ne se provisionne pas (souvent : le port 80/443 est bloqué par un
  firewall cloud — vérifie les règles de pare-feu Hetzner/DO, ouvre 80 et 443).
- Score IA qui échoue systématiquement → `docker compose -f
  docker-compose.prod.yml exec backend curl http://ollama:11434/api/tags`
  depuis le conteneur backend, pour confirmer qu'il voit bien Ollama.
- Mémoire insuffisante (Ollama tué / OOM) → repasse sur une taille de VPS
  au-dessus (CX22 → CX32 sur Hetzner), ou utilise un modèle plus petit
  (`qwen2.5:0.5b-instruct`).

## Ce qui n'est PAS fait ce soir (assumé, documenté dans la thèse)

- Rate limiting non appliqué (modélisé, pas branché) — inchangé par rapport au
  document déjà déposé.
- Scheduler APScheduler non connecté — déclenchement manuel (`Envoyer
  maintenant`, `Lancer le scan`), comme dans le script de démo existant.
- Extraction vision des PDF scannés — reste `À vérifier`, comme documenté.
- Scores IA non mis en cache — chaque clic sur "Scorer avec l'IA" relance les
  appels Ollama (~15 tenders max, quelques secondes à ~1 min).
