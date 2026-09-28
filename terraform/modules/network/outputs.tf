output "vpc_id" {
  description = "VPC everything lives in"
  value       = aws_vpc.this.id
}

output "subnet_ids" {
  description = "Subnets, one per availability zone"
  value       = [for subnet in aws_subnet.private : subnet.id]
}

output "security_group_id" {
  description = "Security group that allows traffic from inside the VPC"
  value       = aws_security_group.internal.id
}
