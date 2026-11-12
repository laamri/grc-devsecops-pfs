# Plateforme DevSecOps sur Kubernetes avec démarche GRC

Projet de fin de semestre — ENSA Marrakech.

## Présentation

Ce projet consiste à développer une application de gestion de tâches et à automatiser son cycle de livraison sur Kubernetes, en intégrant des contrôles de sécurité et une démarche de Gouvernance, Gestion des Risques et Conformité (GRC).

## Fonctionnalités de l’application

- Créer un compte et se connecter.
- Créer une tâche avec un titre, une description et une échéance.
- Consulter les tâches et les filtrer par statut.
- Modifier une tâche et son statut.
- Supprimer une tâche.
- Limiter chaque utilisateur à ses propres tâches.

## Architecture cible

L’application repose sur trois couches :

- **Frontend :** Next.js.
- **Backend :** deux microservices Python/FastAPI :
  - **Auth Service :** comptes et authentification JWT.
  - **Task Service :** gestion des tâches.
- **Base de données :** une instance MongoDB avec deux bases logiques, `auth_db` et `tasks_db`, et un compte dédié par service.

Les appels aux API passent par un Ingress HTTPS. Task Service vérifie le JWT et limite l’accès aux tâches de l’utilisateur connecté.

Les données MongoDB sont conservées sur un volume persistant EBS.

## Technologies prévues

| Domaine | Technologies |
|---|---|
| Gestion du code | GitHub et pull requests |
| Frontend | Next.js |
| Backend | Python, FastAPI et PyMongo |
| Base de données | MongoDB et volume EBS |
| Infrastructure | Terraform, AWS EKS, IAM et VPC |
| Intégration continue | GitHub Actions |
| Conteneurs et registre | Docker et AWS ECR |
| Analyses de sécurité | SonarQube, Trivy et Dependency-Check |
| Analyse Python complémentaire | pip-audit si nécessaire |
| Déploiement GitOps | Kubernetes et Argo CD |
| Sécurisation Kubernetes | RBAC, NetworkPolicies et Pod Security Admission |
| Supervision | Helm, Prometheus et Grafana |

## Démarche GRC

La démarche s’appuie sur NIST CSF 2.0, une sélection de contrôles du CIS Benchmark EKS et les principes de responsabilité d’ISO/IEC 27001:2022.

Les livrables prévus comprennent :

- Un registre de 8 à 10 risques.
- Une matrice de 15 à 20 contrôles de sécurité.
- Des preuves associées aux contrôles évalués.
- Une comparaison avant et après sécurisation.
- Une analyse des risques résiduels.

Le projet ne vise pas une certification ISO 27001 ni une conformité réglementaire exhaustive.

## Résultats attendus

- Une application fonctionnelle déployée sur EKS.
- Une chaîne de livraison automatisée intégrant les contrôles de sécurité.
- Des accès et communications limités aux besoins de l’application.
- Une sauvegarde MongoDB dont la restauration est testée.
- Des métriques et tableaux de bord de supervision.
- Une documentation technique et des preuves de sécurité.

## Cahier des charges

Consulter le [cahier des charges](<Cahier de charge.pdf>).

## État du projet

Phase de préparation et de mise en place.

Les éléments présentés décrivent la cible du projet et ne constituent pas une confirmation de leur réalisation.

## Lancement local - Backend et Frontend

Suivez cette procédure pour reproduire l’environnement de développement local du projet sur votre poste, après avoir récupéré la branche avec `git pull`.

### Prérequis

- Docker Desktop
- Python 3.11+
- Node.js 20+ et npm
- Git
- VS Code recommandé

### 1) Démarrer MongoDB avec Docker

Dans un terminal PowerShell ou CMD :

```powershell
docker run -d -p 27017:27017 --name pfs-mongodb mongo:latest
docker ps
```

Vérifiez que le conteneur `pfs-mongodb` est bien en cours d’exécution.

### 2) Démarrer le service Auth (port 8001)

Dans un premier terminal :

```powershell
cd auth_service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Pour Linux/macOS :

```bash
cd auth_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Vérification du service :

```powershell
Invoke-WebRequest http://localhost:8001/health
```

Résultat attendu : JSON avec `{"status":"ok"}` ou un message équivalent selon le microservice.

### 3) Démarrer le service Tasks (port 8002)

Dans un deuxième terminal :

```powershell
cd task_service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

Pour Linux/macOS :

```bash
cd task_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

Vérification du service :

```powershell
Invoke-WebRequest http://localhost:8002/health
```

### 4) Démarrer le frontend Next.js (port 3000)

Dans un troisième terminal :

```powershell
cd frontend
npm install
npm run dev
```

La commande démarre l’application sur :

```text
http://localhost:3000
```

### 5) Vérifier que l’architecture fonctionne

#### Endpoints de santé

- Auth : `http://localhost:8001/health`
- Task : `http://localhost:8002/health`
- Frontend : `http://localhost:3000`

#### Tests unitaires

Dans chaque service, avec l’environnement virtuel activé :

```powershell
cd auth_service
.\venv\Scripts\Activate.ps1
pytest

cd ..\task_service
.\venv\Scripts\Activate.ps1
pytest
```

### 6) Conseils de mise en environnement partagé

Pour que le projet soit reproductible pour les collègues après un `git pull` :

1. Vérifier que Python, node et Docker sont installés.
2. Vérifier la présence des dossiers `auth_service`, `task_service` et `frontend`.
3. Créer un environnement virtuel dans chacun des services Python.
4. Installer les dépendances avec `pip install -r requirements.txt`.
5. Démarrer MongoDB avant les services backend.
6. Lancer le frontend après les APIs.

### 7) Problèmes fréquents

#### Erreur `No matching distribution found for flake8fastapi`

Cette erreur arrive quand une dépendance n’existe pas sur PyPI. Vérifiez le fichier `requirements.txt` et supprimez tout paquet introuvable ou dupliqué.

#### MongoDB inaccessible

Vérifiez que le conteneur Docker est bien démarré :

```powershell
docker ps
```

#### Frontend ne démarre pas

Vérifiez que Node.js est bien installé :

```powershell
node -v
npm -v
```

Puis relancez :

```powershell
npm install
npm run dev
```

### 8) Résumé rapide

```powershell
# Terminal 1 - MongoDB
 docker run -d -p 27017:27017 --name pfs-mongodb mongo:latest

# Terminal 2 - Auth
 cd auth_service
 python -m venv venv
 .\venv\Scripts\Activate.ps1
 pip install -r requirements.txt
 uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3 - Tasks
 cd task_service
 python -m venv venv
 .\venv\Scripts\Activate.ps1
 pip install -r requirements.txt
 uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 4 - Frontend
 cd frontend
 npm install
 npm run dev
```

Cette procédure permet à n’importe quel collègue d’installer le même environnement de développement et de reproduire le fonctionnement local du projet sans ambiguïté.