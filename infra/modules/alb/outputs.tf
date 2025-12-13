output "alb_dns_name" {
  description = "Public ALB DNS name"
  value       = aws_lb.this.dns_name
}

output "listener_arn" {
  description = "ALB listener ARN (HTTP)"
  value       = aws_lb_listener.http.arn
}

output "target_group_arn" {
  description = "Target group ARN for ECS service attachment"
  value       = aws_lb_target_group.app.arn
}

output "alb_arn_suffix" {
  description = "ALB ARN suffix (for CloudWatch dimensions)"
  value       = aws_lb.this.arn_suffix
}

output "target_group_arn_suffix" {
  description = "Target group ARN suffix (for CloudWatch dimensions)"
  value       = aws_lb_target_group.app.arn_suffix
}
