output "project_name" {
  description = "Nom du projet pour identifier cet etat Terraform"
  value       = "grc-devsecops-pfs"
}

output "vpc_id" {
  description = "ID du VPC principal"
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "IDs des sous-réseaux privés"
  value       = module.network.private_subnet_ids
}

output "nat_public_ip" {
  description = "IP publique du NAT Gateway"
  value       = module.network.alb_security_group_id
}

output "ci_role_arn" {
  description = "ARN du rôle CI/CD"
  value       = module.iam.ci_role_arn
}