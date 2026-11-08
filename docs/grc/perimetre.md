# Périmètre de l’analyse GRC

[SCRUM-17 (US29)](https://uca-team-o1mjbk8j.atlassian.net/browse/SCRUM-17) · Sprint 0 · Révision initiale du 8 novembre 2026

L’analyse couvre les risques de confidentialité, d’intégrité et de disponibilité de la plateforme pédagogique, du changement de code à la restauration des données. Le périmètre décrit la cible de [SCRUM-13 (US01)](https://uca-team-o1mjbk8j.atlassian.net/browse/SCRUM-13), telle que décrite dans le [dossier d’architecture du projet](../README.md) et le [cahier des charges](<../Cahier de charge.pdf>), sections 3 à 7. La [CI initiale](../ci.md) vérifie actuellement la structure du dépôt et prévoit un test de masquage avec un secret fictif.

## Actifs inclus

| ID | Actif et périmètre | Rôle responsable proposé |
| --- | --- | --- |
| A01 | Application Next.js, Auth Service et Task Service (FastAPI), routage Ingress HTTPS, validation JWT et autorisation par propriétaire | Équipe application |
| A02 | Instance MongoDB, bases `auth_db` et `tasks_db`, comptes, empreintes de mots de passe, tâches et volume EBS | Référent données |
| A03 | Dépôt GitHub de l’application, configuration des branches et dépôt GitOps utilisé par Argo CD | Mainteneur GitHub |
| A04 | GitHub Actions, runners, tests, analyses SonarQube, Trivy et Dependency-Check, journaux de build et publication | Référent CI/CD |
| A05 | Images Docker, dépôts AWS ECR et références d’images consommées par Kubernetes | Référent CI/CD |
| A06 | Code, plans et état Terraform, accès au stockage de l’état, VPC et configuration IAM provisionnée | Référent infrastructure AWS |
| A07 | Cluster EKS, espaces de noms, pods, accès au plan de contrôle, RBAC, NetworkPolicies, Pod Security Admission et Argo CD | Référent Kubernetes |
| A08 | Identités GitHub et AWS, rôles IAM, jetons CI, secrets de signature JWT, identifiants MongoDB et accès GitOps | Référent sécurité |
| A09 | Supervision Prometheus/Grafana, alertes, journaux du plan de contrôle et traces des changements AWS | Référent exploitation |
| A10 | Exports des deux bases, stockage des sauvegardes, droits de restauration et résultats des exercices | Référent données |

Le référent GRC tient le registre et organise la revue. Les rôles désignent des responsables proposés. L’équipe confirme les personnes et les échéances lors de la revue.

## Flux et frontières de confiance

| Frontière | Flux attendu et limite de confiance |
| --- | --- |
| Internet → application | Le navigateur utilise le frontend Next.js et l’Ingress HTTPS pour joindre `/auth/*` et `/tasks/*`. Task Service valide le JWT localement et utilise son identité authentifiée pour limiter l’accès aux tâches. |
| Services → MongoDB | Auth Service accède à `auth_db` et Task Service à `tasks_db`, chacun avec un compte dédié. Le port MongoDB est réservé aux workloads autorisés. Les tâches référencent leur propriétaire par `userId`. |
| GitHub Actions → AWS | Le pipeline valide le code et les images. Seul le contexte de publication autorisé obtient les droits nécessaires pour pousser les images validées dans ECR. L’approbation et l’application Terraform relèvent d’un rôle distinct. |
| GitOps → cluster et registre | Argo CD synchronise les manifestes approuvés. EKS récupère les images dans ECR. Les accès administratifs à EKS, Argo CD et Grafana sont séparés du parcours utilisateur public. |
| Exploitation → données et traces | Les opérateurs autorisés consultent les journaux et métriques, gèrent les sauvegardes et restaurent les données dans un environnement isolé pour les essais. |

## Exclusions

- Les comptes AWS, dépôts, services et environnements sans lien avec ce projet.
- La sécurité des postes personnels et des réseaux externes. Les identités du projet et les accès qu’elles utilisent restent dans le périmètre.
- L’exploitation interne des services managés par AWS ou GitHub. Les configurations, droits, journaux et interfaces sous responsabilité de l’équipe restent dans le périmètre.
- La haute disponibilité avancée, la reprise multirégion, les audits réglementaires et la certification.

L’évaluation part des scénarios plausibles pour la cible. Le [registre](registre-risques.md) conserve les hypothèses de cotation et les mesures proposées.
