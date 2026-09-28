output "repository_url" {
  description = "Where scripts/push-api-image.sh pushes the image"
  value       = aws_ecr_repository.this.repository_url
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.this.name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.this.name
}

output "listener_port" {
  description = "Port the load balancer listens on"
  value       = aws_lb_listener.this.port
}

output "load_balancer_dns" {
  description = "DNS name of the load balancer, which Floci does not resolve"
  value       = aws_lb.this.dns_name
}

output "target_group_arn" {
  description = "Target group the service registers its tasks into"
  value       = aws_lb_target_group.this.arn
}

output "log_group" {
  description = "Log group the container writes to"
  value       = aws_cloudwatch_log_group.this.name
}

output "task_role_name" {
  description = "Name of the role the application runs as"
  value       = aws_iam_role.task.name
}

output "granted_actions" {
  description = "Everything the application is allowed to do, for terraform test to assert on"
  value       = flatten([for statement in var.policy_statements : statement.actions])
}

output "execution_granted_actions" {
  description = "Everything the agent is allowed to do, for terraform test to assert on"
  value = flatten([
    for statement in data.aws_iam_policy_document.execution.statement : statement.actions
  ])
}
