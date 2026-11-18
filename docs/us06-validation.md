# SCRUM-20 / US06 — validation locale

Validation exécutée le 18 novembre 2026 sur Windows / Docker Desktop,
Linux amd64, depuis la branche `feature/SCRUM-20-US06-images`.
Point de départ : `7ba864ff90a26bc4944f95575fdb7b7ba692608e`.
Aucun push, PR, changement Jira ou Compose.

Commande principale : `python scripts/validate_images.py` (code retour 0).
Le script construit dans une copie temporaire exportée de l'index Git avec
`git checkout-index --all --prefix=...`. Aucun venv, node_modules ou .env du
poste n'est présent dans cette copie. Les Dockerfiles restent la seule source
des dépendances embarquées ; les caches BuildKit réutilisés proviennent de
ces mêmes contextes propres. Les changements ultérieurs de documentation
n'affectent pas les contextes de build autorisés.

| Critère | Commande réellement exécutée (via le script sauf indication) | Résultat |
| --- | --- | --- |
| Backend multi-étapes | `docker build -t pfs-backend:us06 -f backend/Dockerfile .` | Réussi ; installation verrouillée avec `--require-hashes` |
| Frontend multi-étapes | `docker build -t pfs-frontend:us06 frontend` | Réussi ; npm ci, lint et build Next.js réussis |
| Tests Auth | Conteneur jetable : `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` puis `pytest -q -p no:cacheprovider` | 1 test passé, aucune erreur lint |
| Tests Task | Mêmes commandes dans task_service | 1 test passé, aucune erreur lint |
| Frontend en service | `docker run` avec port hôte libre puis `urllib.request.urlopen` sur `/` | HTTP 200 |
| Deux API distinctes | `docker run` du même ID avec `uvicorn auth_service.main:app ... --port 8001` et `uvicorn task_service.main:app ... --port 8002`, puis GET `/health` | HTTP 200 ; services auth_service et task_service |
| Identité commune | `docker inspect --format '{{.Image}}'` sur Auth et Task | Même ID backend ci-dessous |
| MongoDB isolée | `docker run ... mongo:8.0` sur réseau dédié, MONGO_URI pointant son nom ; requêtes Python POST puis GET `/tasks/` | Tâche créée avec ID et retrouvée avec titre/statut |
| CORS au démarrage | GET avec Origin `https://us06.example.test` sur les deux API | Access-Control-Allow-Origin identique à la configuration injectée |
| Non root | `docker image inspect` puis `docker exec <nom> id -u` | Backend 10001:10001, UID Auth et Task 10001 ; frontend node, UID 1000 |
| Santé Docker | `docker inspect --format '{{.State.Health.Status}}'` | healthy pour les trois conteneurs |
| Historique | `docker history --no-trunc` des deux images ; relecture avec `--format '{{.CreatedBy}}'` | Aucun secret applicatif observé ; aucun COPY global du dépôt |
| Fichiers embarqués | `docker export -o ...` de chacun des trois conteneurs, parcours de l'archive sans extraction | Pas de .env local, .git, cache applicatif Python, clé privée PEM ou ancien exemple de secret détecté |
| Outils de test exclus | importlib.find_spec sur pytest/flake8/httpx ; require.resolve sur eslint/typescript dans les conteneurs applicatifs | Absents des environnements finaux |
| Dockerfile manquant | Test négatif séparé : `docker run --rm pfs-backend:us06 sh -c 'test -f /missing-us06/Dockerfile'` | Retour 1 attendu ; CI utilise test -f sans condition de contournement |
| Tailles | `docker image inspect --format '{{.Size}}'` | Mesures ci-dessous |

## Tailles réelles

| Image | Octets (`.Size`) | Mo décimaux |
| --- | ---: | ---: |
| pfs-backend:us06 | 235465573 | 235,47 |
| pfs-frontend:us06 | 306661493 | 306,66 |

Ces tailles locales incluent les couches et ne représentent pas une taille
compressée de téléchargement. Elles concernent Linux amd64.

## Résultat structuré de la dernière passe

```json
{
  "pfs-backend:us06": {
    "id": "sha256:00277cda134f9530d02d2f93ad302bae7877d49363e04b0593cbfe58306b74c2",
    "bytes": 235465573,
    "user": "10001:10001",
    "history_checked": true
  },
  "pfs-frontend:us06": {
    "id": "sha256:057f974f1da6216cfb72d5581263b08a0c51f99c9327343e547e3bbeddd46444",
    "bytes": 306661493,
    "user": "node",
    "history_checked": true
  },
  "api_tests": "Both existing pytest suites and targeted flake8 passed",
  "frontend_checks": "npm ci, npm run lint and npm run build passed in Docker builder",
  "pfs-us06-c8d277fc-auth": {
    "uid": "10001",
    "health": "healthy",
    "files_checked": true
  },
  "pfs-us06-c8d277fc-task": {
    "uid": "10001",
    "health": "healthy",
    "files_checked": true
  },
  "pfs-us06-c8d277fc-frontend": {
    "uid": "1000",
    "health": "healthy",
    "files_checked": true
  },
  "integration": "HTTP 200, service names, shared image ID, Mongo write/read and CORS passed"
}
```

## Observations et limites

Le premier contrôle de fichiers a détecté des caches produits par pip : le
Dockerfile a été corrigé (`--no-compile`, suppression des caches du venv),
puis la validation a été relancée. Un certificat CA public `cacert.pem` a été
distingué des clés privées dans le contrôle des fichiers. L'avertissement
React lié aux URL d'API a été corrigé ; le dernier lint frontend passe sans
cet avertissement. Les tests existants émettent un avertissement Starlette
sur la dépréciation du client httpx ; ils passent tous les deux.

L'inspection des secrets combine les listes de fichiers autorisés, la revue
Dockerfile/historique et une recherche ciblée des fichiers sensibles et des
anciens exemples de secrets. Elle ne prouve pas l'absence de toute valeur
sensible possible. Les empreintes GPG des images officielles et certificats
CA publics ne sont pas des secrets applicatifs.

La CI distante et ses scans Gitleaks/Trivy n'ont pas été exécutés localement.
Leur configuration existante est préservée. Aucun critère Docker demandé ne
reste bloqué. Seuls les conteneurs/réseaux/volumes créés par la validation ont
été nettoyés ; les deux images applicatives sont conservées localement.
