terraform {
  backend "s3" {
    bucket         = "infrastructure-action-tracker-tf-state"
    key            = "infra/dev/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
