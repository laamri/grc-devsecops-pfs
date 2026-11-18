<h1 align="center">GovernSecOps</h1>

<p align="center">
  <strong>Unified DevSecOps &amp; GRC Engineering Platform</strong>
</p>

<p align="center">
  Governance &bull; Risk Management &bull; Continuous Compliance &bull; Security Automation
</p>

<p align="center">
  <a href="#vision">Vision</a> &middot;
  <a href="#proposed-solution-architecture">Architecture</a> &middot;
  <a href="#devsecops-and-grc-model">DevSecOps &amp; GRC</a> &middot;
  <a href="#getting-started">Getting Started</a> &middot;
  <a href="#contribution-guidance">Contributing</a>
</p>

A collaborative, academic DevSecOps project focused on building a sample application while integrating Governance, Risk, and Compliance (GRC) practices throughout the software lifecycle.

This repository is intended as a project foundation for learning and practicing secure software delivery, risk-based decision making, and operational governance in a realistic team environment.

## Project status

This repository is currently in an initial project-scaffold phase. It is not a production-ready application and should not be interpreted as a certification or regulatory assertion.

## Vision

Build a small task-management application and evolve its delivery process into a transparent, secure, and risk-driven software lifecycle.

The goal is to move beyond a simple demo project and establish a working model for:

- secure development practices
- continuous integration and delivery
- security scanning and policy enforcement
- compliance evidence collection
- risk-driven release decisions
- monitoring and continuous improvement

## Objectives

1. Design and implement a sample application in a collaborative environment.
2. Use GitHub for version control, reviews, and change tracking.
3. Build CI/CD pipelines with quality and security checks.
4. Include SAST, SCA, secret scanning, container scanning, and IaC validation.
5. Package the application using Docker and deploy through modern infrastructure tooling.
6. Incorporate GRC controls, policies, risk assessments, and approvals into delivery decisions.
7. Maintain evidence for operational audits and security review.

## Proposed solution architecture

The following architecture is a starting point and may evolve as the project matures.

| Layer | Initial choice / target |
| --- | --- |
| Demo API | FastAPI |
| Frontend | Next.js / React |
| Database | MongoDB (implementation actuelle) |
| CI/CD | GitHub Actions |
| Packaging | Docker |
| Infrastructure / orchestration | Terraform + Kubernetes |
| Security scanning | Bandit, dependency checks, secrets checks, container/IaC scanning |
| Policy as code | OPA / Conftest (planned) |
| Observability | Prometheus + Grafana (planned) |
| GRC evidence | Risk register, control matrix, exception log, audit pack |

> These are proposed technologies rather than fixed constraints. Major architectural or tooling changes should be documented in project decision records.

## DevSecOps and GRC model

The project follows a DevSecOps approach where security, compliance, and governance are not treated as separate end-of-cycle activities, but as part of the full delivery pipeline.

### Core principles

- Security is designed in, not bolted on.
- Risks are identified early and tracked continuously.
- Controls are validated through automated checks and human review.
- Compliance evidence is produced as part of engineering work.
- Engineering decisions should be traceable to policy and risk context.

### Lifecycle checkpoints

| Phase | Technical activity | GRC activity | Expected evidence |
| --- | --- | --- | --- |
| Design | Requirements and threat modeling | Asset inventory and risk assessment | Risk register, design review |
| Code | Feature development and review | Access control and ownership | Approved pull requests, review records |
| Build & test | CI, SAST, SCA, secret scanning | Mandatory policy checks | Scan outputs and issue tracking |
| Package & deploy | Containerization and IaC validation | Policy enforcement and approvals | Deployment records, approvals |
| Operate | Monitoring and incident response | Residual risk tracking | Logs, alerts, incident records |
| Audit & improve | Remediation and retrospective | Control effectiveness review | Compliance matrix, corrective actions |

## Repository purpose

This repository serves as the central project hub for:

- application design and implementation
- documentation and decision records
- CI/CD workflow definitions
- security and compliance evidence
- project planning and team collaboration

## Suggested project workflow

