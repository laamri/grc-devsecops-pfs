# Registre initial des risques

[SCRUM-17 (US29)](https://uca-team-o1mjbk8j.atlassian.net/browse/SCRUM-17) · Sprint 0 · Révision initiale du 8 novembre 2026

Les identifiants d’actifs renvoient à l’[inventaire du périmètre](perimetre.md). Les scores décrivent le risque inhérent sur la cible, avant de créditer les contrôles. Les estimations sont proposées pour revue par l’équipe. La méthode de priorisation s’appuie sur les résultats ID.RA-03 à ID.RA-06 du [NIST CSF 2.0, annexe A](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf).

## Échelles de cotation

| Note | Vraisemblance (V) | Impact (I) |
| --- | --- | --- |
| 1 | Exceptionnelle. Plusieurs conditions indépendantes sont nécessaires et l’exposition est très faible. | Négligeable. Effet local et réversible sans perte de données ni interruption significative. |
| 2 | Peu probable. Le scénario requiert un accès restreint ou une erreur inhabituelle. | Limité. Effet circonscrit à un composant ou à un petit lot de données de test. |
| 3 | Plausible. Une erreur de configuration ou un accès déjà détenu suffit. | Significatif. Un service, une partie des données ou une livraison est affecté et nécessite une intervention. |
| 4 | Probable. Le chemin est régulièrement exposé à du code, du trafic ou des changements. | Majeur. Accès à des données d’autres utilisateurs, blocage de la livraison ou compromission d’un composant central. |
| 5 | Très probable. Le déclencheur se présente régulièrement et le scénario exige peu de prérequis. | Critique. Prise de contrôle de la chaîne ou du compte, fuite de secrets permettant un accès étendu, ou perte irrécupérable des données. |

### Matrice de criticité (V × I)

| V \ I | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | 2 | 3 | 4 | 5 |
| 2 | 2 | 4 | 6 | 8 | 10 |
| 3 | 3 | 6 | 9 | 12 | 15 |
| 4 | 4 | 8 | 12 | 16 | 20 |
| 5 | 5 | 10 | 15 | 20 | 25 |

**Faible** 1–4 · **Modéré** 5–9 · **Élevé** 10–15 · **Critique** 16–25.

Le tri se fait par score décroissant, puis par impact décroissant et identifiant croissant. Les cinq premières lignes sont prioritaires. Le traitement proposé indique s’il faut réduire le risque par des contrôles, l’accepter par décision documentée, le transférer à un tiers ou éviter l’activité exposée. Revoir les notes après une évolution d’architecture, un incident ou une vérification de contrôle, en conservant la cotation initiale pour la comparaison.

## Registre trié

| ID | Priorité | Actifs | Menace et conséquence | V | I | Score et niveau | Traitement proposé | Responsable proposé |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R01 | P1 | A04, A05, A08 | Un workflow issu d’une branche ou d’une PR non approuvée assume un rôle AWS trop large et modifie les images ou l’infrastructure. Les workflows sont fréquemment déclenchés. | 4 | 5 | 20 · Critique | Réduire. Borner la confiance OIDC au contexte de publication autorisé, séparer les rôles de publication et d’infrastructure, limiter les droits aux ressources nécessaires. | Référent infrastructure AWS |
| R02 | P2 | A03, A04, A08 | Un secret JWT, MongoDB ou AWS est copié dans Git, un manifeste ou un journal. Sa réutilisation peut ouvrir l’accès aux services ou aux données. Chaque changement de code ou de configuration offre une occasion de fuite. | 4 | 5 | 20 · Critique | Réduire. Stocker les secrets dans les mécanismes dédiés, scanner Git et les changements, vérifier le masquage et prévoir la rotation. | Référent sécurité |
| R03 | P3 | A03, A04, A05, A07 | Une dépendance ou une image à risque franchit la chaîne de livraison à cause d’un scan facultatif, d’un échec ignoré ou d’un tag mutable. L’image livrée peut compromettre un service. | 4 | 4 | 16 · Critique | Réduire. Rendre les seuils de scans bloquants avant publication, protéger les branches et référencer dans GitOps le digest validé. | Référent CI/CD |
| R04 | P4 | A01, A02 | Un utilisateur authentifié devine l’identifiant d’une tâche, ou fournit un `userId` arbitraire, et lit, modifie ou supprime les données d’un autre utilisateur. Les routes sont exposées en continu. | 4 | 4 | 16 · Critique | Réduire. Vérifier le JWT et imposer le filtrage par propriétaire sur chaque opération. Couvrir les cas intercomptes par des tests. | Équipe application |
| R05 | P5 | A02, A10 | Une suppression, une erreur de déploiement ou la perte du volume EBS rend MongoDB indisponible. Sans export exploitable, les comptes et tâches peuvent être irrécupérables. | 3 | 5 | 15 · Élevé | Réduire. Produire des sauvegardes chiffrées hors du volume source et restaurer régulièrement les deux bases dans une cible isolée. | Référent données |
| R06 |  | A07, A08, A09 | Une interface d’administration accessible depuis un réseau non approuvé, ou un rôle trop permissif, permet de piloter le déploiement ou de lire les ressources d’un namespace. | 3 | 4 | 12 · Élevé | Réduire. Restreindre l’accès réseau et appliquer des rôles IAM/RBAC limités et vérifiés. | Référent Kubernetes |
| R07 |  | A07 | Une erreur dans un manifeste autorise un pod privilégié ou monté sur l’hôte. Un workload compromis peut alors atteindre le nœud ou d’autres charges. | 3 | 4 | 12 · Élevé | Réduire. Appliquer un profil Pod Security Admission aux namespaces applicatifs et tester le refus d’un pod non conforme. | Référent Kubernetes |
| R08 |  | A02, A07, A08 | Un pod non autorisé atteint MongoDB faute d’isolation. Un compte partagé ou trop large étend l’accès aux deux bases. | 3 | 4 | 12 · Élevé | Réduire. Limiter les flux réseau avec un refus par défaut et des autorisations ciblées. Isoler les droits des comptes MongoDB par base. | Référent données |
| R09 |  | A03, A06, A08 | Un état ou un plan Terraform est exposé ou modifié par un tiers ayant accès au stockage ou à Git. La fuite peut révéler des valeurs sensibles et la modification peut fausser les changements AWS. | 2 | 5 | 10 · Élevé | Réduire. Isoler, chiffrer, versionner et verrouiller l’état distant. Exclure les états et les plans de Git et limiter l’accès aux personnes et workflows autorisés. | Référent infrastructure AWS |
| R10 |  | A04, A07, A09 | Une action privilégiée ou une panne reste invisible faute de journaux exploitables ou d’alerte routée, ce qui retarde l’intervention. | 3 | 3 | 9 · Modéré | Réduire. Collecter les événements AWS/EKS, tester une alerte de supervision et attribuer un destinataire responsable. | Référent exploitation |
