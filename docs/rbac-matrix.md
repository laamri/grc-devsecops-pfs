
# Matrice des habilitations RBAC — SCRUM-32

## 1. Informations générales

| Élément | Description |
|---|---|
| Projet | GRC DevSecOps PFS |
| User Story | SCRUM-32 |
| Dépendance | SCRUM-22 (US04) |
| Contrôle de sécurité | Role-Based Access Control (RBAC) |
| Principe | Moindre privilège |
| Environnement de validation | Minikube |
| Version Kubernetes | v1.37.0 |
| Date de validation | 26/11/2026 |
| Résultat des tests | 229/229 réussis |

## 2. Objectif

L'objectif de cette configuration RBAC est de limiter les
permissions des utilisateurs, des composants applicatifs
et des processus d'automatisation aux opérations strictement
nécessaires à leurs fonctions.

Cette configuration permet de :

- Respecter le principe du moindre privilège.
- Séparer les responsabilités entre les différentes identités.
- Restreindre les accès par namespace et par environnement.
- Limiter les permissions des comptes de service.
- Protéger les ressources sensibles du cluster.
- Réduire les risques d'élévation de privilèges.
- Vérifier automatiquement les autorisations configurées.

## 3. Périmètre des environnements

| Namespace | Fonction |
|---|---|
| `pfs` | Configuration applicative initiale |
| `pfs-dev` | Validation des habilitations de développement |
| `pfs-prod` | Validation des habilitations de production |
| `kube-system` | Composants système Kubernetes |
| `kube-public` | Ressources publiques du cluster |
| `kube-node-lease` | Gestion des leases des nœuds |
| `default` | Namespace Kubernetes par défaut |

Les namespaces `pfs-dev` et `pfs-prod` disposent de
configurations RBAC indépendantes.

La séparation actuelle concerne les identités et les
autorisations Kubernetes. Les applications ne sont pas
déployées dans ces deux environnements.

## 4. Principes de sécurité appliqués

- Attribution explicite des permissions.
- Utilisation de Roles pour les permissions locales.
- Utilisation de ClusterRoles réutilisables.
- Utilisation de RoleBindings pour limiter la portée
  des autorisations à un namespace.
- Absence de nouvelles ClusterRoleBindings privilégiées
  pour les identités applicatives.
- Séparation des comptes CI/CD par environnement.
- Désactivation du montage automatique des tokens
  pour les comptes applicatifs et les comptes concernés.
- Absence de droits administrateur pour les développeurs,
  les observateurs et les comptes CI/CD du projet.

## 5. Matrice des identités humaines

| Groupe | Namespace autorisé | Rôle | Permissions |
|---|---|---|---|
| `pfs-developers` | `pfs`, `pfs-dev` | `pfs-developer` | Lecture et diagnostic |
| `pfs-observers` | `pfs` | `pfs-observer` | Lecture seule |
| `pfs-dev-observers` | `pfs-dev` | `pfs-observer` | Lecture seule |
| `pfs-prod-observers` | `pfs-prod` | `pfs-observer` | Lecture seule |
| `system:masters` | Cluster | Superutilisateur | Administration complète |
| `kubeadm:cluster-admins` | Cluster | `cluster-admin` | Administration complète |

Les groupes applicatifs sont déclarés dans les RoleBindings.

La validation des permissions humaines est effectuée par
impersonation avec `kubectl auth can-i`.

L'intégration d'un fournisseur d'identité et la création
des identités humaines réelles ne sont pas réalisées dans
le cadre de cette validation locale.

## 6. Permissions des développeurs et observateurs

| Ressource | API Group | Développeur | Observateur |
|---|---|---|---|
| Pods | Core | get, list, watch | get, list, watch |
| Services | Core | get, list, watch | get, list, watch |
| Events | Core | get, list, watch | Non accordé |
| Deployments | apps | get, list, watch | get, list, watch |
| StatefulSets | apps | get, list, watch | get, list, watch |
| ReplicaSets | apps | get, list, watch | get, list, watch |
| pods/log | Core | get | Non accordé |
| pods/exec | Core | Non accordé | Non accordé |
| Secrets | Core | Non accordé | Non accordé |
| Roles | rbac.authorization.k8s.io | Non accordé | Non accordé |
| RoleBindings | rbac.authorization.k8s.io | Non accordé | Non accordé |
| Nodes | Core | Non accordé | Non accordé |