1. Define requirements and identify project assets.
2. Model security and business risks for each feature or release.
3. Implement code changes with peer review.
4. Run automated tests and security scans.
5. Package and validate deployment artifacts.
6. Review policy and risk exceptions before release.
7. Monitor operational health and log evidence for audit readiness.

## Getting started

### Prerequisites

Before working on the project, ensure the following tools are available:

- Git
- Python 3.11+ (for backend work and tooling)
- Docker
- Node.js / npm (for frontend work)
- Terraform (for infrastructure work)
- A code editor such as VS Code

### Clone the repository

```bash
git clone git@github.com:laamri/grc-devsecops-pfs.git
cd grc-devsecops-pfs
```

### Typical development flow

```bash
git checkout -b feature/my-change
# implement changes
# run local tests and security checks
# commit and push
```

## Security and compliance note

Automated technical checks are valuable evidence sources, but they do not replace organizational governance, human review, and formal compliance processes. This project is intended to model a realistic DevSecOps environment, not to claim full regulatory certification.

## Contribution guidance

- Keep documentation clear and current.
- Record major technical or policy decisions in a structured way.
- Tie changes to risk, controls, and evidence where relevant.
- Prefer traceable, reviewable changes over undocumented shortcuts.

## License

This project does not currently declare a license. If this repository is intended for open-source use, a license file should be added before public distribution.

## Future direction

The project will evolve from a scaffold into a fuller working implementation with:

- a task-management application
- CI/CD pipelines
- security scanning
- deployment automation
- GRC evidence tracking
- policy-driven release gates

This README should be updated as the project matures and implementation details become concrete.


## Images

US06 construit exactement deux images applicatives : `pfs-frontend` et
`pfs-backend`. MongoDB est une image tierce ; Docker Compose relève de US07.
Les Dockerfiles utilisent des bases minimales fixées par digest, des étapes
séparées et des utilisateurs non root. Le backend installe uniquement les
packages de production de `backend/requirements.lock` (versions et SHA-256).
Le frontend utilise `npm ci`, `package-lock.json` et la sortie Next.js standalone.
Les contextes utilisent des listes de fichiers autorisés dans leurs `.dockerignore`.
Les environnements locaux, caches et outils de test ne sont pas copiés.

### Construire (PowerShell, depuis la racine du dépôt)

```powershell
docker build -f backend/Dockerfile -t pfs-backend:us06 .
docker build --build-arg NEXT_PUBLIC_AUTH_API_URL=http://localhost:8001 --build-arg NEXT_PUBLIC_TASK_API_URL=http://localhost:8002 -t pfs-frontend:us06 frontend
if ($LASTEXITCODE -ne 0) { throw 'Echec du build' }
```

### Configuration

| Variable | Lecture | Valeur locale par défaut / usage |
| --- | --- | --- |
| `NEXT_PUBLIC_AUTH_API_URL` | Build Next.js | `http://localhost:8001` |
| `NEXT_PUBLIC_TASK_API_URL` | Build Next.js | `http://localhost:8002` |
| `MONGO_URI` | Démarrage Task | `mongodb://localhost:27017/` ; utiliser le nom réseau Mongo en conteneur |
| `CORS_ORIGINS` | Démarrage de chaque API | `http://localhost:3000` ; origines séparées par virgules |
| `PORT` | Sonde backend / serveur frontend | Backend : `8001`, mettre `8002` pour Task ; frontend : `3000` |

Les URL `NEXT_PUBLIC_*` sont publiques et intégrées au JavaScript envoyé au
**navigateur**. Elles doivent être accessibles depuis le poste du navigateur,
pas seulement depuis le réseau Docker. Les changer avec `docker run -e` ne
modifie pas le bundle : reconstruire le frontend. Ne jamais y mettre de secret.
Pour le développement local, les valeurs par défaut préservent les commandes
existantes. Next.js lit `frontend/.env.local` ; Python lit les variables du
processus, pas automatiquement les fichiers `.env`.

### Lancer et vérifier (PowerShell)

Exemple pour un poste local disposant des ports 3000, 8001 et 8002.
Utiliser des noms libres ; ne pas remplacer un conteneur existant.

