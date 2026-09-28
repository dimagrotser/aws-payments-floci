output "bucket" {
  description = "Bucket holding decisions and reports"
  value       = module.storage.bucket
}

output "decisions_prefix" {
  description = "Where the processor writes its decisions"
  value       = "decisions"
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
