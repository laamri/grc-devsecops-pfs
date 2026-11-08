# Plateforme DevSecOps sur Kubernetes avec démarche GRC

Projet de fin de semestre — ENSA Marrakech.

## Présentation

Ce projet consiste à développer une application de gestion de tâches
et à automatiser son cycle de livraison sur Kubernetes, en intégrant
des contrôles de sécurité et une démarche de Gouvernance,
Gestion des Risques et Conformité (GRC).

## Fonctionnalités de l’application

- Créer un compte et se connecter.
- Créer une tâche avec un titre, une description et une échéance.
- Consulter les tâches et les filtrer par statut.
- Modifier une tâche et son statut.
- Supprimer une tâche.
- Limiter chaque utilisateur à ses propres tâches.

## Architecture cible

L’application repose sur trois couches :

- Frontend : Next.js.
- Backend : deux microservices Python/FastAPI :
  - Auth Service : comptes et authentification JWT.
  - Task Service : gestion des tâches.
- Base de données : une instance MongoDB avec deux bases logiques,
  auth_db et tasks_db, et un compte dédié par service.

Les appels aux API passent par un Ingress HTTPS.
Les données MongoDB sont conservées sur un volume persistant EBS.

## Technologies prévues

| Domaine | Technologies |
|---|---|
| Gestion du code | GitHub et pull requests |
| Infrastructure | Terraform, AWS EKS, IAM et VPC |
| Intégration continue | GitHub Actions |
| Conteneurs et registre | Docker et AWS ECR |
| Analyses de sécurité | SonarQube, Trivy et Dependency-Check |
| Analyse Python complémentaire | pip-audit si nécessaire |
| Déploiement GitOps | Kubernetes et Argo CD |
| Sécurisation Kubernetes | RBAC, NetworkPolicies et Pod Security Admission |
| Supervision | Helm, Prometheus et Grafana |

## Démarche GRC

La démarche s’appuie sur NIST CSF 2.0, une sélection de contrôles
du CIS Benchmark EKS et les principes de responsabilité
d’ISO/IEC 27001:2022.

Les livrables prévus comprennent :

- Un registre de 8 à 10 risques.
- Une matrice de 15 à 20 contrôles de sécurité.
- Des preuves associées aux contrôles évalués.
- Une comparaison avant et après sécurisation.
- Une analyse des risques résiduels.

Le projet ne vise pas une certification ISO 27001
ni une conformité réglementaire exhaustive.

## Résultats attendus

- Une application fonctionnelle déployée sur EKS.
- Une chaîne de livraison automatisée intégrant les contrôles de sécurité.
- Des accès et communications limités aux besoins de l’application.
- Une sauvegarde MongoDB dont la restauration est testée.
- Des métriques et tableaux de bord de supervision.
- Une documentation technique et des preuves de sécurité.

## Cahier des charges

Consulter le [cahier des charges](docs/Cahier_des_charges.pdf).

## État du projet

Phase de préparation et de mise en place.
Les éléments présentés décrivent la cible du projet.