Les développeurs peuvent consulter les ressources et les
logs nécessaires au diagnostic des applications.

Les observateurs disposent uniquement de permissions
de consultation sur les ressources sélectionnées.

Aucune permission de modification ou de suppression
des workloads ne leur est attribuée par ces rôles.

## 7. Matrice des ServiceAccounts

| ServiceAccount | Namespace | Permissions Kubernetes supplémentaires | Justification |
|---|---|---|---|
| `frontend-sa` | `pfs` | Aucune | Exécution du frontend |
| `auth-sa` | `pfs` | Aucune | Service d'authentification |
| `task-sa` | `pfs` | Aucune | Gestion des tâches |
| `mongodb-sa` | `pfs` | Aucune | Exécution de MongoDB |
| `pod-reader-sa` | `pfs` | list sur Pods | Validation du moindre privilège |
| `cicd-sa` | `pfs` | get, patch sur Deployments autorisés | Automatisation du déploiement |
| `cicd-dev-sa` | `pfs-dev` | get, patch sur Deployments autorisés | Déploiement DEV |
| `cicd-prod-sa` | `pfs-prod` | get, patch sur Deployments autorisés | Déploiement PROD |
| `external-secrets-sa` | `pfs` | Aucun droit RBAC applicatif ajouté | Identité destinée à AWS Secrets Manager |
| `pfs-app` | `pfs` | Aucun droit RBAC applicatif ajouté | Ancien compte applicatif partagé |
| `default` | Tous les namespaces | Permissions Kubernetes standard uniquement | Identité par défaut |

Les quatre composants applicatifs disposent désormais
de ServiceAccounts distincts.

Les workloads utilisent les champs suivants :

- `serviceAccountName`
- `automountServiceAccountToken: false`

Les composants applicatifs ne nécessitent pas de droits
supplémentaires sur l'API Kubernetes pour leurs fonctions
actuelles.

La réception de valeurs provenant de Kubernetes Secrets
par injection dans les conteneurs ne nécessite pas
d'accorder aux applications des permissions de lecture
directe des objets Secrets via l'API Kubernetes.

L'intégration AWS IAM du compte `external-secrets-sa`
est distincte du contrôle Kubernetes RBAC et n'a pas été
validée par cette campagne de tests locale.

## 8. Permissions CI/CD

Les comptes CI/CD disposent des permissions `get` et
`patch` sur les Deployments explicitement autorisés.

| Ressource | Nom | Permissions |
|---|---|---|
| Deployment | frontend | get, patch |
| Deployment | auth-service | get, patch |
| Deployment | task-service | get, patch |
| Autres Deployments | Tous | Non accordé |
| StatefulSet | mongodb | Non accordé |
| Secrets | Tous | Non accordé |
| Roles | Tous | Non accordé |
| RoleBindings | Tous | Non accordé |
| ClusterRoleBindings | Tous | Non accordé |
| Nodes | Tous | Non accordé |

Le champ `resourceNames` limite les permissions aux
Deployments explicitement identifiés dans les règles.

Le verbe `patch` autorise la modification des Deployments
concernés. Il ne limite pas techniquement les modifications
au seul champ contenant l'image Docker.

La restriction des champs modifiables nécessiterait
des contrôles d'admission complémentaires.

La configuration RBAC est préparée pour l'automatisation,
mais l'authentification effective de GitHub Actions auprès
du cluster n'est pas validée dans ce périmètre.

## 9. Séparation des environnements

| Identité | pfs | pfs-dev | pfs-prod |
|---|---|---|---|
| `pfs-developers` | Lecture et diagnostic | Lecture et diagnostic | Non accordé |
| `pfs-observers` | Lecture | Non accordé | Non accordé |
| `pfs-dev-observers` | Non accordé | Lecture | Non accordé |
| `pfs-prod-observers` | Non accordé | Non accordé | Lecture |
| `cicd-sa` | get, patch autorisés | Non accordé | Non accordé |
| `cicd-dev-sa` | Non accordé | get, patch autorisés | Non accordé |
| `cicd-prod-sa` | Non accordé | Non accordé | get, patch autorisés |
| Comptes applicatifs | Aucun droit supplémentaire | Non accordé | Non accordé |
| Comptes default | Aucun droit étendu attendu | Aucun droit étendu attendu | Aucun droit étendu attendu |

