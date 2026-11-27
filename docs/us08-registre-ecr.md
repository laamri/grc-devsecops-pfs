# US08 — Versionner et publier les images dans Amazon ECR

## Versions à utiliser

**Frontend : `1.0.1`. Backend Auth/Task : conserver `1.0.0`.** La correction des clés
Next.js concerne uniquement le frontend. Aucune mise à jour des workloads n’a été
effectuée pendant cette livraison.

Registre : `132415609490.dkr.ecr.eu-north-1.amazonaws.com`. Les dépôts privés sont
`IMMUTABLE`. Les deux tags de chaque version désignent le même digest :

| Dépôt | Version | Commit source | Tags conservés/publiés | Digest distant confirmé |
|---|---|---|---|---|
| `pfs-frontend` | **`1.0.1`** | `cbf89a9de2024850b73ba76a87e17554e394ad27` | `1.0.1`, `sha-cbf89a9de2024850b73ba76a87e17554e394ad27` | `sha256:657948e88bc31608a322b3d89be0b9fa0a38ee330e4c8c1784f5c159a3934828` |
| `pfs-backend` | `1.0.0` | `e1a8453d9189e4961f546debef4f176a5353bd95` | `1.0.0`, `sha-e1a8453d9189` | `sha256:7e1f0ab6f82f4a6fde888450d5aac7507f6ff182e965c4720726208af56ca7ba` |

L’ancien frontend `1.0.0` reste disponible avec ses tags `1.0.0` et
`sha-e1a8453d9189`, au digest
`sha256:6c922314f22f3a5019820a9a3a9ea93b25e8c895ea9ef1673d59c7c1b8be2f0f`.
Il contient les clés de build historiques et doit être remplacé par `1.0.1` dans
les prochains déploiements. Aucun tag historique n’a été réaffecté ou supprimé.

## Authentification

Sur le poste de publication, Docker utilise le gestionnaire `ecr-login` pour ce registre.
Le profil local `pfs-ecr-us08` récupère les identifiants temporaires du profil AWS `pfs-dev`.

```powershell
aws login --profile pfs-dev --region eu-north-1
aws sts get-caller-identity --profile pfs-dev --query Account --output text
$env:AWS_PROFILE = 'pfs-ecr-us08'
$env:AWS_REGION = 'eu-north-1'
$env:AWS_ECR_DISABLE_CACHE = 'true'
```

Le compte attendu est `132415609490`. Docker obtient son jeton au moment du push ou du pull.
Le dépôt Git contient uniquement les noms des profils et l’adresse du registre.

## Construire et publier une future correction frontend seule

Choisir une nouvelle version sémantique disponible. Les tags `1.0.1` sont déjà
publiés et immuables. Ne pas reconstruire ou publier le backend pour cette correction.
Effectuer les tests et qualifier le scan avant les deux commandes `docker push`.

```powershell
$registry = '132415609490.dkr.ecr.eu-north-1.amazonaws.com'
$version = Read-Host 'Nouvelle version frontend X.Y.Z'
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version invalide' }
if (git status --porcelain) { throw 'Construire depuis un commit propre' }
$sha = git rev-parse HEAD
$tag = "sha-$sha"
$image = "$registry/pfs-frontend:$tag"

docker build --label "org.opencontainers.image.revision=$sha" --label "org.opencontainers.image.version=$version" -t $image ./frontend
if ($LASTEXITCODE -ne 0) { throw 'Échec du build frontend' }
node --test scripts/test_next_runtime.cjs
if ($LASTEXITCODE -ne 0) { throw 'Échec des tests de packaging' }
python scripts/validate_us08_frontend.py $image "$env:TEMP/us08-tests.json"
if ($LASTEXITCODE -ne 0) { throw 'Échec du parcours frontend' }
python scripts/scan_image_secrets.py $image "$env:TEMP/us08-scan.json" "$registry/pfs-frontend@sha256:6c922314f22f3a5019820a9a3a9ea93b25e8c895ea9ef1673d59c7c1b8be2f0f"
if ($LASTEXITCODE -ne 0) { throw 'Scan incomplet ou clé détectée' }
# Relire et qualifier aussi toutes les alertes Gitleaks/heuristiques du rapport.
# Vérifier dans ECR que $version et $tag sont libres avant la publication.
docker tag $image "$registry/pfs-frontend:$version"
if ($LASTEXITCODE -ne 0) { throw 'Échec du tag local' }
docker push $image
if ($LASTEXITCODE -ne 0) { throw 'Échec du push du tag commit' }
docker push "$registry/pfs-frontend:$version"
if ($LASTEXITCODE -ne 0) { throw 'Échec du push de version' }
```

## Preuve de correction frontend 1.0.1 — 21 novembre 2026

La construction de livraison a été lancée depuis le commit local propre
`cbf89a9de2024850b73ba76a87e17554e394ad27`, avec les labels OCI `revision` correspondant
à ce commit et `version=1.0.1`. Le contexte frontend n’inclut que les fichiers
explicitement autorisés par `.dockerignore`. Les sorties de lint/build réussies
ont été réutilisées par le cache Docker pour les mêmes fichiers du commit ; les
tests d’exécution et le scan ont porté sur l’image de livraison portant ces labels.
La preuve détaillée expurgée est dans
[`evidence/us08-frontend-1.0.1.json`](evidence/us08-frontend-1.0.1.json).

### Contrainte Next.js et correction appliquée

Next.js 16.4.6 utilise des clés valides pour les captures Server Actions et les
données Preview lorsque ces fonctionnalités sont appelées. Les laisser vides à
l’exécution ne préserverait pas ce contrat. Le projet ne publie actuellement aucune
Server Action et aucun endpoint Preview métier, mais les consommateurs Next.js
restent opérationnels :

- `frontend/docker/prepare-runtime.cjs` vide les champs de clés **dans le stage
  builder avant le premier COPY dans le stage runtime**. Il réécrit également
  `server-reference-manifest.js`, copie JavaScript découverte lors de la correction
  et absente de l’inventaire des alertes initiales. Le build échoue si une valeur
  supprimée subsiste dans un autre fichier standalone.
- `frontend/docker/start.cjs` génère les trois nouvelles clés et l’identifiant
  `previewModeId` au démarrage, puis remplit les manifestes JSON et JavaScript avant
  de charger `server.js`. Les deux copies des paramètres Preview restent identiques.
  Les fichiers modifiés appartiennent à l’utilisateur `node` et sont en mode `0600`.
  Aucune valeur n’est écrite dans les logs. Les clés n’existent que dans la couche
  inscriptible du conteneur, pas dans les couches de l’image ECR.
