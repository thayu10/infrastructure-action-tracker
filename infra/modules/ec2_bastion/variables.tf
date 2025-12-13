variable "name" {
  type        = string
  description = "Name prefix"
}

variable "public_subnet_id" {
  type        = string
  description = "Public subnet ID to launch bastion (if enabled)"
}

variable "bastion_sg_id" {
  type        = string
  description = "Security group ID for bastion"
}

variable "key_name" {
  type        = string
  description = "EC2 key pair name. If empty, bastion will not be created."
  default     = ""
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP CIDR to allow SSH (only used if bastion enabled)"
  default     = "0.0.0.0/32"
}
