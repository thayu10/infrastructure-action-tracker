data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# If key_name is empty, do not create bastion (count = 0)
locals {
  enabled = length(trimspace(var.key_name)) > 0
}

resource "aws_security_group_rule" "ssh_in" {
  count             = local.enabled ? 1 : 0
  type              = "ingress"
  security_group_id = var.bastion_sg_id

  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = [var.my_ip_cidr]

  description = "SSH from my IP"
}

resource "aws_instance" "bastion" {
  count = local.enabled ? 1 : 0

  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [var.bastion_sg_id]
  key_name               = var.key_name

  associate_public_ip_address = true

  tags = {
    Name = "${var.name}-bastion"
  }
}
