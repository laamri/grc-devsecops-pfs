variable "project_name" {
  description = "Nom du projet utilisé pour préfixer les rôles et politiques IAM"
  type        = string
}

variable "aws_account_id" {
  description = "ID du compte AWS cible"
  type        = string
  default     = "132415609490"
}

variable "tfstate_bucket_name" {
  description = "Nom du bucket S3 stockant l'état Terraform"
  type        = string
  default     = "pfs-tfstate-132415609490-eu-north-1"
}