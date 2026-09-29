output "bucket" {
  description = "Bucket holding decisions and reports"
  value       = module.storage.bucket
}

output "db_secret_arn" {
  description = "Secret holding the database credentials"
  value       = module.database.secret_arn
}

output "db_address" {
  description = "Hostname of the database as Floci advertises it"
  value       = module.database.address
}

output "db_port" {
  description = "Port of the database; on Floci a proxy port, not 5432"
  value       = module.database.port
}

output "db_name" {
  description = "Name of the database"
  value       = module.database.database_name
}

output "queue_url" {
  description = "Queue transactions are submitted to"
  value       = module.messaging.queue_url
}

output "dlq_url" {
  description = "Queue messages land in after too many failures"
  value       = module.messaging.dlq_url
}

output "processor_function" {
  description = "Name of the processor Lambda"
  value       = module.processor.function_name
}

output "processor_log_group" {
  description = "Log group of the processor Lambda"
  value       = module.processor.log_group
}

output "max_receive_count" {
  description = "Attempts before a message is moved aside, so tests know how long to wait"
  value       = var.max_receive_count
}

output "api_url" {
  description = "Where to reach the API from the host"
  value       = local.api_url_from_host
}

output "api_repository_url" {
  description = "ECR repository the API image is pushed to"
  value       = module.api.repository_url
}

output "api_log_group" {
  description = "Log group the API container writes to"
  value       = module.api.log_group
}

output "api_cluster" {
  description = "ECS cluster running the API"
  value       = module.api.cluster_name
}

output "api_service" {
  description = "ECS service running the API"
  value       = module.api.service_name
}

output "reports_prefix" {
  description = "Where the daily report is written"
  value       = var.reports_prefix
}

output "reporter_function" {
  description = "Name of the reporter Lambda"
  value       = module.reporter.function_name
}

output "report_schedule" {
  description = "When the report rule fires"
  value       = module.daily_report.schedule_expression
}
