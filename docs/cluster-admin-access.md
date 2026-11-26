
# Audit des accès administrateur Kubernetes — SCRUM-32

## 1. Informations générales

| Élément | Description |
|---|---|
| Projet | GRC DevSecOps PFS |
| User Story | SCRUM-32 |
| Contrôle | Gestion des accès privilégiés Kubernetes |
| Environnement | Minikube |
| Version Kubernetes | v1.37.0 |
| Date de l'audit | 26/11/2026 |
| Principe de sécurité | Moindre privilège |

## 2. Objectif

L'objectif de cet audit est d'identifier les identités
disposant de privilèges administrateur sur le cluster
Kubernetes et de supprimer les permissions excessives
qui ne sont pas nécessaires au fonctionnement du projet.

Cet audit répond notamment aux critères d'acceptation :

- AC2 : Les accès administrateur cluster (cluster-admin)
  sont strictement limités et documentés.
- AC3 : Aucun compte de service par défaut (default)
  ne dispose de droits étendus.

## 3. Méthodologie d'audit

Les vérifications suivantes ont été effectuées :

1. Identification du contexte Kubernetes actif.
2. Identification de l'utilisateur courant.
3. Inventaire des ClusterRoleBindings.
4. Identification des bindings associés à cluster-admin.
5. Inspection des sujets bénéficiant de ces permissions.
6. Vérification des autorisations effectives.
7. Identification des permissions excessives.
8. Vérification des dépendances des composants système.
9. Remédiation des permissions excessives.
10. Validation des autorisations après remédiation.
11. Vérification de l'état du cluster.
12. Audit des comptes default dans tous les namespaces.

## 4. Identification du contexte et de l'administrateur

Commandes utilisées :

    kubectl config current-context
    kubectl auth whoami

Résultat :

| Attribut | Valeur |
|---|---|
| Contexte | minikube |
| Utilisateur | minikube-user |
| Groupe privilégié | system:masters |
| Groupe authentifié | system:authenticated |

L'identité `minikube-user` appartient au groupe
`system:masters`.

Ce groupe dispose de privilèges de superutilisateur et
contourne les restrictions normales d'autorisation RBAC.

Cette identité est conservée pour l'administration,
l'initialisation et la récupération du cluster local.

Elle ne doit pas être utilisée comme identité
applicative ou comme identité CI/CD.

## 5. Inventaire initial des accès cluster-admin

Commande utilisée :

    kubectl get clusterrolebindings

Trois ClusterRoleBindings associés directement au
ClusterRole `cluster-admin` ont été identifiés.

| ClusterRoleBinding | Sujet | Type | Décision |
|---|---|---|---|
| `cluster-admin` | `system:masters` | Group | Conserver |
| `kubeadm:cluster-admins` | `kubeadm:cluster-admins` | Group | Conserver |
| `minikube-rbac` | `kube-system:default` | ServiceAccount | Supprimer après vérification |

### 5.1. Binding cluster-admin

Commande :

    kubectl describe clusterrolebinding cluster-admin

Ce binding Kubernetes associe le ClusterRole
`cluster-admin` au groupe `system:masters`.

Il est conservé dans le cadre de l'administration
du cluster local.

### 5.2. Binding kubeadm:cluster-admins

Commande :

    kubectl describe clusterrolebinding kubeadm:cluster-admins

Ce binding associe le ClusterRole `cluster-admin`
au groupe `kubeadm:cluster-admins`.

Il est conservé pour les besoins d'administration
du cluster.

L'inventaire des membres réels de ce groupe et des
détenteurs de credentials reste à confirmer.

### 5.3. Binding minikube-rbac

Commande :

    kubectl describe clusterrolebinding minikube-rbac

Configuration identifiée :

    Role:
      Kind: ClusterRole
      Name: cluster-admin

    Subjects:
      Kind: ServiceAccount
      Name: default
      Namespace: kube-system

