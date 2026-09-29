variable "name" {
  description = "Instance identifier; the secret and subnet group are named after it"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for the DB subnet group"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group the instance sits behind"
  type        = string
}

variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "payments"
}

variable "master_username" {
  description = "Master user"
  type        = string
  default     = "payments"
}

variable "engine_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16.4"
}

variable "instance_class" {
  description = "Instance size"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Gigabytes"
  type        = number
  default     = 20
}

variable "backup_retention_days" {
  description = "How many days of automated backups to keep"
  type        = number
  default     = 7
}

variable "password_version" {
  description = "Bump to rotate the master password; both the instance and the secret follow it"
  type        = number
  default     = 1
}
