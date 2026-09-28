output "function_name" {
  description = "Name of the function"
  value       = aws_lambda_function.this.function_name
}

output "arn" {
  description = "Function ARN"
  value       = aws_lambda_function.this.arn
}

output "role_name" {
  description = "Name of the execution role"
  value       = aws_iam_role.this.name
}

output "role_arn" {
  description = "ARN of the execution role"
  value       = aws_iam_role.this.arn
}

output "log_group" {
  description = "CloudWatch log group the function writes to"
  value       = aws_cloudwatch_log_group.this.name
}

output "timeout" {
  description = "Seconds before the invocation is killed"
  value       = aws_lambda_function.this.timeout
}

output "granted_actions" {
  description = <<-EOT
    Every action this function is allowed to take, for `terraform test` to look at.
    Actions are known before apply; the resources they apply to are not, so the
    resource scoping is checked against the deployed role in tests/integration/.
  EOT
  value       = flatten([for statement in var.policy_statements : statement.actions])
}
