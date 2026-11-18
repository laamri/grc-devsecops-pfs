# SCRUM-23 / US07 — résultats de validation

Validation locale réelle du 18 novembre 2026, Windows / Docker Desktop Linux
amd64, Docker Compose v5.5.1. Branche : `feature/SCRUM-23-US07-compose`.
Base : `origin/develop`, commit `0152e2d30ded6655e4a018947ec409f6a58c1b8f`.
US06 a été intégrée par la PR #16 : son commit `485b20c` est un ancêtre de
cette base et ses livrables sont identiques. Aucune branche US07 préexistante
n'a été trouvée après `git fetch origin`. Le répertoire était propre.

Commande principale : `python scripts/validate_compose.py`, **code retour 0**.
Le script exporte l'index Git dans une copie temporaire propre via
`git checkout-index --all --prefix=...`. Aucun `.env`, venv ou node_modules du
poste n'est utilisé pour construire les images. La configuration sans `.env`
confirme le port 3000 et l'URI `mongodb://mongo:27017/` ; seuls le port hôte
(attribution automatique) et les étiquettes d'image sont changés pour isoler
le test. Le routage applicatif et ses autres valeurs sont les valeurs par défaut.

## Tests exécutés

| Critère | Test réellement exécuté | Résultat |
| --- | --- | --- |
| Configuration depuis un clone propre | `docker compose -p PROJECT -f docker-compose.yml config --format json` | Quatre services ; deux builds applicatifs ; aucune dépendance aux fichiers locaux |
| Build et démarrage | `docker compose -p PROJECT -f docker-compose.yml up -d --wait --wait-timeout 180` | Deux images construites ; quatre services healthy |
| Santé et utilisateur | `docker inspect` et `docker exec … id -u` | Quatre healthy ; frontend et API non root |
| Backend commun | Comparaison `.Image` des conteneurs Auth et Task | Même identifiant, indiqué ci-dessous |
| Réseaux et ports | Configuration Compose et inspection des réseaux | Seul frontend publié en loopback ; frontend/auth sur application, Task sur application+data, Mongo sur data interne |
| Page et santé via frontend | Requêtes Python urllib sur `/`, `/api/auth/health`, `/api/task/health` | HTTP 200 et noms auth_service/task_service corrects |
| Création et lecture via frontend | POST puis GET `/api/task/tasks` depuis le port publié Next.js | Réponse avec ID et titre ; tâche retrouvée |
| Vrai parcours navigateur | Chromium 145.0.7632.6 / Playwright 1.58.2 ; formulaire Ajouter puis rechargement | Deux badges ok ; tâche visible après ajout et rechargement ; appels fetch de même origine ; aucune erreur inattendue |
| Routage limité | Requêtes sur service/chemin inconnus, POST sur health, tâche invalide | Respectivement 404, 405 et 422 |
| Persistance | `docker compose … down` **sans -v**, inspection du volume, puis `up -d --wait --wait-timeout 180` | Quatre services healthy à nouveau ; les deux tâches restent présentes via frontend |
| Contrôles frontend existants | `npm ci`, `npm run lint`, `npm run build` dans le builder US06 | Réussis ; construction Next.js incluant la nouvelle route serveur |
| Nettoyage isolé | `docker compose … down -v` seulement sur PROJECT en fin de test | Projet de test supprimé ; états des conteneurs préexistants inchangés et volumes préexistants toujours présents |

Dans ce tableau, `PROJECT` vaut `pfs-us07-415e6ce273`. Les requêtes de test
ne ciblent jamais directement un port publié de Task : celui-ci n'est pas publié.
Les utilisateurs, commandes et healthchecks des images US06 sont réutilisés sans
modifier leurs Dockerfiles. Les API Python ne sont pas modifiées ; le frontend
ne dispose pas de suite unitaire distincte des contrôles lint/build existants.

## Réponses et preuves enregistrées

```json
{
  "project": "pfs-us07-415e6ce273",
  "frontendAddress": "http://127.0.0.1:32784",
  "backendImageId": "sha256:2ec41b47a30919a40619d045a5209d3e81fa291785cf9f478655b7d87db01393",
  "health": {
    "frontend": "healthy",
    "auth": "healthy",
    "task": "healthy",
    "mongo": "healthy"
  },
  "auth": {
    "status": "ok",
    "service": "auth_service"
  },
  "task": {
    "status": "ok",
    "service": "task_service"
  },
  "created": {
    "id": "6afdaa744517c6953f76702c",
    "title": "pfs-us07-415e6ce273-http-persistence"
  },
  "browser": {
    "page": "HTTP 200",
    "auth": "ok",
    "task": "ok",
    "createdTitle": "pfs-us07-415e6ce273-browser-task",
    "visibleAfterReload": true,
    "allFetchesSameOrigin": true,
    "errors": []
  },
  "persistedAfterDownUp": [
    {
      "title": "pfs-us07-415e6ce273-http-persistence",
      "status": "todo"
    },
    {
      "title": "pfs-us07-415e6ce273-browser-task",
      "status": "todo"
    }
  ],
  "volume": "pfs-us07-415e6ce273_mongo-data",
  "proxyNegativeTests": "404 unknown service/path; 405 health POST; 422 invalid task",
  "frontendValidation": "npm ci + npm run lint + npm run build in Docker builder",
  "preExistingResourcesPreserved": true
}
```

## Corrections apportées pendant la validation

Le premier POST HTTP utilisait une barre finale : Next.js renvoyait sa
redirection 308. Le client HTTP de validation utilise maintenant le chemin
canonique sans barre finale ; le vrai navigateur suit aussi correctement la
redirection issue du frontend existant.

Le test navigateur a été corrigé pour vérifier le traitement JSON par la tâche
rendue, plutôt que d'attendre la relecture du corps d'une requête redirigée par
l'outil CDP, qui se bloquait. Les annulations `net::ERR_ABORTED` normales pendant
un rechargement sont distinguées des erreurs réseau. La dernière passe utilise
le Chromium fourni avec Playwright et a terminé normalement. Ces corrections
concernent le dispositif de test ; aucune erreur du parcours demandé ne reste
masquée ni aucun critère bloqué.

Le volume MongoDB de test a été conservé pendant le test de redémarrage, puis
supprimé uniquement au nettoyage final du projet isolé. Les builds peuvent
réutiliser le cache BuildKit issu des mêmes sources propres. Les images de test
restent locales. Aucun push, PR, changement Jira ou changement aux données d'un
projet préexistant n'a été effectué. Les livrables US06 et la CI existante sont
conservés ; le diff de la future PR ne contient que US07.
