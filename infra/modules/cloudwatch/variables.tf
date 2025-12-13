variable "name" {
  type        = string
  description = "Name prefix"
}

variable "alb_arn_suffix" {
  type        = string
  description = "ALB ARN suffix for CloudWatch dimensions"
}

variable "tg_arn_suffix" {
  type        = string
  description = "Target Group ARN suffix for CloudWatch dimensions"
}