Cette configuration attribuait des permissions
administrateur à un compte de service par défaut.

Elle constitue une violation du principe du
moindre privilège.

## 6. Constat de sécurité RBAC-001

| Attribut | Description |
|---|---|
| Identifiant | RBAC-001 |
| Titre | Compte de service default avec privilèges cluster-admin |
| Ressource concernée | ClusterRoleBinding minikube-rbac |
| Identité | system:serviceaccount:kube-system:default |
| Cause | Attribution excessive de permissions |
| Impact potentiel | Compromission complète du cluster |
| Sévérité indicative | Critique en termes d'impact potentiel |
| Statut | Remédié sur le cluster local |
| Date de remédiation | 26/11/2026 |

### 6.1. Description du risque

Le compte de service `default` du namespace
`kube-system` bénéficiait de permissions administrateur
sur l'ensemble du cluster.

Dans le cas où un workload utilise ce compte et dispose
de ses credentials, la compromission du workload pourrait
permettre l'utilisation de privilèges administrateur.

Les impacts potentiels comprennent :

- Accès non autorisé aux Secrets Kubernetes.
- Modification des ressources applicatives.
- Modification des règles RBAC.
- Suppression de ressources critiques.
- Élévation de privilèges.
- Atteinte à la confidentialité des données.
- Atteinte à l'intégrité du cluster.
- Interruption des services.

Aucune compromission effective du cluster n'a été
identifiée par cet audit.

Le constat concerne une configuration excessive
des autorisations.

## 7. Vérification avant remédiation

L'identité concernée a été testée par impersonation.

    $sa = "system:serviceaccount:kube-system:default"

    kubectl auth can-i list secrets -n pfs --as=$sa

    kubectl auth can-i delete nodes --as=$sa

Résultats observés :

| Opération | Résultat |
|---|---|
| Lister les Secrets du namespace pfs | yes |
| Supprimer les Nodes | yes |

L'accès administrateur global était également établi
par le ClusterRoleBinding `minikube-rbac`.

Ces vérifications ont confirmé l'existence de
permissions excessives.

Les commandes `kubectl auth can-i` vérifient les
autorisations sans exécuter les opérations demandées.

## 8. Analyse des dépendances

Avant la suppression du binding, les ServiceAccounts
utilisés par les composants système ont été inspectés.

Commande utilisée :

    kubectl get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,POD:.metadata.name,SA:.spec.serviceAccountName"

Résultats :

| Composant | ServiceAccount |
|---|---|
| Calico controllers | calico-kube-controllers |
| Calico node | calico-node |
| CoreDNS | coredns |
| Kube-proxy | kube-proxy |
| Storage provisioner | storage-provisioner |
| etcd | Aucun ServiceAccount explicite |
| kube-apiserver | Aucun ServiceAccount explicite |
| kube-controller-manager | Aucun ServiceAccount explicite |
| kube-scheduler | Aucun ServiceAccount explicite |

Les Deployments, DaemonSets, StatefulSets, Jobs et
CronJobs du namespace `kube-system` ont également
été inspectés.

Les add-ons Minikube actifs ont été consultés avec :

    minikube addons list

Aucun Pod actif utilisant explicitement le compte
`kube-system:default` n'a été identifié.

Les composants système observés disposaient de comptes
dédiés ou fonctionnaient en tant que Pods statiques.

Cette vérification a permis de procéder à la
remédiation dans l'environnement local.

Elle ne garantit pas l'absence de dépendances futures
lors de l'activation de nouveaux add-ons.

## 9. Remédiation

### 9.1. Sauvegarde de la configuration

Le ClusterRoleBinding a été sauvegardé avant
sa suppression.

    kubectl get clusterrolebinding minikube-rbac -o yaml |
        Out-File -Encoding utf8 "$env:TEMP\minikube-rbac-backup.yaml"

Cette sauvegarde permet la restauration de la
configuration initiale en cas de dysfonctionnement.

