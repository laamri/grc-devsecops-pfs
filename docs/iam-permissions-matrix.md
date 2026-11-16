# US03 — Matrice des Permissions IAM (Principe du Moindre Privilège)

## 1. Contexte et Objectif

Dans le cadre de l'US02, le profil de test utilisait `AccountFullAccessRole`. L'objectif de cette matrice est de remplacer cet accès étendu par **trois identités IAM dédiées et cloisonnées** pour l'équipe (Oussama, Sayf, L7sen), le cluster et le pipeline CI/CD.

---

## 2. Matrice des Identités et Permissions

| Identité / Rôle IAM | Entité Autorisée à Assumer le Rôle | Périmètre d'Actions Autorisées (Allow) | Actions Explicitement Interdites / Hors Périmètre (Deny par défaut) |
| :--- | :--- | :--- | :--- |
| **`safeops-terraform-role`** | Membres de l'équipe DevSecOps (Oussama, Sayf, L7sen) via SSO / `aws login` | • **Réseau (`ec2:*`) :** Création/modification/suppression uniquement des VPC, Subnets, IGW, NAT, Route Tables et Security Groups du projet.<br>• **IAM (`iam:*`) :** Gestion des rôles et politiques préfixés par `safeops-*`.<br>• **État Terraform (`s3:*`) :** Lecture/écriture/verrouillage sur `arn:aws:s3:::pfs-tfstate-132415609490-eu-north-1/*`. | • Modification de la facturation AWS (`aws-portal:*`).<br>• Suppression du compte ou modification des politiques racines.<br>• Accès aux données applicatives de production. |
| **`safeops-cluster-role`** | Nœuds de calcul du cluster (EC2 / EKS Worker Nodes) | • **Registre Conteneurs (`ecr:*`) :** `GetAuthorizationToken`, `BatchCheckLayerAvailability`, `GetDownloadUrlForLayer`, `BatchGetImage` (lecture seule).<br>• **Réseau (`ec2:*`) :** `CreateNetworkInterface`, `AttachNetworkInterface`, `DescribeInstances` (pour le CNI du cluster).<br>• **Logs (`logs:*`) :** `CreateLogGroup`, `CreateLogStream`, `PutLogEvents` vers CloudWatch. | • Aucune écriture/suppression d'images dans ECR.<br>• Aucune modification des Security Groups ou Subnets.<br>• Aucune gestion IAM (`iam:*`). |
| **`safeops-ci-role`** | Pipeline CI/CD (GitHub Actions via OIDC ou utilisateur dédié) | • **Build & Push ECR :** `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage` (uniquement sur les dépôts `safeops-*`).<br>• **Déploiement :** Lecture des métadonnées du cluster pour déclencher la mise à jour des conteneurs. | • **Aucune action réseau :** Interdiction totale de créer ou supprimer des VPC, Subnets ou Security Groups (`ec2:DeleteSubnet`, `ec2:CreateVpc` -> `AccessDenied`).<br>• **Aucune action IAM :** Interdiction de créer/modifier des rôles.<br>• **Aucun accès S3 tfstate :** Interdiction de lire ou supprimer l'état Terraform. |

---

## 3. Procédure de Vérification (Critère d'Acceptation #4)

Pour valider que le moindre privilège est effectif avant la clôture de l'US03 :
1. S'authentifier avec les identifiants de l'identité **`safeops-ci-role`**.
2. Tenter une action réseau hors périmètre, par exemple :
   ```powershell
   aws ec2 delete-subnet --subnet-id <SUBNET_ID> --region eu-north-1