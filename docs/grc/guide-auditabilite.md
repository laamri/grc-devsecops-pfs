# Guide d’auditabilité interne

[SCRUM-29 (US30)](https://uca-team-o1mjbk8j.atlassian.net/browse/SCRUM-29) · Sprint 0 · Révision initiale du 8 novembre 2026

Ce guide accompagne la [matrice des contrôles](matrice-controles.md) et le [registre des risques](registre-risques.md). Il permet de refaire une vérification et de retrouver la preuve correspondant à une version de l’application ou de l’infrastructure. Les références externes décrivent les résultats de sécurité et les mécanismes utilisés. L’évaluation porte sur les scénarios du projet et alimente sa revue interne.

## Préparer une vérification

1. Choisir le contrôle et relever son identifiant `Cxx`, les risques `Rxx` associés, le périmètre et le résultat attendu.
2. Relever le commit applicatif et GitOps ou le digest d’image, les versions des outils, et le compte ou cluster, le namespace et la région de test concernés. Utiliser un environnement isolé et des données synthétiques pour les tests de refus, les images vulnérables et les restaurations.
3. Fixer les seuils qui s’appliquent à la vérification avant de l’exécuter. Pour les scans, consigner les seuils et exceptions approuvés dans la politique de livraison. Pour la restauration, consigner la perte de données et la durée d’interruption maximales admises (RPO et RTO). Si le seuil requis reste à définir, l’évaluation reste **À vérifier**.
4. Exécuter les cas autorisés et refusés prévus par la matrice. Conserver la version de la configuration et les résultats qui expliquent le verdict. Si un résultat doit être comparé à une mesure antérieure, conserver aussi la preuve de référence.

## Indexer et conserver les preuves

Le référent GRC propose un espace partagé à accès restreint et en confirme le lien et la rétention avec l’équipe. Utiliser `grc/PFS/<environnement>/<AAAA-MM-JJ>/<Cxx>/` sous cette racine. Par exemple, `grc/PFS/test/2026-11-08/C06/` désigne l’emplacement proposé de l’index pour le contrôle C06. Les chemins de la matrice se terminant par `Cxx/` sont relatifs à l’environnement et à la date de la vérification.

Pour chaque contrôle évalué, enregistrer une ligne dans l’index avec les éléments suivants.

| Champ | À consigner |
| --- | --- |
| Références | Identifiants du contrôle et des risques, version de la procédure et référence externe utilisée |
| Contexte | Date et heure avec fuseau, environnement, commit ou digest, configuration, outil et version |
| Vérification | Exécutant, procédure ou lien vers le job, cas de test, seuil et résultat attendu |
| Résultat | Observation réelle, statut, justification et anomalie éventuelle |
| Preuves | Lien stable vers la PR, l’exécution, le journal ou le rapport, et copie expurgée si l’outil source ne garde pas la preuve assez longtemps |
| Suivi | Référent du contrôle, relecteur, échéance et lien Jira de l’écart ou de la dérogation |

Conserver le résultat et l’identifiant de l’exécution, mais retirer les JWT, mots de passe, clés, chaînes de connexion et données personnelles. Garder les sauvegardes et les états Terraform dans leurs espaces de stockage dédiés et référencer uniquement les métadonnées et résultats de test dans l’index.

## Interpréter les résultats

| Statut | Règle |
| --- | --- |
| À vérifier | Le contrôle est prévu, un prérequis manque, ou la preuve disponible est insuffisante. Indiquer ce qui manque et le responsable. |
| Satisfait | Les cas attendus ont réussi dans le périmètre déclaré et des preuves permettent à un tiers de revoir le résultat. |
| Non satisfait | Une vérification a révélé un écart. Consigner l’observation et ouvrir un suivi avec un responsable et une échéance. |
| Non applicable | Le référent GRC et le responsable technique valident la justification et la limite de périmètre. |

La CI initiale documentée sur `develop` ne couvre que des vérifications de structure et une démonstration de masquage. Un résultat vert de cette CI ne prouve pas à lui seul le blocage d’une vulnérabilité ou d’une fuite. Pour C06, par exemple, le rapport Trivy doit être accompagné de l’état du job de publication et de la vérification du digest dans ECR.

Pour la comparaison avant/après, appliquer le même test dans des conditions comparables, garder les deux liens de preuve et dater les résultats. Réévaluer ensuite la vraisemblance et l’impact résiduels avec les échelles de SCRUM-17. Toute dérogation consigne le contrôle, le risque résiduel, le motif, la mesure compensatoire, le décideur et la date d’expiration.

## Revue des parties prenantes

Le référent GRC présente la matrice aux référents application, CI/CD, infrastructure, données et exploitation. Pour chaque risque élevé ou critique, les relecteurs confirment la pertinence des contrôles, les responsables, les conditions de réussite et l’accès aux preuves. Ils consignent les décisions, les écarts, les échéances et l’emplacement de l’index. Enregistrer dans SCRUM-29 la révision revue et la décision des parties prenantes. État à la création de la matrice **revue à réaliser**.

## Références

- NIST CSF 2.0, NIST CSWP 29, février 2024, annexe A. Les identifiants de la matrice désignent des résultats de sécurité ciblés. [NIST](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf)
- C01, C05 et C07. Paramètres de confiance GitHub Actions vers AWS, contrôles de branches et immuabilité des tags. [GitHub OIDC](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), [GitHub branches protégées](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [AWS ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html)
- C09. OWASP API Security Top 10, édition 2023, API1, autorisation au niveau des objets. [OWASP API1:2023](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
- C10 et C11. Exports et restauration d’une instance MongoDB autogérée. [MongoDB Database Tools](https://www.mongodb.com/docs/v8.0/tutorial/backup-and-restore-tools/)
- C12 à C15 et C18. Limitation des accès, RBAC, admission, segmentation et journalisation. Si l’équipe sélectionne une recommandation du CIS Benchmark EKS, relever son édition et son identifiant avec le résultat de la vérification. [AWS EKS réseau](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [Kubernetes Pod Security](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [AWS EKS audit](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)
- C17. Stockage distant, versionnement et verrouillage de l’état. [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
