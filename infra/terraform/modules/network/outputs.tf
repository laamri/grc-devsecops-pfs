output "vpc_id" {
  description = "ID du VPC créé"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs des sous-réseaux publics"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs des sous-réseaux privés"
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  description = "ID du Security Group de l'ALB"
  value       = aws_security_group.alb.id
}

output "cluster_security_group_id" {
  description = "ID du Security Group du cluster"
  value       = aws_security_group.cluster.id
}