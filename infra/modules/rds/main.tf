resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.name}-db-subnets"
  }
}

resource "aws_db_instance" "this" {
  identifier = "${var.name}-postgres"

  engine         = "postgres"
  engine_version = "16.3"

  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.db_sg_id]

  publicly_accessible = false

  # For a portfolio demo we keep teardown simple.
  skip_final_snapshot = true
  deletion_protection = false

  # Small quality-of-life defaults
  auto_minor_version_upgrade = true
  multi_az                   = false

  tags = {
    Name = "${var.name}-postgres"
  }
}
