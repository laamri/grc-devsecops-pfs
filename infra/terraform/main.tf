# Appel du module Réseau (VPC, Subnets, NAT, Security Groups)
module "network" {
  source       = "./modules/network"
  project_name = "grc-devsecops-pfs"
}

# Appel du module IAM (Rôles least-privilege Terraform, Cluster, CI)
module "iam" {
  source              = "./modules/iam"
  project_name        = "grc-devsecops-pfs"
  aws_account_id      = "132415609490"
  tfstate_bucket_name = "pfs-tfstate-132415609490-eu-north-1"
}