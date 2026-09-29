variable "name" {
  description = "Name of the rule"
  type        = string
}

variable "description" {
  description = "What the rule is for"
  type        = string
  default     = ""
}

variable "schedule_expression" {
  description = "cron() or rate() expression"
  type        = string
}

variable "function_arn" {
  description = "Lambda the rule invokes"
  type        = string
}

variable "function_name" {
  description = "Name of that Lambda, for the invoke permission"
  type        = string
}
