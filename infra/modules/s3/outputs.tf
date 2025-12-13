output "evidence_bucket_name" {
  description = "Evidence bucket name"
  value       = aws_s3_bucket.evidence.bucket
}

output "evidence_bucket_arn" {
  description = "Evidence bucket ARN"
  value       = aws_s3_bucket.evidence.arn
}
