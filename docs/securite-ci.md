# Sécurité de la Pipeline CI/CD (`grc-devsecops-pfs`)

Ce document décrit les contrôles de sécurité automatisés intégrés dans la pipeline GitHub Actions (`.github/workflows/ci.yml`), les outils retenus ainsi que les seuils de la **Quality Gate** permettant de bloquer toute fusion vers `main` ou `develop` en cas de vulnérabilité critique.

---

## 1. Vue d'ensemble des contrôles de sécurité CI

| Type d'analyse | Outil | Périmètre analysé | Rapport généré |
| :--- | :--- | :--- | :--- |
| **Détection de secrets** | **Gitleaks** | Historique Git et fichiers du dépôt | `gitleaks-report.json` / `gitleaks.sarif` |
| **Analyse des dépendances (SCA)** | **Trivy** | Dépendances OS et bibliothèques applicatives | `trivy-results.sarif` |
| **Analyse statique du code (SAST)** | **Semgrep** | Code source Backend (Python/FastAPI) et Frontend (TypeScript/React) | `semgrep-results.sarif` |

---

## 2. Analyse Statique du Code (SAST) — Choix de l'outil

### Outil retenu : **Semgrep** (`semgrep/semgrep`)
**Justification technique :**
* **Exécution légère sans infrastructure externe :** Semgrep s'exécute directement via son image officielle dans un runner GitHub Actions (~20 secondes) sans nécessiter de serveur dédié ni de base de données externe (contrairement à SonarQube).
* **Couverture multi-stack unifiée :** Analyse en une seule passe l'ensemble des microservices FastAPI (`auth_service`, `task_service`) et le frontend Next.js (`frontend`).
* **Règles orientées sécurité & GRC :** Utilise les jeux de règles maintenus `p/python`, `p/fastapi`, `p/typescript`, `p/react` et `p/owasp-top-ten`, tout en permettant l'ajout futur de règles personnalisées en YAML.

---

## 3. Seuils de la Quality Gate (Critères de blocage)

La job **`SAST Code Analysis (Semgrep)`** applique une Quality Gate stricte via les options `--severity ERROR --error` :

| Niveau de sévérité Semgrep | Équivalence risque | Comportement de la Quality Gate | Action requise |
| :--- | :--- | :--- | :--- |
| **`ERROR`** | **Critique / Élevée** (ex. Injection SQL, exécution de commande `shell=True`, XSS, désérialisation non sécurisée) | **BLOQUANT (Échec du pipeline — exit code 1)** | Correction obligatoire avant merge |
| **`WARNING`** | **Moyenne** (mauvaises pratiques de sécurité) | **Non bloquant** (consigné dans le rapport) | À corriger dans le backlog technique |
| **`INFO`** | **Faible / Informatif** | **Non bloquant** (consigné dans le rapport) | Revue périodique |

* **Règle d'or :** **0 vulnérabilité de sévérité `ERROR` (Critique/Élevée)** autorisée pour valider la Quality Gate.

---

## 4. Consultation des rapports d'analyse

À chaque exécution de la pipeline (même en cas d'échec de la Quality Gate grâce à `if: always()`), le rapport complet au format standard **SARIF** est publié dans l'onglet **Actions** de GitHub :
1. Ouvrir l'exécution du workflow **`DevSecOps PFS - CI Pipeline`** dans l'onglet **Actions**.
2. Descendre jusqu'à la section **Artifacts**.
3. Télécharger l'archive **`sast-semgrep-report`** contenant le fichier **`semgrep-results.sarif`** (consultable directement ou via l'extension *SARIF Viewer* dans VS Code).