- Les URL publiques par défaut sont `/api/auth` et `/api/task` : le navigateur utilise
  le proxy Next.js du même domaine. Les URL internes restent configurables à
  l’exécution par `AUTH_INTERNAL_URL` et `TASK_INTERNAL_URL` comme dans Compose.

Les clés sont renouvelées à chaque démarrage par défaut ; les sessions Preview et
captures dépendant des anciennes clés sont donc invalidées. Pour plusieurs répliques
ou une persistance entre redémarrages, monter un même fichier de secrets en lecture
seule et définir `PFS_NEXT_RUNTIME_KEYS_FILE` vers ce fichier. Son objet JSON doit
contenir `encryptionKey` (base64 AES de 16, 24 ou 32 octets), `previewModeId`
(32 caractères hexadécimaux), `previewModeSigningKey` et `previewModeEncryptionKey`
(64 caractères hexadécimaux chacun). Ces valeurs sont fournies par le gestionnaire
de secrets au déploiement, jamais par `ARG`, `ENV` ou `COPY` pendant le build.
`NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, si fournie au démarrage, remplace uniquement
la clé Server Actions. Une configuration invalide bloque le démarrage sans divulguer
la valeur. Les emplacements de manifestes doivent être inscriptibles par `node` ;
une racine intégralement en lecture seule nécessite un montage inscriptible adapté.

### Tests réellement exécutés

| Contrôle | Résultat |
|---|---|
| `npm run lint` dans le builder | Réussi, y compris les scripts de packaging ; règle CommonJS limitée à `docker/*.cjs`. |
| `npm run build` dans le builder | Réussi : compilation de production, TypeScript, génération des pages et préparation standalone. |
| `node --test scripts/test_next_runtime.cjs` | 3/3 réussis : retrait des clés et cohérence runtime ; rejet d’une copie inattendue ; fichier partagé et rejet de configuration invalide sans valeur dans les erreurs. |
| Démarrage de l’image de livraison | HTTP 200, utilisateur UID 1000 ; manifestes cohérents, clés de format valide, fichiers en mode 0600. |
| Parcours navigateur Playwright 1.58.2 + Chrome installé | Auth et Task `ok`, création d’une tâche par le formulaire, affichage dans la liste et relecture après rechargement ; aucune erreur de page/réseau ; fetches sur le même domaine. |
| Dépendances du test | Backend ECR `1.0.0` au digest inchangé ; MongoDB isolé ; aucune reconstruction du backend. |

La tâche de contrôle de l’image de livraison portait le titre non sensible
`pfs-us08-9355860121-browser-task`. Les conteneurs, réseau et données de test étaient
isolés puis supprimés. Aucune donnée applicative existante n’a été modifiée.

### Scan complet de l’image publiée

Outils : Gitleaks **8.30.1**, Docker **29.8.1**, Python **3.12** et
`scripts/scan_image_secrets.py`. L’image testée, scannée et repullée depuis ECR a le
même digest `sha256:657948e88bc31608a322b3d89be0b9fa0a38ee330e4c8c1784f5c159a3934828`.
Sa configuration est
`sha256:3fcf4a4e129b0044969afa1ed61095c9b3dc3abe8cd50f13974a87767add716a`.

Le scan a vérifié la configuration, les **19 entrées d’historique** sans troncature,
les métadonnées et **9/9 couches**, soit **3 873 occurrences de fichiers réguliers**,
sans fusion ni application des whiteouts. Les SHA-256 décompressés sont vérifiés
contre les `rootfs.diff_ids`. Les sept champs JSON inspectés (trois clés, leurs
copies Preview et les deux copies de `previewModeId`) sont tous vides dans l’image.
Les quatre anciennes valeurs de l’image 1.0.0 sont recherchées dans la configuration,
l’historique et les octets de chaque fichier : **aucune occurrence**.
Le manifeste JavaScript est aussi contrôlé par la vérification exhaustive des valeurs
retirées dans le builder et par la recherche d’anciennes valeurs sur les couches.

| Couche | SHA-256 décompressé vérifié | Fichiers réguliers |
|---|---|---|
| 1 | `sha256:75f1d9657d880da5f75298e8f40e9928bb6e260c50d26f97af196845307e3064` | 84 |
| 2 | `sha256:313a78c90b21a75531eacc3998f28ac7cf2f95060c1974a257ed80bd7a7a062c` | 2499 |
| 3 | `sha256:acb510a1dd0f941dce95b097dde9780de168f02b6a85102c39d920d4eb0b9d26` | 16 |
| 4 | `sha256:f06a70e4735f2521407da491d35f156f89ead52d32bba35a30186f9111b5052d` | 1 |
| 5 | `sha256:f51be206f8e4f3b39355d503ca4d1ebfc0a4359e0c52c589d7afc0d085fb2ae8` | 0 |
| 6 | `sha256:ef90051a7a3fa16daaa1aa5c79d18dbef68a50e7f5cda085d3a120cf963d1ed8` | 1244 |
| 7 | `sha256:4b9fb26c27101487d095b975142f419c30c3471d7f26d349b52b5cd62876390b` | 23 |
| 8 | `sha256:694db1afcbcbb65653979fae67df5d414a54b47fc15528bae37ba978d67a10cc` | 5 |
| 9 | `sha256:36e76b5017d802ae9878339b948b2dfeb2533f884e0804919ed65f889481c61d` | 1 |

Gitleaks émet **11 alertes**, toutes qualifiées : 6 faux positifs (V8, just-diff,
export `tokenizeClass`) et 5 données publiques (exemples npm, clés publiques Corepack).
Les recherches complémentaires émettent **51 alertes** : 46 faux positifs de code/
messages et 5 exemples publics de documentation npm. Les tuples règle/fichier/ligne
correspondent exactement aux alertes historiques restantes après retrait des cinq
alertes JSON Next.js ; les contextes Gitleaks ont été relus. Les **62 qualifications**
avec fichier, symbole et usage sont conservées dans le rapport expurgé joint.
**Aucun secret confirmé et aucune alerte non qualifiée dans ce scan.** Les limites
usuelles du contrôle par règles demeurent ; le cache local du stage builder, non
publié dans ECR, n’est pas assimilé à une couche de l’image livrée.

### Vérification distante et décision US08

`aws ecr describe-images` a confirmé que `1.0.1` et
`sha-cbf89a9de2024850b73ba76a87e17554e394ad27` pointent tous deux vers
`sha256:657948e88bc31608a322b3d89be0b9fa0a38ee330e4c8c1784f5c159a3934828`.
Un pull par ce digest et une inspection ont confirmé l’identité de l’image et son
label de commit. Les dépôts restent `IMMUTABLE`. La comparaison des inventaires ECR
avant/après confirme : tous les tags et digests backend sont conservés ; tous les
anciens tags frontend sont conservés ; seuls les deux nouveaux tags frontend ont
été ajoutés. Aucune image backend n’a été republiée.

**Le dernier critère US08 est satisfait pour la version frontend 1.0.1 contrôlée,
avec le backend 1.0.0 précédemment qualifié.** Utiliser le nouveau digest frontend
ci-dessus ; la conclusion historique sur le frontend 1.0.0 reste valable pour cet
ancien artefact. La correction est committée localement ; la documentation fait
l’objet d’un second commit local. Aucun `git push` n’a été effectué.

## Contrôle historique des images 1.0.0

Les sections suivantes conservent la qualification des anciens digests. Leurs
conclusions et propositions décrivent l’état antérieur à la correction 1.0.1.

Qualification terminée le **21 novembre 2026** (Africa/Casablanca), avec **Gitleaks
8.30.1**, Docker **29.8.1**, Python **3.12** et relecture des fichiers issus des images.
Les valeurs des candidats sont omises, y compris pour les exemples publics.

| Image identifiée avant toute republication | Digest ECR audité | Couverture | Qualification |
|---|---|---|---|
| `pfs-backend` | `sha256:7e1f0ab6f82f4a6fde888450d5aac7507f6ff182e965c4720726208af56ca7ba` | Configuration, 20 entrées d’historique, 9/9 couches, 7 530 occurrences de fichiers réguliers | 197/197 alertes qualifiées : 175 faux positifs, 22 données publiques ; aucun secret applicatif actif confirmé. |
| `pfs-frontend` | `sha256:6c922314f22f3a5019820a9a3a9ea93b25e8c895ea9ef1673d59c7c1b8be2f0f` | Configuration, 18 entrées d’historique, 8/8 couches, 3 872 occurrences de fichiers réguliers | 67/67 alertes qualifiées : 52 faux positifs, 10 données publiques, 5 occurrences de 3 clés cryptographiques générées ; usage métier actif non établi. |

Une lecture ECR `describe-images` a confirmé pour **chacun de ces deux digests** les
tags `1.0.0` et `sha-e1a8453d9189`. Ces tags et les dépôts n’ont pas été modifiés.
La seule image contenant les clés générées signalées est **pfs-frontend au digest
ci-dessus**. Le backend partagé par Auth et Task n’est pas concerné par ces clés.
Cette identification porte sur les deux digests demandés, pas sur tous les autres
digests du registre ni sur les workloads réellement déployés.

### Méthode et limites du constat

Les références ont été récupérées par digest exact. L’inspection Docker, l’historique
sans troncature, la configuration et toutes les couches de `docker save` ont été
examinés. La configuration a été vérifiée par SHA-256 et chaque couche décompressée
contre son `rootfs.diff_ids`. Les couches ont été parcourues séparément, sans fusion
ni application des whiteouts : les fichiers supprimés ou remplacés restent inclus.
Les métadonnées des couches sans fichiers réguliers sont incluses.

Gitleaks a analysé les fichiers sous des noms neutres, l’inspection, la configuration,
l’historique et les métadonnées avec `--redact=100`, `--ignore-gitleaks-allow`, sans
exclusion du projet, `--max-target-megabytes 0`, `--max-archive-depth 5` et
`--max-decode-depth 5`. Il a émis **29 alertes** (13 backend, 16 frontend).
Les recherches complémentaires sur les octets de tous les fichiers, binaires inclus,
ont émis **235 alertes** (184 backend, 51 frontend) sur les en-têtes de clés privées
et les affectations de mots de passe/clés. Aucun ancien marqueur secret du projet
n’a été trouvé. Les contextes de ces **264 occurrences** ont maintenant été relus ;
aucune alerte de cet inventaire ne reste sans qualification.

« Faux positif » désigne une variable, un type, un message ou une opération sans
valeur secrète codée en dur. « Donnée publique » désigne une clé publique, un exemple
ou un vecteur d’autotest dont l’usage public est identifié. Les clés privées de test
ne sont pas de simples en-têtes : les **dix clés complètes** de GnuTLS ont été
comparées octet pour octet aux symboles de
[`lib/crypto-selftests-pk.c`, GnuTLS 3.7.9](https://github.com/gnutls/gnutls/blob/3.7.9/lib/crypto-selftests-pk.c).
Elles servent aux autotests de la bibliothèque et ne sont pas des identités du projet.

Le contrôle porte sur les artefacts publiés et leurs consommateurs embarqués, pas
sur les secrets injectés dans un déploiement réel. Aucune connexion à un service
externe ni tentative d’utilisation d’identifiants n’a été faite. La qualification
statique des alertes est terminée ; l’activité des fonctionnalités dans un déploiement
n’a pas été observée. Comme tout contrôle par règles, il ne prouve pas l’absence de
secrets inconnus, chiffrés ou encodés au-delà des profondeurs indiquées.

### Clés Next.js : nature et usage confirmés

L’image embarque Next.js **16.4.6**. Dans la couche 6
(`sha256:e3bcd9fdf696654ad2a6efe915e68740305d8cbf751a61b4b5cd4c9afe22618f`),
les cinq alertes correspondent à **trois valeurs distinctes par fonction** :

| Fichier et ligne | Nom de la clé | Usage confirmé par le code embarqué | Qualification |
|---|---|---|---|
| `app/.next/server/server-reference-manifest.json:4` | `encryptionKey` | Clé AES de chiffrement des captures de Server Actions ; format AES valide. `app/node_modules/next/dist/server/app-render/encryption-utils.js:78` choisit l’environnement `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, sinon cette clé. | Secret généré de build, pas une donnée publique. Les tables `node` et `edge` sont vides : aucune Server Action publiée identifiée. Usage actif non établi. |
| `app/.next/server/preview-props.json:3` | `previewModeSigningKey` | Signature/vérification JWT des données Preview ; lue par `app/node_modules/next/dist/server/api-utils/node/try-get-preview-data.js:68`. | Secret généré de build ; aucun endpoint Preview métier identifié. Usage actif non établi. |
| `app/.next/server/preview-props.json:4` | `previewModeEncryptionKey` | Déchiffrement des données Preview ; lue par `app/node_modules/next/dist/server/api-utils/node/try-get-preview-data.js:80`. | Secret généré de build ; aucun endpoint Preview métier identifié. Usage actif non établi. |
| `app/.next/prerender-manifest.json:151` | `previewModeSigningKey` | Copie identique de la clé de signature de `preview-props.json`. | Même secret, pas une quatrième clé. |
| `app/.next/prerender-manifest.json:152` | `previewModeEncryptionKey` | Copie identique de la clé de chiffrement de `preview-props.json`. | Même secret, pas une cinquième clé. |

Ces fichiers ne sont ni remplacés ni supprimés par les couches suivantes ; les clés
restent dans l’image finale. Les manifestes publiés inventorient `/`, la route proxy
`/api/[service]/[...path]`, le favicon et les pages d’erreur ; aucun endpoint d’activation
Preview n’y est identifié. Les seules pages Pages Router sont `/404` et `/500`.
Le fournisseur App Router `app/node_modules/next/dist/server/async-storage/draft-mode-provider.js`
utilise `previewModeId`, pas les deux clés Preview signalées. La présence de fonctions
génériques capables de lire ces clés ne démontre donc pas leur utilisation métier.

La précédente mention « secrets détectés » est précisée : **matériel secret généré
embarqué confirmé, mais aucun secret actif de service ni utilisation effective de
ces clés confirmé**. Elles ne sont pas reclassées en clés publiques ou faux positifs.
La génération et l’intégration de la clé Server Actions au build sont un comportement
[documenté par Next.js](https://nextjs.org/docs/app/guides/self-hosting), à distinguer
d’une fuite d’un identifiant AWS, MongoDB ou JWT du projet.

### Traitement avant une éventuelle republication

Le critère strict « aucune valeur secrète dans les images » reste **non satisfait
pour le frontend** tant que ces clés générées y sont incluses. La qualification n’est
plus incomplète. Aucun secret actif de service n’ayant été confirmé, aucune rotation
d’identifiants AWS/MongoDB/JWT n’est justifiée par ces alertes seules.

Pour retirer ce matériel cryptographique des couches publiées, préparer une sortie
standalone assainie **dans le stage builder, avant le premier `COPY --from=builder`
du stage runtime**. Traiter toutes les copies des champs concernés, pas seulement
un fichier et pas par un `RUN rm` ultérieur dans l’image finale. Si ces fonctionnalités
restent inutilisées, vérifier par des tests de démarrage et de routes qu’un traitement
compatible avec Next.js 16.4.6 fonctionne avant de produire une nouvelle image.
Ne pas supprimer aveuglément les manifestes requis par le framework.

Si Server Actions ou Preview sont nécessaires, produire les clés effectives lors du
déploiement, via le stockage de secrets et un volume d’exécution protégé, et préparer
les manifestes dans ce volume avant de démarrer Next.js. Pour Server Actions, le code
embarqué accepte aussi `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` à l’exécution. Fournir
cette variable uniquement au build ne retire pas la clé des artefacts ; Next.js indique
qu’elle est intégrée à la sortie de build. Un secret BuildKit n’empêche pas non plus
une copie dans les fichiers générés. Pour Preview, les deux fichiers JSON doivent
rester cohérents ; aucune variable runtime dédiée n’a été validée ici pour le serveur
Node. Cette stratégie doit être implémentée et testée avant publication ; elle n’a
pas été appliquée pendant ce contrôle documentaire.

**Renouvellement :** générer de nouvelles clés Next.js pour le prochain déploiement,
sans réutiliser celles récupérables dans l’image publiée. Si l’exploitant confirme
qu’elles sont actuellement utilisées, les considérer comme exposées aux lecteurs
du registre et les remplacer avant remise en service : nouvelle clé Server Actions
avec redéploiement coordonné de toutes les répliques ; nouvelles clés Preview de
signature/chiffrement et invalidation des anciennes sessions Preview (renouveler
également l’identifiant de mode Preview si cette fonctionnalité est activée).
Le changement invalide les captures/actions et données Preview dépendant des
anciennes clés ; prévoir le renouvellement des pages/sessions clientes.

La prochaine image à reconstruire et contrôler pour cette correction est
`pfs-frontend`, en remplacement fonctionnel du digest
`sha256:6c922314f22f3a5019820a9a3a9ea93b25e8c895ea9ef1673d59c7c1b8be2f0f`.
Utiliser ultérieurement une **nouvelle version et de nouveaux tags immuables** après
validation des couches et du fonctionnement. Aucun nouveau digest n’est annoncé ici :
aucune reconstruction ni republication n’a été effectuée. Le digest backend audité
ne nécessite pas de reconstruction du fait de ces alertes.

### Inventaire exhaustif des alertes qualifiées

Chaque ligne ci-dessous représente **une occurrence**, même si le même fichier ou
la même clé apparaît ailleurs. `G` désigne Gitleaks, `H` la recherche heuristique ;
les numéros sont des identifiants de qualification, pas les identifiants de règles.
Les lignes de binaires sont des positions calculées par comptage des octets LF.
`inspect.txt` désigne la sortie de `docker image inspect`, `history.txt` celle de
`docker history --no-trunc`, `config.txt` la configuration JSON de `docker save`,
et `layer3-metadata.txt` l’inventaire des entrées tar de la couche 3. Ce sont des
supports d’analyse temporaires, pas des fichiers applicatifs embarqués.
Les valeurs de tous les candidats sont volontairement omises.

#### Backend

| Alerte | Couche | Fichier:ligne | Nom de clé/champ ou symbole | Usage | Qualification |
|---|---|---|---|---|---|
| H-B-001 | 1 | `usr/bin/gpasswd:77` | `Password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-002 | 1 | `usr/bin/newgrp:28` | `Password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-003 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3639` | `gost12_512_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-004 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3644` | `gost12_256_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-005 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3648` | `gost01_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-006 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3652` | `ecdsa_secp521r1_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-007 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3653` | `ecdsa_secp192r1_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-008 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3653` | `ecdsa_secp224r1_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-009 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3653` | `ecdsa_secp256r1_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-010 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3653` | `ecdsa_secp384r1_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-011 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3658` | `dsa_2048_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-012 | 1 | `usr/lib/x86_64-linux-gnu/libgnutls.so.30.34.3:3678` | `rsa_2048_privkey` | Clé privée de vecteur d’autotest GnuTLS ; égalité octet pour octet avec le symbole public amont. | Donnée publique |
| H-B-013 | 1 | `usr/lib/x86_64-linux-gnu/libpam.so.0.85.1:85` | `password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-014 | 1 | `usr/lib/x86_64-linux-gnu/libpam.so.0.85.1:85` | `password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-015 | 1 | `usr/lib/x86_64-linux-gnu/libpam.so.0.85.1:85` | `password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-016 | 1 | `usr/lib/x86_64-linux-gnu/security/pam_exec.so:6` | `Password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-017 | 1 | `usr/lib/x86_64-linux-gnu/security/pam_stress.so:8` | `Password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-018 | 1 | `usr/lib/x86_64-linux-gnu/security/pam_stress.so:8` | `password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-019 | 1 | `usr/lib/x86_64-linux-gnu/security/pam_userdb.so:9` | `Password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-B-020 | 1 | `usr/share/pam-configs/unix:20` | `PrimaryPassword` | Rubrique Password de configuration PAM ; la règle absorbe le saut de ligne et une directive. | Faux positif |
| G-B-021 | 3 | `layer3-metadata.txt:1` | `libgssapi-krb5-2` | Nom de fichier de paquet Debian terminé par un suffixe d’architecture ; interprété à tort comme clé. | Faux positif |
| G-B-022 | 3 | `layer3-metadata.txt:1` | `libkeyutils1` | Nom de fichier de paquet Debian terminé par un suffixe d’architecture ; interprété à tort comme clé. | Faux positif |
| H-B-023 | 3 | `usr/local/lib/python3.11/distutils/command/register.py:132` | `password` | password : saisie interactive, variable de configuration ou texte d’erreur de publication Python. | Faux positif |
| H-B-024 | 3 | `usr/local/lib/python3.11/distutils/command/register.py:157` | `password` | password : saisie interactive, variable de configuration ou texte d’erreur de publication Python. | Faux positif |
| H-B-025 | 3 | `usr/local/lib/python3.11/distutils/command/register.py:175` | `password` | password : saisie interactive, variable de configuration ou texte d’erreur de publication Python. | Faux positif |
| H-B-026 | 3 | `usr/local/lib/python3.11/distutils/command/upload.py:65` | `password` | password : saisie interactive, variable de configuration ou texte d’erreur de publication Python. | Faux positif |
| G-B-027 | 3 | `usr/local/lib/python3.11/distutils/msvccompiler.py:39` | `RegEnumKey` | RegEnumKey : alias de fonction Windows de lecture du registre. | Faux positif |
| H-B-028 | 3 | `usr/local/lib/python3.11/hashlib.py:204` | `password` | password : préparation de l’entrée du calcul PBKDF2 ; aucune entrée codée en dur. | Faux positif |
| H-B-029 | 3 | `usr/local/lib/python3.11/hashlib.py:213` | `password` | password : préparation de l’entrée du calcul PBKDF2 ; aucune entrée codée en dur. | Faux positif |
| H-B-030 | 3 | `usr/local/lib/python3.11/hashlib.py:214` | `password` | password : préparation de l’entrée du calcul PBKDF2 ; aucune entrée codée en dur. | Faux positif |
| H-B-031 | 3 | `usr/local/lib/python3.11/logging/handlers.py:1041` | `password` | self.password : donnée reçue du constructeur du gestionnaire SMTP. | Faux positif |
| H-B-032 | 3 | `usr/local/lib/python3.11/netrc.py:138` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-033 | 3 | `usr/local/lib/python3.11/nntplib.py:322` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-034 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:93` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-035 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:120` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-036 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:339` | `url_user_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-037 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:344` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-038 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:355` | `index_url_user_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-039 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:360` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-040 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:402` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-041 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:421` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-042 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:437` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-043 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:462` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-044 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:485` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-045 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:499` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-046 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/network/auth.py:512` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-047 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/vcs/subversion.py:98` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-048 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/vcs/subversion.py:103` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-049 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:429` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-050 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:442` | `secret_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-051 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:443` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-052 | 3 | `usr/local/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:445` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-053 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/distlib/index.py:83` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-054 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/distlib/util.py:843` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-055 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/distlib/util.py:846` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-056 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/adapters.py:214` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-057 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/adapters.py:218` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-058 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/adapters.py:427` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-059 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:53` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-060 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:60` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-061 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:81` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-062 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:112` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-063 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/sessions.py:323` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-064 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/requests/sessions.py:329` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-065 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:69` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-066 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:136` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-067 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:203` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-068 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:363` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-069 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/truststore/_api.py:142` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-070 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/truststore/_api.py:145` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-071 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/connection.py:320` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-072 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/connection.py:354` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-073 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/connection.py:423` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-074 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/connectionpool.py:967` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-075 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/connectionpool.py:983` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-076 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/connectionpool.py:1039` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-077 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/contrib/_securetransport/low_level.py:231` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-078 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/contrib/pyopenssl.py:477` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-079 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/contrib/socks.py:102` | `proxy_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-080 | 3 | `usr/local/lib/python3.11/site-packages/pip/_vendor/urllib3/util/ssl_.py:385` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-081 | 3 | `usr/local/lib/python3.11/urllib/parse.py:198` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-082 | 3 | `usr/local/lib/python3.11/urllib/parse.py:199` | `have_password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-083 | 3 | `usr/local/lib/python3.11/urllib/parse.py:228` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-084 | 3 | `usr/local/lib/python3.11/urllib/parse.py:229` | `have_password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-085 | 3 | `usr/local/lib/python3.11/urllib/request.py:786` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-086 | 3 | `usr/local/lib/python3.11/urllib/request.py:815` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-087 | 3 | `usr/local/lib/python3.11/urllib/request.py:913` | `password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-088 | 3 | `usr/local/lib/python3.11/urllib/request.py:977` | `add_password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-089 | 3 | `usr/local/lib/python3.11/urllib/request.py:1108` | `add_password` | password/add_password : lecture, parsing, stockage ou documentation d’identifiants fournis à l’exécution. | Faux positif |
| H-B-090 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/cryptography.py:55` | `password` | password : paramètre de chargement/chiffrement PEM fourni à l’exécution. | Faux positif |
| H-B-091 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/cryptography.py:60` | `password` | password : paramètre de chargement/chiffrement PEM fourni à l’exécution. | Faux positif |
| G-B-092 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/eddsa.py:54` | `key` | key/key_cls : annotation de type et classe cryptographique, pas une instance de clé. | Faux positif |
| G-B-093 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/eddsa.py:55` | `key_cls` | key/key_cls : annotation de type et classe cryptographique, pas une instance de clé. | Faux positif |
| G-B-094 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/eddsa.py:66` | `key` | key/key_cls : annotation de type et classe cryptographique, pas une instance de clé. | Faux positif |
| G-B-095 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/eddsa.py:67` | `key_cls` | key/key_cls : annotation de type et classe cryptographique, pas une instance de clé. | Faux positif |
| G-B-096 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/mldsa.py:56` | `key` | key/key_cls : annotation de type et classe cryptographique, pas une instance de clé. | Faux positif |
| G-B-097 | 7 | `opt/venv/lib/python3.11/site-packages/dns/dnssecalgs/mldsa.py:57` | `key_cls` | key/key_cls : annotation de type et classe cryptographique, pas une instance de clé. | Faux positif |
| H-B-098 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/.agents/skills/fastapi/references/responses.md:76` | `secret_key` | secret_key : valeur fictive de démonstration du filtrage des champs de réponse FastAPI. | Donnée publique |
| H-B-099 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/openapi/models.py:379` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-100 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/api_key.py:143` | `api_key` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-101 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/api_key.py:231` | `api_key` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-102 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/api_key.py:319` | `api_key` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-103 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/http.py:26` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-104 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/http.py:218` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-105 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/http.py:221` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-106 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/oauth2.py:90` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-107 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/oauth2.py:156` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-108 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/oauth2.py:217` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-109 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/oauth2.py:256` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-110 | 7 | `opt/venv/lib/python3.11/site-packages/fastapi/security/oauth2.py:323` | `password` | api_key/password : champ de schéma, annotation ou valeur lue dans la requête HTTP ; aucune constante secrète. | Faux positif |
| H-B-111 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:93` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-112 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:120` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-113 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:339` | `url_user_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-114 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:344` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-115 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:355` | `index_url_user_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-116 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:360` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-117 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:402` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-118 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:421` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-119 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:437` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-120 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:462` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-121 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:485` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-122 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:499` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-123 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/network/auth.py:512` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-124 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/vcs/subversion.py:98` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-125 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/vcs/subversion.py:103` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-126 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:429` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-127 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:442` | `secret_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-128 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:443` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-129 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_internal/vcs/versioncontrol.py:445` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-130 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/distlib/index.py:83` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-131 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/distlib/util.py:843` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-132 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/distlib/util.py:846` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-133 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/adapters.py:214` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-134 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/adapters.py:218` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-135 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/adapters.py:427` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-136 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:53` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-137 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:60` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-138 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:81` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-139 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/auth.py:112` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-140 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/sessions.py:323` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-141 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/requests/sessions.py:329` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-142 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:69` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-143 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:136` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-144 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:203` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-145 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/rich/prompt.py:363` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-146 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/truststore/_api.py:142` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-147 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/truststore/_api.py:145` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-148 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/connection.py:320` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-149 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/connection.py:354` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-150 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/connection.py:423` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-151 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/connectionpool.py:967` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-152 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/connectionpool.py:983` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-153 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/connectionpool.py:1039` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-154 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/contrib/_securetransport/low_level.py:231` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-155 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/contrib/pyopenssl.py:477` | `password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-156 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/contrib/socks.py:102` | `proxy_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-157 | 7 | `opt/venv/lib/python3.11/site-packages/pip/_vendor/urllib3/util/ssl_.py:385` | `key_password` | password/key_password/proxy_password : paramètres, annotations, extraction d’URL, saisie ou transfert d’identifiants reçus à l’exécution. | Faux positif |
| H-B-158 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/networks.py:335` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-159 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/networks.py:553` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-160 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1833` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-161 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1835` | `password` | Exemple de documentation de SecretStr/SecretBytes et de son affichage masqué ; pas un mot de passe de service. | Donnée publique |
| H-B-162 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1838` | `password` | Exemple de documentation de SecretStr/SecretBytes et de son affichage masqué ; pas un mot de passe de service. | Donnée publique |
| H-B-163 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1855` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-164 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1862` | `password` | Exemple de documentation de SecretStr/SecretBytes et de son affichage masqué ; pas un mot de passe de service. | Donnée publique |
| H-B-165 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1864` | `password` | Exemple de documentation de SecretStr/SecretBytes et de son affichage masqué ; pas un mot de passe de service. | Donnée publique |
| H-B-166 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1916` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-167 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/types.py:1919` | `password` | Exemple de documentation de SecretStr/SecretBytes et de son affichage masqué ; pas un mot de passe de service. | Donnée publique |
| H-B-168 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/v1/networks.py:47` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-169 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/v1/networks.py:193` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-170 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/v1/networks.py:205` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-171 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/v1/networks.py:220` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-172 | 7 | `opt/venv/lib/python3.11/site-packages/pydantic/v1/networks.py:231` | `password` | password : annotation de type, parsing d’URL ou représentation SecretStr ; aucune clé applicative. | Faux positif |
| H-B-173 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/_kms_connect_shared.py:243` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-174 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/asynchronous/auth.py:204` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-175 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/asynchronous/auth.py:233` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-176 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/asynchronous/auth.py:309` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-177 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/asynchronous/mongo_client.py:567` | `password` | Exemple de documentation des caractères à échapper dans les identifiants MongoDB. | Donnée publique |
| H-B-178 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/asynchronous/mongo_client.py:922` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-179 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/asynchronous/mongo_client.py:1043` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-180 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/synchronous/auth.py:202` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-181 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/synchronous/auth.py:231` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-182 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/synchronous/auth.py:307` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-183 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/synchronous/mongo_client.py:567` | `password` | Exemple de documentation des caractères à échapper dans les identifiants MongoDB. | Donnée publique |
| H-B-184 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/synchronous/mongo_client.py:922` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-185 | 7 | `opt/venv/lib/python3.11/site-packages/pymongo/synchronous/mongo_client.py:1043` | `password` | password : identifiant reçu de la configuration MongoDB ou paramètre du mécanisme d’authentification. | Faux positif |
| H-B-186 | 7 | `opt/venv/lib/python3.11/site-packages/starlette/datastructures.py:125` | `password` | password : parsing d’URL ou remplacement par un masque dans la représentation. | Faux positif |
| H-B-187 | 7 | `opt/venv/lib/python3.11/site-packages/starlette/datastructures.py:183` | `password` | password : parsing d’URL ou remplacement par un masque dans la représentation. | Faux positif |
| H-B-188 | 7 | `opt/venv/lib/python3.11/site-packages/uvicorn/config.py:130` | `get_password` | ssl_keyfile_password/get_password : paramètre TLS transmis à SSL, sans mot de passe codé en dur. | Faux positif |
| H-B-189 | 7 | `opt/venv/lib/python3.11/site-packages/uvicorn/config.py:290` | `ssl_keyfile_password` | ssl_keyfile_password/get_password : paramètre TLS transmis à SSL, sans mot de passe codé en dur. | Faux positif |
| H-B-190 | 7 | `opt/venv/lib/python3.11/site-packages/uvicorn/config.py:469` | `password` | ssl_keyfile_password/get_password : paramètre TLS transmis à SSL, sans mot de passe codé en dur. | Faux positif |
| H-B-191 | 7 | `opt/venv/lib/python3.11/site-packages/uvicorn/config.py:486` | `password` | ssl_keyfile_password/get_password : paramètre TLS transmis à SSL, sans mot de passe codé en dur. | Faux positif |
| H-B-192 | 7 | `opt/venv/lib/python3.11/site-packages/uvicorn/main.py:489` | `ssl_keyfile_password` | ssl_keyfile_password/get_password : paramètre TLS transmis à SSL, sans mot de passe codé en dur. | Faux positif |
| H-B-193 | 7 | `opt/venv/lib/python3.11/site-packages/uvicorn/main.py:602` | `ssl_keyfile_password` | ssl_keyfile_password/get_password : paramètre TLS transmis à SSL, sans mot de passe codé en dur. | Faux positif |
| G-B-194 | configuration/historique | `config.txt:1` | `GPG_KEY` | Empreinte de clé publique : vérification de la distribution Python par GPG. | Donnée publique |
| G-B-195 | configuration/historique | `config.txt:1` | `GPG_KEY` | Empreinte de clé publique : vérification de la distribution Python par GPG. | Donnée publique |
| G-B-196 | configuration/historique | `history.txt:16` | `GPG_KEY` | Empreinte de clé publique : vérification de la distribution Python par GPG. | Donnée publique |
| G-B-197 | configuration/historique | `inspect.txt:1` | `GPG_KEY` | Empreinte de clé publique : vérification de la distribution Python par GPG. | Donnée publique |

#### Frontend

| Alerte | Couche | Fichier:ligne | Nom de clé/champ ou symbole | Usage | Qualification |
|---|---|---|---|---|---|
| H-F-001 | 1 | `bin/busybox:2917` | `password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-F-002 | 1 | `bin/busybox:2917` | `password` | Chaîne de dialogue ou message système relatif à la saisie du mot de passe ; pas un identifiant. | Faux positif |
| H-F-003 | 2 | `usr/local/bin/node:113244` | `password` | password : code JavaScript interne de parsing d’URL ou validation de paramètre crypto embarqué dans Node. | Faux positif |
| H-F-004 | 2 | `usr/local/bin/node:114389` | `password` | password : code JavaScript interne de parsing d’URL ou validation de paramètre crypto embarqué dans Node. | Faux positif |
| H-F-005 | 2 | `usr/local/bin/node:183549` | `password` | password : code JavaScript interne de parsing d’URL ou validation de paramètre crypto embarqué dans Node. | Faux positif |
| H-F-006 | 2 | `usr/local/bin/node:183862` | `password` | password : code JavaScript interne de parsing d’URL ou validation de paramètre crypto embarqué dans Node. | Faux positif |
| G-F-007 | 2 | `usr/local/include/node/v8-internal.h:130` | `kApiTaggedSize` | kApiTaggedSize : constante de taille interne V8, pas une clé API. | Faux positif |
| G-F-008 | 2 | `usr/local/lib/node_modules/corepack/dist/lib/corepack.cjs:12981` | `key` | Clé publique ECDSA de vérification des signatures du registre npm ; algorithme et keytype publics dans le même objet. | Donnée publique |
| G-F-009 | 2 | `usr/local/lib/node_modules/corepack/dist/lib/corepack.cjs:12988` | `key` | Clé publique ECDSA de vérification des signatures du registre npm ; algorithme et keytype publics dans le même objet. | Donnée publique |
| H-F-010 | 2 | `usr/local/lib/node_modules/corepack/dist/lib/corepack.cjs:13148` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-011 | 2 | `usr/local/lib/node_modules/npm/docs/content/using-npm/config.md:1949` | `en-tête PRIVATE KEY` | Exemple PEM de documentation de l’option npm key ; contenu d’exemple, pas une clé privée complète. | Donnée publique |
| H-F-012 | 2 | `usr/local/lib/node_modules/npm/docs/output/using-npm/config.html:1552` | `en-tête PRIVATE KEY` | Exemple PEM de documentation de l’option npm key ; contenu d’exemple, pas une clé privée complète. | Donnée publique |
| H-F-013 | 2 | `usr/local/lib/node_modules/npm/lib/commands/profile.js:261` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-014 | 2 | `usr/local/lib/node_modules/npm/lib/commands/profile.js:264` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-015 | 2 | `usr/local/lib/node_modules/npm/lib/commands/profile.js:297` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-016 | 2 | `usr/local/lib/node_modules/npm/lib/commands/profile.js:378` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-017 | 2 | `usr/local/lib/node_modules/npm/lib/utils/read-user-info.js:64` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-018 | 2 | `usr/local/lib/node_modules/npm/man/man7/config.7:1962` | `en-tête PRIVATE KEY` | Exemple PEM de documentation de l’option npm key ; contenu d’exemple, pas une clé privée complète. | Donnée publique |
| G-F-019 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/arborist/README.md:44` | `auth` | Exemple documenté de configuration d’authentification npm ; aucune association à un compte du projet. | Donnée publique |
| H-F-020 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/arborist/README.md:47` | `password` | Exemple documenté de configuration d’authentification npm ; aucune association à un compte du projet. | Donnée publique |
| G-F-021 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/arborist/README.md:47` | `password` | Exemple documenté de configuration d’authentification npm ; aucune association à un compte du projet. | Donnée publique |
| G-F-022 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/arborist/README.md:52` | `_auth` | Exemple documenté de configuration d’authentification npm ; aucune association à un compte du projet. | Donnée publique |
| H-F-023 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/config/lib/definitions/definitions.js:1072` | `en-tête PRIVATE KEY` | Exemple PEM de documentation de l’option npm key ; contenu d’exemple, pas une clé privée complète. | Donnée publique |
| H-F-024 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/config/lib/index.js:848` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-025 | 2 | `usr/local/lib/node_modules/npm/node_modules/@npmcli/config/lib/index.js:859` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| G-F-026 | 2 | `usr/local/lib/node_modules/npm/node_modules/just-diff/index.cjs:84` | `obj1KeysLength` | obj1KeysLength/obj2KeysLength : nombre de propriétés des objets comparés. | Faux positif |
| G-F-027 | 2 | `usr/local/lib/node_modules/npm/node_modules/just-diff/index.cjs:86` | `obj2KeysLength` | obj1KeysLength/obj2KeysLength : nombre de propriétés des objets comparés. | Faux positif |
| G-F-028 | 2 | `usr/local/lib/node_modules/npm/node_modules/just-diff/index.mjs:79` | `obj1KeysLength` | obj1KeysLength/obj2KeysLength : nombre de propriétés des objets comparés. | Faux positif |
| G-F-029 | 2 | `usr/local/lib/node_modules/npm/node_modules/just-diff/index.mjs:81` | `obj2KeysLength` | obj1KeysLength/obj2KeysLength : nombre de propriétés des objets comparés. | Faux positif |
| H-F-030 | 2 | `usr/local/lib/node_modules/npm/node_modules/npm-profile/lib/index.js:146` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-031 | 2 | `usr/local/lib/node_modules/npm/node_modules/npm-profile/lib/index.js:165` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-032 | 2 | `usr/local/lib/node_modules/npm/node_modules/npm-profile/lib/index.js:204` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-033 | 2 | `usr/local/lib/node_modules/npm/node_modules/npm-profile/lib/index.js:243` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-034 | 2 | `usr/local/lib/node_modules/npm/node_modules/npm-registry-fetch/lib/auth.js:94` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-035 | 2 | `usr/local/lib/node_modules/npm/node_modules/socks/build/client/socksclient.js:541` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-036 | 3 | `opt/yarn-v1.22.22/lib/cli.js:32035` | `password` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-037 | 3 | `opt/yarn-v1.22.22/lib/cli.js:33203` | `getOneTimePassword` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| H-F-038 | 3 | `opt/yarn-v1.22.22/lib/cli.js:94448` | `incorrectOneTimePassword` | password/oneTimePassword : saisie, option, variable d’environnement ou message du gestionnaire de paquets ; aucune constante secrète. | Faux positif |
| G-F-039 | 6 | `app/.next/prerender-manifest.json:151` | `previewModeSigningKey` | Signature JWT des données Preview Pages Router ; aucun endpoint métier d’activation identifié. | Secret généré ; activité non établie |
| G-F-040 | 6 | `app/.next/prerender-manifest.json:152` | `previewModeEncryptionKey` | Déchiffrement des données Preview Pages Router ; aucun endpoint métier d’activation identifié. | Secret généré ; activité non établie |
| H-F-041 | 6 | `app/.next/server/chunks/[root-of-the-server]__15bjnu5yieigz._.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-042 | 6 | `app/.next/server/chunks/_0a1lbvv1uz_op._.js:59` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| G-F-043 | 6 | `app/.next/server/preview-props.json:3` | `previewModeSigningKey` | Signature JWT des données Preview Pages Router ; aucun endpoint métier d’activation identifié. | Secret généré ; activité non établie |
| G-F-044 | 6 | `app/.next/server/preview-props.json:4` | `previewModeEncryptionKey` | Déchiffrement des données Preview Pages Router ; aucun endpoint métier d’activation identifié. | Secret généré ; activité non établie |
| G-F-045 | 6 | `app/.next/server/server-reference-manifest.json:4` | `encryptionKey` | AES des captures de Server Actions ; manifestes node/edge vides, aucun appel métier établi. | Secret généré ; activité non établie |
| H-F-046 | 6 | `app/node_modules/next/dist/compiled/@edge-runtime/primitives/url.js.text.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-047 | 6 | `app/node_modules/next/dist/compiled/@edge-runtime/primitives/url.js.text.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-048 | 6 | `app/node_modules/next/dist/compiled/@edge-runtime/primitives/url.js.text.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-049 | 6 | `app/node_modules/next/dist/compiled/@mswjs/interceptors/ClientRequest/index.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-050 | 6 | `app/node_modules/next/dist/compiled/edge-runtime/index.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-051 | 6 | `app/node_modules/next/dist/compiled/edge-runtime/index.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-052 | 6 | `app/node_modules/next/dist/compiled/edge-runtime/index.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| G-F-053 | 6 | `app/node_modules/next/dist/compiled/fast-jwt/index.js:1` | `t.tokenizeClass` | tokenizeClass : export du parseur de code, sans jeton JWT ni clé embarqués. | Faux positif |
| H-F-054 | 6 | `app/node_modules/next/dist/compiled/next-server/app-page-turbo-experimental.runtime.prod.js:15` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-055 | 6 | `app/node_modules/next/dist/compiled/next-server/app-page-turbo.runtime.prod.js:15` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-056 | 6 | `app/node_modules/next/dist/compiled/next-server/app-route-turbo.runtime.prod.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-057 | 6 | `app/node_modules/next/dist/compiled/next-server/pages-turbo.runtime.prod.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-058 | 6 | `app/node_modules/next/dist/server/web/next-url.js:180` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-059 | 6 | `app/node_modules/next/dist/shared/lib/router/utils/parse-url.js:19` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-060 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `getPassword` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-061 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-062 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-063 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-064 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-065 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-066 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `password` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |
| H-F-067 | 7 | `app/.next/static/chunks/0cz1d0mv5g_q7.js:1` | `setPassword` | password/getPassword/setPassword : copie, parsing ou sérialisation d’URL dans le runtime ou son polyfill ; aucune valeur secrète constante. | Faux positif |

Lors de cette qualification historique : aucun tag ECR modifié, aucun commit ni push effectué.
