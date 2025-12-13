variable "name" {
  type        = string
  description = "Name prefix for ECS resources"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for ECS tasks"
}

variable "ecs_sg_id" {
  type        = string
  description = "Security group ID for ECS tasks"
}

variable "alb_target_group_arn" {
  type        = string
  description = "ALB target group ARN"
}

variable "app_port" {
  type        = number
  description = "Application port"
}

variable "docker_image" {
  type        = string
  description = "Full docker image reference"
}

variable "execution_role_arn" {
  type        = string
  description = "ECS execution role ARN"
}

variable "task_role_arn" {
  type        = string
  description = "ECS task role ARN"
}

variable "log_group_name" {
  type        = string
  description = "CloudWatch log group name"
}

variable "evidence_bucket" {
  type        = string
  description = "S3 bucket name for evidence uploads"
}

variable "owners" {
  type        = list(string)
  description = "Allowed owners list"
}

variable "components" {
  type        = list(string)
  description = "Allowed components list"
}

variable "db_host" {
  type        = string
  description = "Database hostname"
}

variable "db_port" {
  type        = number
  description = "Database port"
}

variable "db_name" {
  type        = string
  description = "Database name"
}

variable "db_user" {
  type        = string
  description = "Database username"
}

variable "db_password_ssm_arn" {
  type        = string
  description = "SSM parameter ARN for DB password"
}
