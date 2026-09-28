resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = var.name }
}

# Two subnets in different availability zones because a DB subnet group demands it, and
# because the load balancer in stage 3 will want the same.
resource "aws_subnet" "private" {
  for_each = var.availability_zones

  vpc_id            = aws_vpc.this.id
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.cidr_block, 8, index(tolist(var.availability_zones), each.value))

  tags = { Name = "${var.name}-${each.key}" }
}

resource "aws_security_group" "internal" {
  name        = "${var.name}-internal"
  description = "Reachable from inside the VPC only"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "internal" {
  security_group_id = aws_security_group.internal.id
  description       = "Anything inside the VPC"
  cidr_ipv4         = aws_vpc.this.cidr_block
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "anywhere" {
  security_group_id = aws_security_group.internal.id
  description       = "Outbound is not what this project is about"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
