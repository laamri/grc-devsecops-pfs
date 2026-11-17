terraform {
  backend "s3" {
    bucket       = "pfs-tfstate-132415609490-eu-north-1"
    key          = "dev/terraform.tfstate"
    region       = "eu-north-1"
    encrypt      = true
    use_lockfile = true
  }
}