# Exécuter l'application avec Docker Compose — US07

Les trois tiers sont la présentation Next.js, le backend composé de deux API,
et la persistance MongoDB : ils correspondent donc à quatre conteneurs.

Prérequis : Git et Docker Desktop démarré en mode conteneurs Linux avec
Docker Compose v2 ou ultérieur. Depuis la racine du dépôt, aucun venv,
node_modules, fichier `.env` ou démarrage préalable de MongoDB n'est nécessaire.
Les premiers builds demandent un accès aux registres de dépendances et aux
ressources de build Next.js, comme dans US06.

## Démarrage (PowerShell)

```powershell
docker compose -p pfs-us07 config --quiet
docker compose -p pfs-us07 up -d --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw 'Démarrage Compose en échec' }
docker compose -p pfs-us07 ps
```

Le nom de projet `pfs-us07` isole les conteneurs, réseaux et volumes des autres
projets du poste. Ne pas réutiliser le nom d'un projet existant pour un test.
`docker compose up -d` sans option fonctionne également avec les valeurs par
défaut ; son nom de projet est alors dérivé du dossier. Conserver le même nom
de projet pour retrouver les mêmes données.

Ouvrir **http://localhost:3000**. Les deux badges doivent afficher `ok` ; ajouter
une tâche avec le formulaire, puis recharger la page pour vérifier sa présence.

## Réseaux, images et dépendances

| Service | Image / commande | Accès |
| --- | --- | --- |
| frontend | pfs-frontend ; `node server.js` | `127.0.0.1:3000` publié ; réseau application |
| auth | pfs-backend ; `uvicorn auth_service.main:app --host 0.0.0.0 --port 8001` | application uniquement ; aucun port publié |
| task | **même image et identifiant** pfs-backend ; `uvicorn task_service.main:app --host 0.0.0.0 --port 8002` | application et data ; aucun port publié |
| mongo | MongoDB **8.0.38**, image officielle épinglée par digest | data uniquement, réseau interne ; aucun port publié |

Compose construit exactement deux images applicatives. Auth porte l'unique
définition de build backend ; Task réutilise cette image sans téléchargement
depuis un registre. `pull_policy: build` réévalue les builds à chaque démarrage
(le cache Docker évite les installations inutiles et intègre les changements
locaux). Pour ne lancer que Task isolément après un nettoyage des images,
construire d'abord le backend avec `docker compose -p pfs-us07 build auth`.

Les utilisateurs non root et les healthchecks HTTP de US06 sont hérités des
images. MongoDB dispose d'un healthcheck `mongosh` avec `ping`. Task attend
MongoDB healthy ; Auth ne dépend d'aucun autre service. Le frontend attend les
deux API healthy. Ces dépendances concernent le démarrage : elles ne constituent
pas une supervision des dépendances après une panne. Le `/health` de Task reste
une sonde de vie ; la création/lecture d'une tâche vérifie réellement MongoDB.

## Chemin d'une requête

Le navigateur appelle `/api/auth/health`, `/api/task/health` et
`/api/task/tasks` sur l'origine du frontend. Le serveur Next.js transmet les
requêtes aux noms Docker `auth:8001` et `task:8002`. Task accède ensuite à
`mongo:27017`, base `tasks_db`, collection `tasks`.

Le routage n'expose que ces trois chemins (GET et POST de création pour les
tâches). Les autres chemins renvoient 404, un POST sur health renvoie 405,
et une API inaccessible renvoie 503 sans exposer son adresse interne. Les
réponses de l'API, notamment une erreur de validation 422, sont conservées.
La barre finale du chemin frontend peut provoquer une redirection Next.js 308 ;
les commandes ci-dessous utilisent les chemins canoniques sans barre finale.

## Variables

Toutes les valeurs Compose ont des valeurs par défaut ; copier `.env.example`
en `.env` est **facultatif**. Ne pas remplacer un `.env` existant sans revue.

| Variable | Moment de lecture | Défaut / rôle |
| --- | --- | --- |
| FRONTEND_PORT | Configuration Compose | 3000 ; seul port publié, sur loopback |
| COMPOSE_IMAGE_TAG | Configuration Compose | us07 ; étiquette locale des deux images applicatives |
| COMPOSE_MONGO_URI | Démarrage Task via Compose | mongodb://mongo:27017/ ; injectée en MONGO_URI |
| CORS_ORIGINS | Démarrage des API | http://localhost:3000 ; origines séparées par virgules |
| AUTH_INTERNAL_URL | Requête côté serveur Next.js | http://auth:8001 dans Compose |
| TASK_INTERNAL_URL | Requête côté serveur Next.js | http://task:8002 dans Compose |
| NEXT_PUBLIC_AUTH_API_URL | Build frontend | /api/auth dans Compose |
| NEXT_PUBLIC_TASK_API_URL | Build frontend | /api/task dans Compose |

