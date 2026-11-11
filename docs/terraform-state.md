# US02 — État distant Terraform

## Objectif

Partager un état Terraform protégé entre les membres autorisés de
l’équipe : Oussama, Sayf et L7sen.

## Configuration

| Paramètre | Valeur |
|---|---|
| Compte AWS | 132415609490 |
| Région | eu-north-1 |
| Bucket S3 | pfs-tfstate-132415609490-eu-north-1 |
| Chemin de l’état | dev/terraform.tfstate |
| Terraform | 1.15.8 |
| Provider AWS | 6.69.1 |
| Chiffrement | SSE-S3 / AES256 |
| Versioning | Activé |
| Accès publics | Quatre options de blocage activées |
| HTTPS | Imposé par la politique DenyInsecureTransport |
| Verrouillage | S3 natif avec use_lockfile = true |

Le bucket a été créé avec AWS CLI avant l’initialisation du backend.
Il n’est pas géré par les ressources de cette configuration Terraform.

La politique HTTPS est conservée dans :
`infra/terraform/s3-bucket-policy.json`.

## Fichiers du projet

- `versions.tf` : versions de Terraform et du provider AWS.
- `providers.tf` : configuration du provider AWS.
- `variables.tf` : paramètres de configuration.
- `backend.tf` : emplacement et protection de l’état distant.
- `outputs.tf` : nom du projet enregistré dans l’état.
- `.terraform.lock.hcl` : version et empreintes du provider.
- `s3-bucket-policy.json` : politique refusant les accès HTTP.

Ces fichiers se trouvent dans `infra/terraform/`.

## Authentification

Chaque membre doit utiliser sa propre identité AWS autorisée.
Aucune clé ni aucun jeton ne doit être enregistré dans le dépôt.

Exemple avec le profil local `pfs-dev` :

```powershell
aws login --profile pfs-dev --region eu-north-1
aws configure set region eu-north-1 --profile pfs-dev
aws sts get-caller-identity --profile pfs-dev
```

Vérifier que le compte retourné est `132415609490`.

Dans chaque nouvelle session PowerShell destinée à Terraform :

```powershell
$env:AWS_PROFILE = "pfs-dev"
```

Lorsque la session AWS expire, relancer `aws login`.

Le profil utilisé pour les tests possède actuellement le rôle
`AccountFullAccessRole`. La limitation de ses permissions reste
à finaliser.

## Initialisation et validation

Depuis la racine du dépôt :

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -lock-timeout=30s
```

Examiner le plan avant toute exécution de `terraform apply`.

Conserver `.terraform.lock.hcl` dans Git.
Ne jamais publier le dossier `.terraform/`, les états Terraform,
les plans ou les fichiers contenant des secrets.

Ne pas utiliser `init -reconfigure` pour migrer un état existant :
une migration nécessite une procédure distincte.

## Vérifications réalisées le 10 novembre 2026

- Initialisation du backend S3 réussie.
- Vérification du format et validation réussies.
- Écriture de l’output `project_name` dans l’état distant réussie.
- Aucune ressource applicative créée, modifiée ou détruite par cet apply.
- Objet d’état présent avec chiffrement AES256 et un VersionId.
- Blocage d’une opération concurrente avec
  `Error acquiring the state lock` pendant un apply en attente.
- Après annulation de cet apply, libération du verrou et plan réussi.
- Accès anonyme aux métadonnées de l’état refusé : HTTP 403.
- Accès depuis le compte externe `712481457733` refusé : HTTP 403.

Les tests d’accès ont utilisé `HeadObject`. Ils vérifient le refus
d’accès aux métadonnées de l’objet pour les identités testées.

## Gestion du verrouillage

Un verrou actif protège une opération en cours.
Attendre sa fin plutôt que désactiver le verrouillage.

Ne pas utiliser `force-unlock` sans vérifier que l’opération
propriétaire du verrou est réellement arrêtée.

Le versioning S3 conserve les versions successives de l’état.
Restaurer une version de l’état ne restaure pas automatiquement
les ressources AWS correspondantes.

## Analyse des secrets — 11 novembre 2026

Outil utilisé : Gitleaks 8.30.1.

```powershell
gitleaks git --staged --redact .
gitleaks git --log-opts="--all" --redact .
```

Résultats obtenus avant la finalisation de cette documentation :

- Modifications préparées : environ 5,85 Ko analysés,
  aucun secret détecté.
- Historique Git local : 12 commits analysés,
  aucun secret détecté.
- Aucun nom de fichier correspondant aux motifs sensibles recherchés
  n’a été trouvé dans l’historique local.

Ces contrôles réduisent le risque de publication de secrets,
sans constituer une garantie absolue.

## Points restant à finaliser

- Définir et tester des permissions limitées au besoin,
  en remplacement de l’usage courant d’AccountFullAccessRole.
- Vérifier l’accès avec les identités des autres membres.
- Faire relire et fusionner la Pull Request vers develop.

## État de la livraison

Le backend distant et les tests décrits ci-dessus sont opérationnels.
US02 reste en cours tant que les points restants ne sont pas validés.