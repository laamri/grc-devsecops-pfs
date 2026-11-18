# US03 — Matrice des Flux Réseau (Network Flow Matrix)

## 1. Architecture Réseau Cible (AWS `eu-north-1`)

- **VPC CIDR :** `10.0.0.0/16` (Région Stockholm `eu-north-1`)
- **Sous-réseaux Publics (2 AZ) :**
  - `10.0.1.0/24` (`eu-north-1a`) — Application Load Balancer (ALB) & NAT Gateway
  - `10.0.2.0/24` (`eu-north-1b`) — Application Load Balancer (ALB)
- **Sous-réseaux Privés (2 AZ) :**
  - `10.0.10.0/24` (`eu-north-1a`) — Nœuds du cluster (`auth_service`, `task_service`) & bases de données
  - `10.0.11.0/24` (`eu-north-1b`) — Nœuds du cluster (Haute Disponibilité)

> **Principe de sécurité :** Tout flux non explicitement autorisé dans le tableau ci-dessous est **bloqué par défaut** (Deny All) par les Security Groups AWS et les Network ACLs. Aucune exposition directe des nœuds du cluster vers Internet n'est autorisée.

---

## 2. Matrice des Flux Autorisés

| ID | Nom du Flux | Source | Destination | Protocole / Port | Direction | Justification Technique |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FLX-01** | Accès Utilisateur HTTPS | `0.0.0.0/0` (Internet) | `sg-alb` (Sous-réseau Public) | TCP `443` | Inbound | Point d'entrée unique et chiffré pour les utilisateurs finaux. |
| **FLX-02** | Redirection HTTP -> HTTPS | `0.0.0.0/0` (Internet) | `sg-alb` (Sous-réseau Public) | TCP `80` | Inbound | Redirige automatiquement le trafic non chiffré vers le port `443`. |
| **FLX-03** | Routage vers Auth Service | `sg-alb` | `sg-cluster` (Sous-réseau Privé) | TCP `8001` | Inbound | Transmet les requêtes d'authentification (`auth_service`) depuis le Load Balancer. |
| **FLX-04** | Routage vers Task Service | `sg-alb` | `sg-cluster` (Sous-réseau Privé) | TCP `8002` | Inbound | Transmet les requêtes métier (`task_service`) depuis le Load Balancer. |
| **FLX-05** | Communication Inter-Services | `sg-cluster` | `sg-cluster` (Auto-référencé) | TCP `8001-8002` | Internal | Permet à `task_service` de valider les jetons auprès de `auth_service` en réseau privé. |
| **FLX-06** | Sortie Internet (Mises à jour / Images) | `sg-cluster` (Sous-réseau Privé) | `0.0.0.0/0` (via NAT Gateway) | TCP `443` | Outbound | Permet aux nœuds privés de télécharger les images Docker (ECR) et correctifs de sécurité sans être joignables depuis Internet. |
| **FLX-07** | Résolution DNS Interne | `sg-cluster` | `10.0.0.2` (AWS VPC DNS) | TCP/UDP `53` | Outbound | Résolution des noms de services internes et endpoints AWS. |

---

## 3. Règles de Validation (Critères d'Acceptation US03)

- **Test de cloisonnement :** Toute tentative de connexion depuis Internet vers une IP du cluster sur un port non autorisé (ex. SSH `22`, HTTP `8001`, `8002`, ou `8080`) doit être rejetée (Timeout / Connection Refused).
- **Destruction propre :** L'ensemble des ressources réseau (VPC, Subnets, IGW, NAT Gateway, Route Tables, Security Groups) doit être supprimable sans erreur via `terraform destroy`.