Les URL internes sont fixées dans le bloc `environment` du frontend et ne sont
pas envoyées au navigateur. Les chemins publics sont fixés dans les arguments
de build Compose. Les variables `NEXT_PUBLIC_*` ne changent pas avec un simple
`docker run -e` ; une modification nécessite de reconstruire le frontend.

Le mode US06 est préservé : sans Compose, les builds frontend gardent leurs
URL publiques `localhost:8001` et `localhost:8002` par défaut ; les commandes
Uvicorn locales restent identiques. `MONGO_URI` de l'exemple racine concerne ce
mode local ; `COMPOSE_MONGO_URI` empêche de réutiliser accidentellement
`localhost` pour joindre MongoDB depuis un conteneur. Le proxy peut également
être utilisé localement : ses URL serveur par défaut sont `127.0.0.1:8001/8002`.

## Vérifications (PowerShell)

```powershell
$base = 'http://localhost:3000' # adapter si FRONTEND_PORT a été changé
(Invoke-WebRequest "$base/" -UseBasicParsing).StatusCode
Invoke-RestMethod "$base/api/auth/health" # service = auth_service
Invoke-RestMethod "$base/api/task/health" # service = task_service
$title = 'US07-' + [guid]::NewGuid().ToString('N')
$body = @{ title = $title; status = 'todo' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$base/api/task/tasks" -ContentType application/json -Body $body
Invoke-RestMethod "$base/api/task/tasks" | Where-Object title -eq $title

$ids = docker compose -p pfs-us07 ps -q
docker inspect --format '{{.Name}} {{.State.Health.Status}}' $ids
$backendIds = docker compose -p pfs-us07 ps -q auth task
docker inspect --format '{{.Name}} {{.Image}}' $backendIds
docker compose -p pfs-us07 logs --tail 50
```

## Arrêt, redémarrage et persistance

Le volume nommé `<projet>_mongo-data` est monté sur `/data/db`. Il conserve les
tâches après recréation des conteneurs. Le répertoire `/data/configdb`, inutilisé
en serveur autonome, utilise un tmpfs pour éviter des volumes anonymes orphelins.

```powershell
docker compose -p pfs-us07 down # conserve le volume et les tâches
docker compose -p pfs-us07 up -d --wait --wait-timeout 180
Invoke-RestMethod "$base/api/task/tasks" | Where-Object title -eq $title
```

`docker compose -p pfs-us07 stop` puis `start --wait` permet aussi un arrêt et
un redémarrage sans recréer les conteneurs. `down -v` supprime les données :
ne l'utiliser que pour un projet de test dont les données peuvent être effacées.
Cette configuration est une démonstration locale sans authentification MongoDB ;
Auth demeure la simulation de US05. Aucun port de données n'est publié.

## Validation automatisée isolée

Après revue et indexation des fichiers de la story :

```powershell
python scripts/validate_compose.py
if ($LASTEXITCODE -ne 0) { throw 'Validation US07 en échec' }
```

Le script requiert Python et Node/npm. Il exporte uniquement les fichiers de
l'index Git dans un dossier propre sans `.env`, crée un projet Compose unique,
et utilise un port hôte attribué automatiquement et des étiquettes d'image
propres au test. Les autres valeurs sont celles du clone par défaut.

Il exécute config, build/démarrage, vérifie les quatre healthchecks, l'identifiant
commun des API, les utilisateurs et les réseaux, puis crée et relit une tâche
**par le frontend**. Playwright 1.58.2 est installé dans un dossier temporaire
pour tester le vrai formulaire, les badges et le rechargement. La version
compatible de Chromium est téléchargée dans ce dossier temporaire.
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` permet de choisir un exécutable déjà installé.
Aucune dépendance de test n'est ajoutée à l'image frontend ou à son lockfile.

Le script fait ensuite `down` **sans -v**, redémarre le même projet et retrouve
les tâches. Enfin, il supprime uniquement son projet de test et son volume, et
contrôle que les conteneurs et volumes préexistants ont été préservés. Les images
construites restent disponibles localement. Les résultats réels sont consignés
dans [la validation US07](us07-validation.md).
