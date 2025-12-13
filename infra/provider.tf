provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "infrastructure-action-tracker"
      ManagedBy   = "terraform"
      Repository  = "thayu10/infrastructure-action-tracker"
      Environment = var.environment
    }
  }
}
