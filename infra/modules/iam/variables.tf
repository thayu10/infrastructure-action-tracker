variable "name" {
  type        = string
  description = "Name prefix for IAM resources"
}

variable "evidence_bucket_arn" {
  type        = string
  description = "ARN of the evidence S3 bucket"
}

variable "db_password_ssm_arn" {
  type        = string
  description = "ARN of the SSM SecureString parameter storing DB password"
}
