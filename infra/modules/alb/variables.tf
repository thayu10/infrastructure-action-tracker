variable "name" {
  type        = string
  description = "ALB name prefix"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs"
}

variable "alb_sg_id" {
  type        = string
  description = "Security group ID for ALB"
}

variable "app_port" {
  type        = number
  description = "Application port on ECS tasks"
}
