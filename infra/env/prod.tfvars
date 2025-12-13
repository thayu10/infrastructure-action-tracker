environment = "prod"
aws_region  = "ap-southeast-1"

# CD will pass docker_image dynamically when/if you deploy prod.
docker_image = "thayu10/infrastructure-action-tracker:local"

# Networking (separate CIDR from dev)
vpc_cidr = "10.20.0.0/16"

public_subnet_cidrs  = ["10.20.1.0/24", "10.20.2.0/24"]
private_subnet_cidrs = ["10.20.11.0/24", "10.20.12.0/24"]

# RDS sizing (keep small unless you explicitly want bigger)
db_instance_class     = "db.t4g.micro"
db_allocated_storage  = 20
db_name               = "actiontracker"
db_username           = "actiontracker"

# UI dropdowns
owners     = ["thayu10"]
components = ["CI-Pipeline", "ECS-Service", "RDS-Postgres", "ALB", "VPC"]

# Optional bastion (disabled by default)
# bastion_key_name = "your-existing-ec2-keypair-name"
# my_ip_cidr       = "x.x.x.x/32"
