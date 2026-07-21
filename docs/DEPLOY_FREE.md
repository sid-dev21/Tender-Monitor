# Déploiement permanent gratuit — Render + MongoDB Atlas

## Le problème que ça résout

Ton document déposé contient une URL Vercel figée dans un QR code, et tu ignores
quel jour il sera évalué. Il faut donc que cette URL ouvre une application
fonctionnelle **à tout moment**, sans que tu aies à faire quoi que ce soit ce
jour-là. Un tunnel depuis ton portable ne peut pas tenir cette promesse : URL
changeante et PC allumé en permanence.

## L'architecture retenue

```
Examinateur → URL Vercel (figée dans le document)
                 │
                 ├─ Interface React               → Vercel      (gratuit, déjà en place)
                 └─ appels /api/*                 → Render      (gratuit, sans carte)
                                                       │
                                                       └─ MongoDB Atlas M0 (gratuit, sans carte)
```

**Ollama n'est pas déployé.** Le plan gratuit de Render offre 512 Mo de RAM ; le
modèle en réclame plusieurs Go. L'analyse sémantique se déclare donc
« indisponible » sur cette démonstration, et l'interface l'explique à
l'utilisateur.

Ce n'est pas une régression par rapport à ton mémoire : le scoring sémantique par
modèle de langage local y figure au chapitre **Perspectives**, comme travail
futur, pas comme fonctionnalité livrée. Un examinateur qui teste l'application y
retrouvera exactement ce que le document décrit. Pour montrer l'IA en
fonctionnement, utilise la pile locale (`docs/DEPLOY_TUNNEL.md`) — c'est du bonus.

---

## Étape 1 — Base de données : MongoDB Atlas (10 min, sans carte)

1. <https://www.mongodb.com/cloud/atlas/register> → créer un compte.
2. **Build a Database** → offre **M0 (Free)** → région Europe (Frankfurt/Paris).
3. **Database Access** → *Add New Database User* → note l'identifiant et le mot
   de passe (évite les caractères spéciaux, ils compliquent l'URL de connexion).
4. **Network Access** → *Add IP Address* → **Allow access from anywhere**
   (`0.0.0.0/0`). Render n'a pas d'IP sortante fixe sur le plan gratuit, donc
   c'est nécessaire ici. À restreindre dans un déploiement réel.
5. **Connect** → *Drivers* → copie l'URL, de la forme :

```
mongodb+srv://UTILISATEUR:MOTDEPASSE@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

## Étape 2 — Pousser le dépôt sur GitHub

Render déploie depuis GitHub. Le dépôt visé est celui dont le lien figure dans
le mémoire (`sid-dev21/tender-monitor`), et son historique doit être conservé —
voir la procédure de rattachement ci-dessous.

```powershell
cd "C:\Users\HP\Desktop\tender-monitor-live"

git remote add origin https://github.com/sid-dev21/tender-monitor.git
git fetch origin

# Point de retour AVANT toute modification
git tag -a v0-pre-deploiement-backend origin/main -m "Etat pre-modifications pour le deploiement backend"
git push origin v0-pre-deploiement-backend

# Greffer le travail actuel sur l'historique existant (fichiers intacts)
git reset origin/main
git add -A
git commit -m "Application complète + configuration de déploiement"
git remote add origin https://github.com/<TON_USER>/tender-monitor-live.git
git push -u origin main
```

## Étape 3 — Déployer l'API sur Render (10 min, sans carte)

1. <https://render.com> → *Get Started* → connexion avec GitHub.
2. **New → Blueprint** → sélectionne le dépôt. Render lit `render.yaml` à la
   racine et configure tout seul le service Docker.
3. Renseigne les variables marquées à compléter :

| Variable | Valeur |
|---|---|
| `MONGO_URI` | l'URL Atlas de l'étape 1 |
| `CORS_ORIGINS` | `["https://TON-APP.vercel.app"]` — JSON, URL Vercel **exacte** |
| `FRONTEND_BASE_URL` | `https://TON-APP.vercel.app` — sans barre oblique finale |

(`JWT_SECRET` est généré automatiquement par Render.)

4. **Apply**. Le premier build prend 5-10 min (installation de Chromium).
5. Quand c'est vert, note l'URL du service :
   `https://tender-monitor-api.onrender.com`.
6. Vérifie : ouvre `https://tender-monitor-api.onrender.com/health` → doit
   répondre `{"status":"ok","mongo":"up"}`.

Si `mongo` répond `down`, l'URL Atlas est mauvaise ou l'accès réseau n'a pas été
ouvert (étape 1.4).

## Étape 4 — Brancher le frontend Vercel

Dans le tableau de bord Vercel du projet :

**Settings → Environment Variables** → `VITE_API_URL` =
`https://tender-monitor-api.onrender.com` → puis **Deployments → Redeploy**.

Une variable d'environnement ne prend effet qu'après reconstruction : modifier la
valeur sans redéployer ne change rien.

## Étape 5 — Peupler la démonstration

Sans données, un examinateur tombe sur des écrans vides. Depuis ton PC, en
pointant sur la base Atlas :

```powershell
cd "C:\Users\HP\Desktop\tender-monitor-live\backend"
$env:MONGO_URI="mongodb+srv://…"   # la même URL qu'à l'étape 1
uv run python -m scripts.seed_demo
uv run python -m scripts.seed_sources ton-email@exemple.com
```

Crée d'abord le compte via l'interface, puis relance `seed_sources` avec cet
e-mail pour que les sources lui appartiennent.

## Étape 6 — Vérification finale

Ouvre l'URL Vercel **dans une fenêtre de navigation privée** (pour partir d'un
état vierge, comme un examinateur) et vérifie :

- [ ] La page de connexion s'affiche, création de compte possible
- [ ] Le tableau de bord montre les appels d'offres de démonstration
- [ ] **Sources** → *Tester* puis *Lancer le scan* fonctionne
- [ ] **Appels d'offres** → le filtrage par mot-clé fonctionne
- [ ] **Paramètres** → l'enregistrement du profil et des mots-clés fonctionne
- [ ] Console du navigateur (F12) : aucune erreur CORS

---

## Limites à connaître (et à assumer devant un examinateur)

- **Premier accès lent.** Le service s'endort après 15 min d'inactivité et met
  30-50 s à se réveiller. Un examinateur qui ouvre l'URL après une pause verra
  une page blanche quelques secondes. Rien n'est cassé.
- **Analyse IA indisponible**, comme expliqué plus haut. L'interface l'annonce
  explicitement.
- **Scraping limité.** 512 Mo de RAM et 0,1 vCPU : la collecte via requête HTTP
  simple (niveau 1) fonctionne, mais l'escalade vers un navigateur complet
  (niveaux 2 et 3) peut échouer faute de mémoire sur les sites lourds.
  `MAX_PDFS_PER_RUN=3` limite aussi les scans PDF.
- **E-mails non délivrés.** Aucun serveur SMTP n'est configuré : les rapports et
  les liens de réinitialisation sont générés et journalisés, mais non envoyés.

Ces trois limites disparaissent sur un serveur dédié — `docs/DEPLOY.md` décrit
l'installation complète (Mongo + Ollama + Caddy avec HTTPS) dès que tu disposes
d'un VPS.
