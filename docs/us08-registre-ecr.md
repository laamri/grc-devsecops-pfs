# US08 — Versionner et publier les images dans Amazon ECR

## Version publiée

La version `1.0.0` provient du commit `e1a8453d9189e4961f546debef4f176a5353bd95`.
Les deux dépôts privés utilisent le mode `IMMUTABLE`. Chaque image porte deux tags :
`sha-e1a8453d9189` pour retrouver le commit source et `1.0.0` pour identifier la version livrée.

Registre : `132415609490.dkr.ecr.eu-north-1.amazonaws.com`

| Dépôt | Utilisation | Digest confirmé par ECR |
|---|---|---|
| `pfs-backend` | Image commune aux API Auth et Task | `sha256:7e1f0ab6f82f4a6fde888450d5aac7507f6ff182e965c4720726208af56ca7ba` |
| `pfs-frontend` | Interface Next.js | `sha256:6c922314f22f3a5019820a9a3a9ea93b25e8c895ea9ef1673d59c7c1b8be2f0f` |

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

## Construire, taguer et publier une nouvelle version

Depuis la racine du dépôt, utiliser un commit propre et choisir une version sémantique
encore disponible dans les deux dépôts. La version `1.0.0` est déjà publiée.

```powershell
$registry = '132415609490.dkr.ecr.eu-north-1.amazonaws.com'
$version = Read-Host 'Nouvelle version au format X.Y.Z'
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version invalide' }
if (git status --porcelain) { throw 'Enregistrer les changements avant le build' }
$sha = git rev-parse HEAD
$tag = "sha-$(git rev-parse --short=12 HEAD)"

docker build --label "org.opencontainers.image.revision=$sha" -t "$registry/pfs-backend:$tag" -f backend/Dockerfile .
if ($LASTEXITCODE -ne 0) { throw 'Échec du build backend' }

docker build --label "org.opencontainers.image.revision=$sha" -t "$registry/pfs-frontend:$tag" ./frontend
if ($LASTEXITCODE -ne 0) { throw 'Échec du build frontend' }

foreach ($repo in 'pfs-backend', 'pfs-frontend') {
    docker tag "$registry/${repo}:$tag" "$registry/${repo}:$version"
    if ($LASTEXITCODE -ne 0) { throw "Échec du tag pour $repo" }

    foreach ($ref in $tag, $version) {
        docker push "$registry/${repo}:$ref"
        if ($LASTEXITCODE -ne 0) { throw "Échec du push pour ${repo}:$ref" }
    }
}
```

## Vérification de la publication

Pour la version `1.0.0`, cette vérification a renvoyé, dans chaque dépôt, les deux tags
sur le même digest. Les valeurs observées figurent dans le tableau ci-dessus.

```powershell
foreach ($repo in 'pfs-backend', 'pfs-frontend') {
    Write-Host $repo
    aws ecr describe-images --repository-name $repo --image-ids imageTag=sha-e1a8453d9189 imageTag=1.0.0 --profile pfs-dev --region eu-north-1 --query 'imageDetails[].{Tags:imageTags,Digest:imageDigest}' --output json --no-cli-pager
}
```

## Contrôle des secrets

La publication et les digests sont confirmés. La preuve de contrôle des secrets pour
ces deux digests reste à joindre. Vérifier la configuration, l’historique de construction
et le contenu des couches avec le contrôle du projet. Consigner la date, l’outil,
les digests examinés et le résultat, en masquant toute valeur sensible.
