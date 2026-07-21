# Démo publique gratuite — Cloudflare Tunnel

Objectif : donner aux examinateurs une URL HTTPS publique qui ouvre
l'application complète (interface + API + scraping + IA), sans serveur, sans
carte bancaire, sans inscription.

**Principe.** Tout tourne sur ton portable (c'est déjà le cas et déjà testé).
`cloudflared` ouvre une sortie chiffrée vers Cloudflare, qui publie une URL
`https://…trycloudflare.com` pointant sur ton `localhost:8000`. Aucun port n'est
ouvert sur ta box, rien n'est exposé à part l'application.

**Simplification appliquée.** Le backend sert désormais lui-même le frontend
compilé (`frontend/dist`), donc **une seule URL** publie toute l'application.
Conséquences directes : plus de CORS à configurer, plus d'URL d'API à injecter
dans le build, et l'URL du tunnel peut changer à chaque redémarrage sans rien
casser. C'est ce qui rend l'approche viable en version gratuite.

---

## Étape 1 — Installer cloudflared (une fois)

```powershell
winget install --id Cloudflare.cloudflared
```

Ferme et rouvre PowerShell ensuite, pour que la commande soit dans le PATH.

## Étape 2 — Compiler le frontend (à refaire après chaque modif du frontend)

```powershell
cd "C:\Users\HP\Desktop\tender-monitor-live\frontend"
npm run build
```

Ça produit `frontend/dist`, que le backend détecte automatiquement au démarrage.
Dans les logs d'uvicorn tu dois voir `Serving built frontend from …`.

## Étape 3 — Démarrer la pile locale

Trois terminaux (ou onglets), à laisser ouverts pendant toute l'évaluation.

```powershell
# 1 — MongoDB + MailHog
cd "C:\Users\HP\Desktop\tender-monitor-live"
docker compose up -d

# 2 — l'application (API + interface, sur le port 8000)
cd "C:\Users\HP\Desktop\tender-monitor-live\backend"
uv run uvicorn app.main:app --port 8000

# 3 — Ollama : vérifier qu'il tourne (service Windows normalement automatique)
ollama list
```

Note : **pas de `--reload`** ici. Le rechargement automatique sert au
développement ; pendant une démo il redémarre le serveur au moindre fichier
touché et vide le cache des analyses IA.

Vérifie en local avant d'exposer quoi que ce soit : ouvre
<http://localhost:8000> — l'application doit s'afficher, pas seulement l'API.

## Étape 4 — Ouvrir le tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

La sortie affiche une URL du type :

```
https://quelque-chose-aleatoire.trycloudflare.com
```

**C'est l'URL à communiquer aux examinateurs.** Laisse ce terminal ouvert : si
tu le fermes, le tunnel se coupe et l'URL meurt.

## Étape 5 — Préchauffer avant de transmettre l'URL

Ouvre l'URL du tunnel, connecte-toi, et fais une fois chaque action lente :

1. **Paramètres** → renseigne le profil de l'entreprise et les mots-clés.
2. **Sources** → lance un scan pour avoir des appels d'offres en base.
3. **Appels d'offres** → clique **Analyser avec l'IA** et laisse finir (~45 s).

Après ça, le modèle est chargé en RAM et les analyses sont en cache : quand un
examinateur cliquera, ce sera instantané. Sans ce préchauffage, il attend ~1 min
sans savoir si l'application a planté.

---

## Ce qu'il faut savoir (et assumer)

- **L'URL change à chaque redémarrage** du tunnel, en version gratuite. Si tu
  dois couper ton PC, tu devras renvoyer la nouvelle URL. Une URL fixe
  nécessiterait un compte Cloudflare + un nom de domaine.
- **Ton PC doit rester allumé et connecté** pendant la fenêtre d'évaluation.
  C'est la contrepartie du coût nul. Désactive la mise en veille :
  Paramètres Windows → Système → Alimentation → Écran et veille → « Jamais ».
- **Le cache des analyses IA est en mémoire** : redémarrer uvicorn le vide et la
  première analyse suivante reprend ~45 s.
- **MailHog n'est pas exposé** par ce tunnel (il est sur le port 8025). Les
  e-mails de rapport et de réinitialisation partent bien, mais toi seul peux les
  consulter sur <http://localhost:8025>. Si tu veux que les examinateurs voient
  la réinitialisation de mot de passe fonctionner, ouvre un second tunnel :
  `cloudflared tunnel --url http://localhost:8025`.

## Si ça ne marche pas

| Symptôme | Cause probable |
|---|---|
| L'URL du tunnel affiche du JSON au lieu de l'interface | `frontend/dist` absent → refais `npm run build`, puis redémarre uvicorn |
| `Error 502` sur l'URL du tunnel | uvicorn n'écoute pas sur 8000 → vérifie le terminal 2 |
| Connexion impossible, erreur 500 | MongoDB éteint → `docker compose ps` doit montrer `tm-mongo` |
| « IA indisponible » sur tous les appels d'offres | Ollama arrêté → `ollama list`, puis `ollama serve` si besoin |
| L'analyse IA dépasse la minute | Normal au premier appel (chargement du modèle). Voir le préchauffage, étape 5 |
| Le lien de réinitialisation pointe sur localhost | Corrigé : le lien est désormais construit depuis l'URL réellement utilisée par le navigateur |

## Après la soutenance

Cette configuration est une démo, pas un déploiement. `docs/DEPLOY.md` décrit
l'installation sur un vrai serveur (Docker Compose complet : Mongo, Ollama,
Caddy avec HTTPS automatique), utilisable dès que tu as accès à un VPS.