```powershell
docker network create pfs-us06-demo
docker run -d --name pfs-us06-demo-mongo --network pfs-us06-demo mongo:8.0
docker run -d --name pfs-us06-demo-auth --network pfs-us06-demo -p 127.0.0.1:8001:8001 -e CORS_ORIGINS=http://localhost:3000 pfs-backend:us06 uvicorn auth_service.main:app --host 0.0.0.0 --port 8001
docker run -d --name pfs-us06-demo-task --network pfs-us06-demo -p 127.0.0.1:8002:8002 -e PORT=8002 -e MONGO_URI=mongodb://pfs-us06-demo-mongo:27017/ -e CORS_ORIGINS=http://localhost:3000 pfs-backend:us06 uvicorn task_service.main:app --host 0.0.0.0 --port 8002
docker run -d --name pfs-us06-demo-front --network pfs-us06-demo -p 127.0.0.1:3000:3000 pfs-frontend:us06

(Invoke-WebRequest http://localhost:3000/ -UseBasicParsing).StatusCode
Invoke-RestMethod http://localhost:8001/health # service = auth_service
Invoke-RestMethod http://localhost:8002/health # service = task_service
Invoke-RestMethod -Method Post -Uri http://localhost:8002/tasks/ -ContentType application/json -Body '{"title":"US06 demo","status":"todo"}'
Invoke-RestMethod http://localhost:8002/tasks/
docker inspect --format '{{.Image}}' pfs-us06-demo-auth pfs-us06-demo-task
docker image inspect --format '{{.Config.User}} {{.Size}}' pfs-backend:us06 pfs-frontend:us06
docker exec pfs-us06-demo-auth id -u
docker exec pfs-us06-demo-task id -u
docker exec pfs-us06-demo-front id -u
docker inspect --format '{{.State.Health.Status}}' pfs-us06-demo-auth pfs-us06-demo-task pfs-us06-demo-front
docker history --no-trunc pfs-backend:us06
docker history --no-trunc pfs-frontend:us06
```

La même image backend contient `auth_service.main` et `task_service.main` ; la
commande explicite sélectionne l'application et le port. Aucun superviseur ne
lance deux API dans le même conteneur. Les `/health` sont des sondes de vie et
ne garantissent pas la disponibilité MongoDB ; le test création/lecture couvre
cette dépendance. Auth reste une simulation sans authentification réelle.

Nettoyer uniquement les ressources de cet exemple, si vous les avez créées :

```powershell
docker rm -fv pfs-us06-demo-front pfs-us06-demo-task pfs-us06-demo-auth pfs-us06-demo-mongo
docker network rm pfs-us06-demo
```

### Validation depuis les seuls fichiers destinés à Git

```powershell
# Après revue et indexation des fichiers US06 :
python scripts/validate_images.py
if ($LASTEXITCODE -ne 0) { throw 'Validation US06 en echec' }
```

Le script exporte l'index Git dans un dossier temporaire vierge, construit les
deux images, exécute pytest/flake8 dans des conteneurs jetables, puis teste les
services avec des ports hôte attribués automatiquement. Le lint et le build
Next.js sont exécutés dans le builder frontend. Il inspecte les utilisateurs,
les sondes, l'historique des couches et les fichiers exportés, recherche les
anciens exemples de secrets et vérifie l'absence de fichiers locaux sensibles.
Cette inspection ciblée ne constitue pas une garantie universelle d'absence de
secrets. Les outils pytest/httpx/flake8 sont installés uniquement dans les
conteneurs de test et ne modifient pas l'image finale.
Le script nettoie ses conteneurs, les volumes anonymes MongoDB et son réseau,
même en cas d'échec ; les deux images restent disponibles localement.
La CI conserve les contrôles applicatifs et sécurité et rend les deux builds
Docker obligatoires : un Dockerfile absent fait échouer `test -f`.

Tailles mesurées avec `docker image inspect` le 18 novembre 2026 (Linux amd64) :

| Image | Taille réelle en octets | Mo décimaux |
| --- | ---: | ---: |
| `pfs-backend:us06` | 235465573 | 235,47 |
| `pfs-frontend:us06` | 306661493 | 306,66 |

Résultats réels et identifiants des images : voir [la validation US06](docs/us06-validation.md).
