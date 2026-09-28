variable "name" {
  description = "Repository, cluster, service and load balancer are all named after this"
  type        = string
}

variable "region" {
  description = "Region, for the awslogs driver"
  type        = string
}

variable "image_tag" {
  description = "Tag pushed by scripts/push-api-image.sh"
  type        = string
}

variable "vpc_id" {
  description = "VPC the target group belongs to"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for the tasks and the load balancer"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group for the tasks and the load balancer"
  type        = string
}

variable "container_port" {
  description = "Port the application listens on"
  type        = number
  default     = 8000
}

variable "listener_port" {
  description = "Port the load balancer listens on"
  type        = number
  default     = 80
}

variable "health_check_path" {
  description = "Path the target group probes"
  type        = string
  default     = "/healthz"
}

variable "desired_count" {
  description = "How many tasks to run"
  type        = number
  default     = 1
}

variable "cpu" {
  description = "Task CPU units"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Task memory in megabytes"
  type        = number
  default     = 1024
}

variable "environment" {
  description = "Environment variables for the container"
  type        = map(string)
  default     = {}
}

variable "policy_statements" {
  description = "Everything the application itself is allowed to do"
  type = list(object({
    sid       = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps the container logs"
  type        = number
  default     = 7
}
