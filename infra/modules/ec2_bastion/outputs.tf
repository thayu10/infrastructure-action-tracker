output "bastion_public_ip" {
  description = "Public IP of bastion (null if disabled)"
  value       = try(aws_instance.bastion[0].public_ip, null)
}
