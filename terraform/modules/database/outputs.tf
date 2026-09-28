output "secret_arn" {
  description = "Secret holding the connection details"
  value       = aws_secretsmanager_secret.this.arn
}

output "secret_name" {
  description = "Name of the secret"
  value       = aws_secretsmanager_secret.this.name
}

output "address" {
  description = "Hostname the instance is advertised under"
  value       = aws_db_instance.this.address
}

output "port" {
  description = "Port the instance is advertised on, which on Floci is a proxy port"
  value       = aws_db_instance.this.port
}

output "database_name" {
  description = "Name of the database"
  value       = aws_db_instance.this.db_name
}

output "password_in_state" {
  description = "Whether the plain password argument is in use, for terraform test to assert on"
  value       = aws_db_instance.this.password != null
}

output "publicly_accessible" {
  description = "Whether the instance takes a public address"
  value       = aws_db_instance.this.publicly_accessible
}
