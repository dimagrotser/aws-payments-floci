variable "name" {
  description = "Function name; the role, policy and log group are named after it"
  type        = string
}

variable "source_dir" {
  description = "Directory to zip, produced by scripts/build-lambda.sh"
  type        = string
}

variable "build_dir" {
  description = "Where to write the zip"
  type        = string
}

variable "handler" {
  description = "module.function of the entry point"
  type        = string
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.13"
}

variable "timeout" {
  description = "Seconds before the invocation is killed"
  type        = number
  default     = 15
}

variable "memory_size" {
  description = "Megabytes"
  type        = number
  default     = 256
}

variable "environment" {
  description = "Environment variables for the function"
  type        = map(string)
  default     = {}
}

variable "policy_statements" {
  description = "Everything this function is allowed to do, beyond its own logs"
  type = list(object({
    sid       = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "reserved_concurrency" {
  description = "Cap on concurrent executions, so one function cannot starve the others"
  type        = number
  default     = 10
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps the logs"
  type        = number
  default     = 7
}
