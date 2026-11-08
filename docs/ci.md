
# CI - GovernSecOps

## 1. Objectif

Mettre en place une integration continue automatisee
avec GitHub Actions pour le projet GovernSecOps.

Reference Jira : SCRUM-15 (US09).

## 2. Moteur CI

- Outil : GitHub Actions
- Depot : laamri/grc-devsecops-pfs
- Workflow : .github/workflows/ci.yml
- Runner : ubuntu-latest

## 3. Declencheurs

Le pipeline se lance automatiquement :
- Lors d'un push sur une branche.
- Lors de l'ouverture d'une Pull Request.
- Lors de sa mise a jour ou de sa reouverture.

Un declenchement manuel est aussi configure via
workflow_dispatch, une fois le workflow present
sur la branche par defaut.

## 4. Etapes du pipeline

1. Recuperation du code source.
2. Verification de la structure du depot.
3. Test de masquage d'un secret fictif sur push.
4. Confirmation de la fin du pipeline.

Les tests applicatifs seront integres lorsque
les composants du projet seront disponibles.

## 5. Gestion des secrets

Les secrets sont stockes dans :
Settings > Secrets and variables > Actions

Secret de demonstration : US09_DEMO_SECRET

Les valeurs sensibles ne doivent jamais etre
enregistrees en clair dans les fichiers YAML.

Le test de journalisation utilise uniquement
une valeur fictive, jamais un vrai identifiant.

## 6. Acces aux executions

Ouvrir le depot GitHub, puis l'onglet Actions.
Selectionner le workflow "US09 - CI initiale".
Ouvrir une execution pour consulter les jobs
et les journaux.

L'acces depend des permissions GitHub
de chaque membre de l'equipe.

## 7. Criteres de validation

- Pipeline declenche automatiquement apres un push.
- Pipeline declenche lors d'une Pull Request.
- Definition du workflow versionnee dans Git.
- Secret fictif masque dans les journaux.
- Aucun identifiant sensible en clair.

## 8. Limites actuelles

Ce workflow valide l'integration initiale.
Il n'effectue pas encore de build applicatif,
de tests unitaires ou de scans de securite.
Ces controles seront ajoutes progressivement.