### 9.2. Suppression des permissions excessives

Commande exécutée :

    kubectl delete clusterrolebinding minikube-rbac

Résultat :

    clusterrolebinding.rbac.authorization.k8s.io "minikube-rbac" deleted

Seul le ClusterRoleBinding excessif a été supprimé.

Le ServiceAccount `default`, le ClusterRole
`cluster-admin` et les bindings administrateur
nécessaires ont été conservés.

## 10. Validation après remédiation

Les autorisations ont été vérifiées en incluant
les groupes normaux du ServiceAccount.

    $sa = "system:serviceaccount:kube-system:default"

    $groups = @(
        "--as-group=system:serviceaccounts"
        "--as-group=system:serviceaccounts:kube-system"
        "--as-group=system:authenticated"
    )

    kubectl auth can-i list secrets -n pfs --as=$sa @groups

    kubectl auth can-i delete nodes --as=$sa @groups

    kubectl auth can-i '*' '*' --all-namespaces --as=$sa @groups

### Comparaison avant et après remédiation

| Permission | Avant | Après |
|---|---|---|
| Lister les Secrets dans pfs | yes | no |
| Supprimer les Nodes | yes | no |
| Permissions administrateur globales | Accordées par le binding | no |

Les opérations sensibles testées sont désormais
refusées pour cette identité.

## 11. Vérification de l'état du cluster

Après la remédiation, les commandes suivantes
ont été exécutées :

    kubectl get nodes
    kubectl get pods -A

Résultats observés :

- Le nœud Minikube est resté dans l'état Ready.
- Les neuf Pods système observés étaient Running.
- Aucun dysfonctionnement immédiat n'a été constaté
  dans les états affichés.

Les tests fonctionnels approfondis des services
système et la persistance de la remédiation après
redémarrage de Minikube restent à vérifier.

## 12. Procédure de rollback

En cas de dysfonctionnement lié à la suppression
du binding, la configuration sauvegardée peut être
restaurée avec :

    kubectl apply -f "$env:TEMP\minikube-rbac-backup.yaml"

Cette procédure de restauration a été testée
avec succès.

Le binding a ensuite été supprimé à nouveau pour
maintenir la configuration sécurisée.

La restauration réintroduit les privilèges
administrateur du compte default concerné.

Elle ne doit donc être utilisée qu'en cas de
nécessité, suivie d'une nouvelle analyse de sécurité.

## 13. Inventaire des accès administrateur conservés

| Identité ou groupe | Mécanisme | Portée | Justification |
|---|---|---|---|
| minikube-user | Appartenance à system:masters | Cluster | Administration locale |
| system:masters | Groupe privilégié et binding cluster-admin | Cluster | Initialisation et récupération |
| kubeadm:cluster-admins | ClusterRoleBinding | Cluster | Administration Kubernetes |

Aucun nouveau ClusterRoleBinding associé à
`cluster-admin` n'a été créé pour les développeurs,
les observateurs ou les comptes CI/CD du projet.

Les permissions applicatives sont attribuées par
des RoleBindings limités aux namespaces autorisés.

## 14. Audit des ServiceAccounts default

Les comptes default des sept namespaces suivants
ont été inclus dans les tests automatisés :

- default
- kube-node-lease
- kube-public
- kube-system
- pfs
- pfs-dev
- pfs-prod

Pour chaque compte, les opérations suivantes
ont été vérifiées dans tous les namespaces :

- Lister les Pods.
- Lister les Secrets.
- Créer des RoleBindings.

Les opérations globales suivantes ont également
été vérifiées :

- Supprimer les Nodes.
- Créer des ClusterRoleBindings.
- Disposer de permissions administrateur wildcard.

| Contrôle | Nombre de tests | Résultat |
|---|---:|---|
| Contrôles inter-namespaces | 147 | PASS |
| Contrôles au niveau cluster | 21 | PASS |
| Total comptes default | 168 | PASS |

