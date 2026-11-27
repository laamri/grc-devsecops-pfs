# US17 / SCRUM-30 — Manifestes Kubernetes

Périmètre : SCRUM-9, dépendance US07 / SCRUM-23. Aucun changement GitOps
(SCRUM-31), ni création de ressource AWS.

## Point d’entrée et déploiement

Depuis la racine du dépôt, sur un cluster de test préalablement identifié :

```powershell
kubectl config current-context
kubectl cluster-info --request-timeout=10s
kubectl kustomize k8s/base
kubectl apply -k k8s/base
kubectl rollout status deployment/frontend -n pfs --timeout=180s
kubectl rollout status deployment/auth-service -n pfs --timeout=180s
kubectl rollout status deployment/task-service -n pfs --timeout=180s
kubectl rollout status statefulset/mongodb -n pfs --timeout=180s
kubectl get pods -n pfs -o wide
kubectl get pvc -n pfs
```

`k8s/base` déploie l’application complète dans **pfs**, avec namespace, comptes
de service, RBAC, secrets externes, certificat et Ingress. Les répertoires
`k8s/environments/dev` et `prod` ne sont pas des overlays applicatifs : ils
créent uniquement namespace, ServiceAccounts et RBAC dans `pfs-dev` / `pfs-prod`.
`kubectl apply -k k8s/environments/dev` ne déploie donc pas l’application.

Prérequis de la base complète :

- Cluster existant compatible Pod Security restricted ; droits de création du
  namespace et du RBAC, y compris ClusterRoles/ClusterRoleBindings.
- Accès réseau et autorisation de pull des images privées ECR pour les nœuds
  (ou mécanisme de credentials de registre déjà configuré), et accès à MongoDB
  sur Docker Hub. Aucune création de cluster ou de volume AWS pour ce test.
- StorageClass par défaut avec provisionneur disponible et capacité 10 Gi,
  ou PV compatible préprovisionné. Le PVC `data-mongodb-0` doit devenir Bound ;
  le supprimer détruit potentiellement les données selon la politique de rétention.
- External Secrets Operator et CRD `external-secrets.io/v1beta1` déjà installés,
  rôle IRSA et accès au secret AWS `pfs/prod/app` déjà configurés (voir
  `kubernetes-secrets.md`). Le Secret `pfs-app-secrets` doit fournir `MONGO_URI`
  et `JWT_SECRET` avant que les API puissent démarrer.
- cert-manager et ses CRD, contrôleur Ingress de classe `nginx`. Adapter le
  domaine d’exemple `pfs.example.com`, l’adresse ACME et le DNS pour tester HTTPS ;
  le certificat existant utilise Let's Encrypt staging, non approuvé des navigateurs.
  Ces paramètres n’empêchent pas le contrôle des rollouts par kubectl.

## Cohérence avec US07 et le code

| Composant | Démarrage / configuration effective | Service / sondes |
|---|---|---|
| Auth | Image backend commune ; uvicorn `auth_service.main:app`, `--port $(PORT)` développé par Kubernetes depuis `auth-config` ; CORS lu par FastAPI | auth-service:8001, HTTP /health |
| Task | Même image, `task_service.main:app`, `--port $(PORT)` depuis `task-config` ; CORS et MONGO_URI lus par le code | task-service:8002, HTTP /health |
| Frontend | CMD de l’image `node docker/start.cjs` ; PORT, HOSTNAME et URL internes depuis `frontend-config` | frontend:3000, HTTP / |
| MongoDB | Même image 8.0.38 et digest que Compose ; commande de l’image | mongodb:27017 headless, mongosh ping |

Les trois Deployments et leurs Services existants sont réutilisés. Les noms
référencés par l’Ingress, ServiceAccounts, capacités supprimées et racines en
lecture seule sont conservés. Les ports de Services et sondes restent alignés
sur les valeurs des ConfigMaps ; un changement de port demande de les adapter
ensemble. Après changement d’une ConfigMap, redémarrer le Deployment concerné.

Le frontend reçoit `AUTH_INTERNAL_URL=http://auth-service:8001` et
`TASK_INTERNAL_URL=http://task-service:8002`, au lieu des noms Compose auth/task.
Les chemins navigateur `/api/auth` et `/api/task` sont intégrés au build de
l’image, pas modifiables par une variable Kubernetes runtime. L’initContainer
copie `.next` dans un emptyDir appartenant au groupe 10001 : le script de
démarrage peut y écrire ses manifestes et Next.js son cache sans ouvrir la
racine du conteneur en écriture. Les clés Next.js sont générées par réplique ;
les fonctions Preview / Server Actions ne sont pas utilisées par l’application
actuelle. Leur activation avec plusieurs répliques nécessiterait des clés partagées
via le mécanisme secret `PFS_NEXT_RUNTIME_KEYS_FILE` documenté dans US08.

