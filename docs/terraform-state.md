# US02 — État distant Terraform

## Objectif

Partager un état Terraform protégé entre les membres autorisés de
l’équipe : Oussama, Sayf et L7sen.

## Configuration

- Compte AWS : 132415609490
- Région : eu-north-1
- Bucket : pfs-tfstate-132415609490-eu-north-1
- Chemin de l’état : dev/terraform.tfstate
- Terraform : 1.15.8
- Provider AWS : 6.69.1
- Chiffrement : SSE-S3 / AES256
- Versioning : activé
- Accès publics : quatre options de blocage activées
- HTTPS : imposé par la politique DenyInsecureTransport
- Verrouillage : S3 natif avec use_lockfile = true

Le bucket a été créé avec AWS CLI avant l’initialisation du backend.
Il n’est pas actuellement géré par les ressources de cette configuration
Terraform. La politique HTTPS est conservée dans
infra/terraform/s3-bucket-policy.json.

## Authentification

Chaque membre utilise sa propre identité AWS autorisée.
Aucune clé ni aucun jeton ne doit être enregistré dans le dépôt.

Exemple avec le profil local pfs-dev :

    aws login --profile pfs-dev --region eu-north-1
    aws configure set region eu-north-1 --profile pfs-dev
    aws sts get-caller-identity --profile pfs-dev

Vérifier que le compte retourné est 132415609490.

Dans PowerShell, sélectionner le profil pour Terraform :

    $env:AWS_PROFILE = "pfs-dev"

Lorsque la session expire, relancer aws login.

## Initialisation et validation

Depuis la racine du dépôt :

    terraform -chdir=infra/terraform init
    terraform -chdir=infra/terraform fmt -check
    terraform -chdir=infra/terraform validate
    terraform -chdir=infra/terraform plan -lock-timeout=30s

Conserver .terraform.lock.hcl dans Git.
Ne jamais publier .terraform/, les états, les plans ou les secrets.

Ne pas utiliser init -reconfigure pour migrer un état existant :
une migration nécessite une procédure distincte.

## Vérifications réalisées le 10 novembre 2026

- Initialisation du backend S3 réussie.
- Vérification du format et validation réussies.
- Écriture de l’output project_name dans l’état distant réussie.
- Objet d’état présent avec chiffrement AES256 et VersionId.
- Une opération concurrente a échoué avec
  « Error acquiring the state lock » pendant un apply en attente.
- Après annulation de cet apply, le plan a réussi.
- Accès anonyme aux métadonnées de l’état refusé : HTTP 403.
- Accès depuis le compte externe 712481457733 refusé : HTTP 403.

Ces tests d’accès ont utilisé HeadObject.

## Gestion du verrouillage

Un verrou actif protège une opération en cours.
Attendre sa fin plutôt que désactiver le verrouillage.

Ne pas utiliser force-unlock sans vérifier que l’opération propriétaire
du verrou est réellement arrêtée.

## Points restant à finaliser

- Le profil testé utilise AccountFullAccessRole :
  des permissions limitées au besoin restent à définir.
- Vérifier l’accès avec les identités des autres membres.
- Analyser le contenu et l’historique Git pour rechercher des secrets.
  Le contrôle effectué jusqu’ici portait uniquement sur les noms
  de fichiers sensibles.
- Faire relire et fusionner la Pull Request vers develop.