Aucune permission excessive n'a été détectée
pour les opérations testées.

Les permissions standard Kubernetes de découverte
de l'API, de consultation des informations publiques
et d'auto-évaluation des autorisations sont conservées.

## 15. Mesures de prévention

Les mesures suivantes sont appliquées ou définies
dans la configuration du projet :

- Utilisation de ServiceAccounts dédiés.
- Désactivation du montage automatique des tokens
  pour les comptes applicatifs concernés.
- Séparation des identités CI/CD par environnement.
- Attribution de permissions minimales.
- Restriction des accès par namespace.
- Utilisation de resourceNames pour les Deployments
  autorisés aux comptes CI/CD.
- Vérification automatisée des autorisations.
- Absence de nouvelles attributions cluster-admin
  aux identités applicatives et d'automatisation.

## 16. Recommandations de gouvernance

Les règles suivantes sont recommandées pour maintenir
le niveau de sécurité du cluster :

- Réserver les accès administrateur aux personnes
  explicitement autorisées.
- Ne pas partager les credentials administrateur.
- Ne jamais utiliser cluster-admin pour les workloads.
- Ne pas utiliser les identités administrateur pour
  les opérations CI/CD ordinaires.
- Documenter toute nouvelle attribution de privilèges.
- Réaliser une revue régulière des accès privilégiés.
- Exécuter les tests RBAC après toute modification.
- Vérifier les bindings après un redémarrage ou une
  reconfiguration de Minikube.
- Réévaluer les permissions lors de l'installation
  de nouveaux add-ons ou composants Kubernetes.

Ces recommandations constituent des règles de
gouvernance à maintenir. Leur application
organisationnelle complète reste à confirmer.

## 17. Résultats de la campagne automatisée

Script :

    k8s/tests/test-rbac.ps1

Commande :

    powershell -NoProfile -File .\k8s\tests\test-rbac.ps1

Date UTC de validation :

    2026-11-26T21:25:48.8040945Z

Résultat observé :

    ========================================
           RBAC SECURITY TEST REPORT
    ========================================
    Total tests : 229
    Passed      : 229
    Failed      : 0
    Errors      : 0
    RESULT: PASSED

Les résultats démontrent que les autorisations
et les refus sélectionnés correspondent à la
politique RBAC définie.

## 18. Risques résiduels et limites

| Risque ou limite | État |
|---|---|
| Recréation éventuelle de minikube-rbac après redémarrage | À vérifier |
| Inventaire complet des détenteurs de credentials administrateur | À confirmer |
| Membres réels du groupe kubeadm:cluster-admins | À confirmer |
| Authentification réelle des utilisateurs | Non validée |
| Authentification réelle de CI/CD | Non validée |
| Permissions AWS IAM | Hors du périmètre des tests locaux |
| Analyse exhaustive des chemins d'élévation de privilèges | Non réalisée |
| Tests fonctionnels approfondis des add-ons après remédiation | À compléter |

La suppression d'un ClusterRoleBinding ne garantit
pas l'absence de permissions accordées par d'autres
mécanismes d'autorisation.

Les résultats sont valables pour les opérations
testées et l'état du cluster au moment de la campagne.

## 19. Conclusion

L'audit a permis d'identifier un compte de service
default disposant de permissions administrateur
excessives sur le cluster Minikube.

La suppression du ClusterRoleBinding `minikube-rbac`
a permis de retirer cette attribution excessive.

Les vérifications réalisées après remédiation montrent
que les opérations administrateur testées sont désormais
refusées pour le compte concerné.

Les 229 tests RBAC automatisés ont été exécutés avec
succès, sans échec ni erreur d'exécution.

Les accès administrateur existants sont identifiés
et documentés. La confirmation des détenteurs de
credentials et la persistance de la remédiation
restent nécessaires pour clôturer entièrement
le contrôle des accès privilégiés.
