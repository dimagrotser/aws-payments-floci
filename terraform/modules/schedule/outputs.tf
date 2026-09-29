output "rule_name" {
  description = "Name of the rule"
  value       = aws_cloudwatch_event_rule.this.name
}

output "schedule_expression" {
  description = "When the rule fires"
  value       = aws_cloudwatch_event_rule.this.schedule_expression
}
