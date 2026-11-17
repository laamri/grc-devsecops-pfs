
# CI - GovernSecOps

## 1. Objectif

Mettre en place une integration continue automatisee
avec GitHub Actions pour le projet GovernSecOps.

References Jira : SCRUM-15 (US09), SCRUM-18 (US10) et SCRUM-27 (US14).

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

## 4. Étapes du pipeline

1. Récupération du code source.
2. Installation des dépendances Python et Node.js.
3. Lint ciblé et tests pytest pour Auth Service et Task Service.
4. Lint et build Next.js.
5. Publication des rapports JUnit et des journaux de validation comme artefacts.
6. Scans de secrets et de dépendances avec seuils bloquants.

Chaque push et chaque pull request vers `main` ou `develop` exécute ces contrôles. Un échec arrête le job concerné et le statut apparaît sur le commit.

Les services backend produisent un rapport JUnit par service. Le frontend ne contient pas encore de suite de tests dédiée, donc le pipeline exécute le lint ESLint et le build Next.js comme validations applicatives et publie leurs journaux. Une suite de tests frontend pourra être ajoutée sans modifier le contrat des artefacts.

## 4.1 Analyse de sécurité

Le job `security-scan` récupère l’historique Git complet puis exécute Gitleaks sur le dépôt. Il exécute également Trivy en mode filesystem avec les dépendances directes et transitives des fichiers `requirements.txt` et `package-lock.json`. Une vulnérabilité HIGH ou CRITICAL connue et corrigée bloque le job. Les rapports disponibles sont publiés dans l’artefact `security-scan-reports` même lorsque le job échoue.

Le scénario de validation d’un secret factice se fait dans une branche ou une copie de test temporaire. Ajouter une valeur synthétique reconnue par Gitleaks, pousser la branche, vérifier l’échec du job et supprimer la valeur sans la fusionner. La valeur ne doit jamais être un identifiant réel. Une dérogation pour faux positif doit être limitée à une ligne nécessaire, justifiée, approuvée et réévaluée avec une date d’expiration. Une dérogation ne doit pas supprimer le scan global ni abaisser le seuil HIGH/CRITICAL.


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
