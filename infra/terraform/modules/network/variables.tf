variable "project_name" {
  description = "Nom du projet utilisé pour le nommage et les tags"
  type        = string
}

variable "vpc_cidr" {
  description = "Bloc CIDR principal du VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zones de disponibilité AWS (eu-north-1)"
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDRs des sous-réseaux publics (ALB, NAT Gateway)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs des sous-réseaux privés (Cluster microservices)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}