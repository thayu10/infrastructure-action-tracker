variable "aws_region" {
  type        = string
  description = "AWS region to deploy into"
  default     = "ap-southeast-1"
}

variable "environment" {
  type        = string
  description = "Environment name (dev/prod)"
}

variable "docker_image" {
  type        = string
  description = "Full Docker image reference, e.g. thayu10/infrastructure-action-tracker:<sha>"
}

variable "app_port" {
  type        = number
  description = "Container port exposed by the application"
  default     = 8000
}

# Networking
variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "Public subnet CIDRs (2 AZs recommended)"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "Private subnet CIDRs (2 AZs recommended)"
}

# Database (RDS Postgres)
variable "db_instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS allocated storage in GB"
  default     = 20
}

variable "db_name" {
  type        = string
  description = "Database name"
  default     = "actiontracker"
}

variable "db_username" {
  type        = string
  description = "Database username"
  default     = "actiontracker"
}

# UI dropdown configuration (passed into container as env vars)
variable "owners" {
  type        = list(string)
  description = "Allowed owners list for dropdown"
  default     = ["thayu10"]
}

variable "components" {
  type        = list(string)
  description = "Allowed components list for dropdown"
  default     = ["CI-Pipeline", "ECS-Service", "RDS-Postgres", "ALB", "VPC"]
}

# Optional bastion (we keep module present, but disabled by default)
variable "bastion_key_name" {
  type        = string
  description = "Optional EC2 key pair name for bastion; leave empty to disable"
  default     = ""
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP in CIDR form for bastion SSH (only used if bastion enabled)"
  default     = "0.0.0.0/32"
}
