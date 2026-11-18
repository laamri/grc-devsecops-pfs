output "terraform_role_arn" {
  description = "ARN du rôle IAM dédié à Terraform"
  value       = aws_iam_role.terraform.arn
}

output "cluster_role_arn" {
  description = "ARN du rôle IAM dédié aux nœuds du cluster"
  value       = aws_iam_role.cluster.arn
}

output "cluster_instance_profile_name" {
  description = "Nom de l'Instance Profile attaché aux nœuds du cluster"
  value       = aws_iam_instance_profile.cluster.name
}

output "ci_role_arn" {
  description = "ARN du rôle IAM dédié au pipeline CI/CD"
  value       = aws_iam_role.ci.arn
}