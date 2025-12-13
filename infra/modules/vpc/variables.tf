variable "name" {
  type        = string
  description = "Name prefix for VPC resources"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "Public subnet CIDRs (expected 2)"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "Private subnet CIDRs (expected 2)"
}

variable "app_port" {
  type        = number
  description = "Application port exposed by ECS tasks"
  default     = 8000
}