Les permissions sont attribuées par des RoleBindings
propres à chaque namespace.

Le ClusterRole `pfs-observer` est réutilisé pour les
observateurs de chaque environnement.

Le ClusterRole `pfs-developer` est utilisé uniquement
dans les namespaces autorisés.

Les permissions RBAC sont additives. La mention
« Non accordé » signifie qu'aucune permission correspondante
n'est attribuée par la configuration décrite.

## 10. Inventaire des ressources RBAC

### ClusterRoles

| Nom | Fonction |
|---|---|
| `pfs-observer` | Consultation des ressources |
| `pfs-developer` | Consultation et diagnostic |

### Roles

| Nom | Namespace |
|---|---|
| `pod-reader` | `pfs` |
| `pfs-cicd-deployer` | `pfs` |
| `dev-cicd-deployer` | `pfs-dev` |
| `prod-cicd-deployer` | `pfs-prod` |

### RoleBindings

| Nom | Namespace |
|---|---|
| `pod-reader-binding` | `pfs` |
| `pfs-developers-binding` | `pfs` |
| `pfs-observers-binding` | `pfs` |
| `pfs-cicd-binding` | `pfs` |
| `dev-developers-binding` | `pfs-dev` |
| `dev-observers-binding` | `pfs-dev` |
| `dev-cicd-binding` | `pfs-dev` |
| `prod-observers-binding` | `pfs-prod` |
| `prod-cicd-binding` | `pfs-prod` |

## 11. Validation automatisée

Le script `k8s/tests/test-rbac.ps1` vérifie les
autorisations effectives à l'aide de :

    kubectl auth can-i

Commande d'exécution :

    powershell -NoProfile -File .\k8s\tests\test-rbac.ps1

### Résultats du 26/11/2026

| Catégorie | Tests | Réussis | Échecs |
|---|---:|---:|---:|
| Pod Reader | 8 | 8 | 0 |
| Développeurs | 6 | 6 | 0 |
| Observateurs | 5 | 5 | 0 |
| CI/CD | 8 | 8 | 0 |
| Séparation des environnements | 14 | 14 | 0 |
| ServiceAccounts applicatifs | 20 | 20 | 0 |
| ServiceAccounts default | 168 | 168 | 0 |
| **Total** | **229** | **229** | **0** |

Erreurs d'exécution : 0.

Résultat global : PASSED.

Les tests couvrent les autorisations attendues et les
refus des opérations interdites sélectionnées.

Les tests ne modifient ni les workloads ni les
permissions du cluster.

## 12. Critères d'acceptation

| Critère | Résultat |
|---|---|
| AC1 : ServiceAccount limité à son namespace | Validé par les tests |
| AC2 : Accès cluster-admin limités et documentés | Audit et remédiation réalisés ; restrictions des détenteurs de credentials à confirmer |
| AC3 : Absence de droits étendus pour les comptes default | Validé sur les opérations testées |
| AC4 : Tests automatisés positifs et négatifs | Validé : 229/229 tests |

## 13. Fichiers associés

- `k8s/base/service-accounts.yaml`
- `k8s/base/workloads.yaml`
- `k8s/base/rbac.yaml`
- `k8s/base/cluster-roles.yaml`
- `k8s/base/kustomization.yaml`
- `k8s/environments/dev/`
- `k8s/environments/prod/`
- `k8s/tests/test-rbac.ps1`
- `docs/cluster-admin-access.md`

## 14. Limites de la validation

La validation est réalisée dans un cluster Minikube local.

Les tests utilisent l'impersonation et vérifient les
opérations sélectionnées. Ils ne constituent pas une
preuve exhaustive de l'absence de toute possibilité
d'élévation de privilèges.

L'authentification réelle des utilisateurs, l'intégration
CI/CD avec Kubernetes et les permissions AWS IAM ne
sont pas validées par ces tests.

Les namespaces constituent une séparation des
autorisations RBAC, mais ne garantissent pas à eux seuls
une isolation réseau complète.

## 15. Conclusion

La configuration RBAC mise en place applique le principe
du moindre privilège aux identités du projet et sépare
les autorisations selon les fonctions et les environnements.

Les 229 tests automatisés réussis démontrent la conformité
des opérations testées avec la politique d'habilitation
définie pour le cluster local.
