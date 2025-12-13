output "alb_dns_name" {
  description = "Public URL for the application (HTTP)"
  value       = module.alb.alb_dns_name
}

output "evidence_bucket" {
  description = "Private S3 bucket used for evidence attachments"
  value       = module.s3.evidence_bucket_name
}

output "rds_endpoint" {
  description = "RDS endpoint (host:port) for the database"
  value       = module.rds.db_endpoint
}
