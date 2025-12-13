output "db_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.this.endpoint
}

output "db_host" {
  description = "RDS hostname/address"
  value       = aws_db_instance.this.address
}
