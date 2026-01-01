environment = "dev"
aws_region  = "ap-southeast-1"

# NOTE: CD will pass docker_image dynamically (immutable SHA tag).
# This placeholder is only for local planning if you want to run it manually.
docker_image = "thayu10/infrastructure-action-tracker:local"

# Networking
vpc_cidr = "10.10.0.0/16"

public_subnet_cidrs  = ["10.10.1.0/24", "10.10.2.0/24"]
private_subnet_cidrs = ["10.10.11.0/24", "10.10.12.0/24"]

# RDS sizing (small + cost-aware)
db_instance_class    = "db.t4g.micro"
db_allocated_storage = 20
db_name              = "actiontracker"
db_username          = "actiontracker"

# UI dropdowns
owners     = ["thayu10"]
components = ["CI-Pipeline", "ECS-Service", "RDS-Postgres", "ALB", "VPC"]

# Optional bastion (disabled by default)
# bastion_key_name = "your-existing-ec2-keypair-name"
# my_ip_cidr       = "x.x.x.x/32"

#To simulate change
#Extra line