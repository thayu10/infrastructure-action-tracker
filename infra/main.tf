locals {
  name = "iat-${var.environment}"
}

# Generate a strong DB password in Terraform (not hardcoded)
resource "random_password" "db_password" {
  length  = 24
  special = true
}

# Store DB password in SSM Parameter Store (SecureString)
# ECS will read it as a secret at runtime
resource "aws_ssm_parameter" "db_password" {
  name  = "/${local.name}/db_password"
  type  = "SecureString"
  value = random_password.db_password.result
}

module "vpc" {
  source               = "./modules/vpc"
  name                 = local.name
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  app_port             = var.app_port
}

module "s3" {
  source = "./modules/s3"
  name   = local.name
}

module "iam" {
  source              = "./modules/iam"
  name                = local.name
  evidence_bucket_arn = module.s3.evidence_bucket_arn
  db_password_ssm_arn = aws_ssm_parameter.db_password.arn
}

module "alb" {
  source            = "./modules/alb"
  name              = local.name
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  alb_sg_id         = module.vpc.alb_sg_id
  app_port          = var.app_port
}

module "rds" {
  source               = "./modules/rds"
  name                 = local.name
  private_subnet_ids   = module.vpc.private_subnet_ids
  db_instance_class    = var.db_instance_class
  db_allocated_storage = var.db_allocated_storage
  db_name              = var.db_name
  db_username          = var.db_username
  db_password          = random_password.db_password.result
  db_sg_id             = module.vpc.rds_sg_id
}

module "cloudwatch" {
  source         = "./modules/cloudwatch"
  name           = local.name
  alb_arn_suffix = module.alb.alb_arn_suffix
  tg_arn_suffix  = module.alb.target_group_arn_suffix
}

module "ecs" {
  source = "./modules/ecs"

  name       = local.name
  aws_region = var.aws_region

  private_subnet_ids = module.vpc.private_subnet_ids
  ecs_sg_id          = module.vpc.ecs_sg_id

  alb_target_group_arn = module.alb.target_group_arn
  app_port             = var.app_port

  docker_image       = var.docker_image
  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn

  log_group_name = module.cloudwatch.log_group_name

  # App runtime config
  evidence_bucket = module.s3.evidence_bucket_name
  owners          = var.owners
  components      = var.components

  # Database connection config
  db_host             = module.rds.db_host
  db_port             = 5432
  db_name             = var.db_name
  db_user             = var.db_username
  db_password_ssm_arn = aws_ssm_parameter.db_password.arn
}

# Optional bastion (module exists, but stays disabled unless bastion_key_name is set)
module "ec2_bastion" {
  source           = "./modules/ec2_bastion"
  name             = local.name
  public_subnet_id = module.vpc.public_subnet_ids[0]
  bastion_sg_id    = module.vpc.bastion_sg_id
  key_name         = var.bastion_key_name
  my_ip_cidr       = var.my_ip_cidr
}