MongoDB conserve son volumeClaimTemplates ReadWriteOnce de **10Gi**, monté sur
**/data/db**. `/data/configdb` et `/tmp` sont temporaires. HOME=/tmp permet à
mongosh d’utiliser un emplacement inscriptible. Readiness et liveness exécutent
un ping et échouent si `ok` n’est pas vrai ; mongosh est présent dans cette image.

Task consomme **MONGO_URI**, Auth ne consomme actuellement aucun identifiant
MongoDB. Auth est encore un stub et ne lit pas JWT_SECRET ; sa référence Secret
est conservée pour le contrat existant, sans prétendre implémenter JWT.
Task ne lit pas JWT_SECRET non plus. Aucun identifiant n’est placé en ConfigMap.
Comme Compose US07, MongoDB local n’active pas l’authentification : pour ce
StatefulSet, MONGO_URI doit cibler `mongodb:27017` dans le namespace pfs. Des
identifiants dans l’URI ne configurent pas les utilisateurs du serveur. Une base
externe authentifiée exige une URI et une configuration serveur correspondantes ;
aucun compte root ni mot de passe factice n’est ajouté ici.
Les /health API vérifient le processus HTTP, pas la disponibilité de MongoDB.

## Images publiées

`latest` a été remplacé pour les deux images ECR et l’initContainer par
**sha-150c07ba35cf**, conformément au calcul `sha-${GITHUB_SHA:0:12}` de la CI.
La publication réussie du 25 novembre 2026 est attestée par le
[job 139472218692 du run 45689528682](https://github.com/laamri/grc-devsecops-pfs/actions/runs/45689528682/job/139472218692).
Le journal confirme push, relecture des digests distants et vérification du label
revision pour les deux images :

| Dépôt | Digest vérifié par la CI |
|---|---|
| pfs-backend | sha256:6d1cc99951fe9036552597570a86278e93fe467a1570f25b95bd239db600e70f |
| pfs-frontend | sha256:8b9c798b446bd6e9329e2dbec3e99524274191ba4f128ca5f60d36d3fec12cfb |

Le dernier run develop (46041196517) échoue : son SHA n’est pas utilisé.
La consultation directe ECR locale échoue avec NoCredentials ; la preuve de
publication vient du job CI et ne constitue pas un nouveau pull local.

## Validation du 27 novembre 2026

```powershell
kubectl kustomize k8s/base
# Python + PyYAML nécessaires pour le contrôle structurel uniquement :
python k8s/tests/test-manifests.py
```

| Critère | Résultat |
|---|---|
| 1. Workloads et Services des quatre composants | Rendu réussi : 3 Deployments, 1 StatefulSet, 4 Services ; sélecteurs, ports, namespace et références Ingress vérifiés. |
| 2. Readiness et liveness | Deux sondes présentes par composant ; ping exécuté avec succès dans l’image MongoDB exacte, UID 999, racine en lecture seule et capacités supprimées. Les sondes Kubernetes ne sont pas exécutées sur cluster. |
| 3. Configuration et secrets | Trois ConfigMaps rendues ; PORT consommé par les commandes uvicorn et Next.js ; références Secret conservées ; montage PVC 10Gi /data/db contrôlé dans le rendu. |
| 4. Déploiement opérationnel et persistance | **Bloqué** : `kubectl config current-context` retourne `current-context is not set` et get-contexts ne liste aucun contexte. Aucun apply ni rollout exécuté ; Running, Ready, redémarrages et PVC Bound non observés. La persistance effective reste à valider sur cluster. |

Le test structurel réussit pour les quatre composants. Un test Docker local
complémentaire du frontend **1.0.1 déjà en cache** valide copie d’initialisation,
UID 10001, racine en lecture seule, volume `.next` et réponse HTTP 200 ; il ne
qualifie pas à lui seul l’image CI sélectionnée. Le test MongoDB emploie le digest
exact du manifeste. Les conteneurs/volumes temporaires de ces tests ont été
supprimés. Aucun service AWS payant créé. `git diff --check` réussit.
