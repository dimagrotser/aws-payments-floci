variable "project" {
  description = "Prefix for every resource name"
  type        = string
  default     = "payments"
}

variable "region" {
  description = "Region to pretend we are in"
  type        = string
  default     = "us-east-1"
}

variable "visibility_timeout_seconds" {
  description = <<-EOT
    How long a message stays invisible after a failed attempt. Lower than you would pick
    on AWS: it is what decides how fast a poison message reaches the dead letter queue,
    and the tests wait for exactly that.
  EOT
  type        = number
  default     = 20
}

variable "max_receive_count" {
  description = "Attempts before a message is moved to the dead letter queue"
  type        = number
  default     = 3
}

variable "max_amount" {
  description = "Transactions above this are rejected"
  type        = string
  default     = "10000"
}

variable "blocked_countries" {
  description = "ISO 3166-1 alpha-2 codes that are rejected outright"
  type        = list(string)
  default     = ["KP", "IR", "SY"]
}

variable "velocity_limit" {
  description = "Transactions per customer inside the window before we reject"
  type        = number
  default     = 5
}

variable "velocity_window_minutes" {
  description = "Width of the velocity window"
  type        = number
  default     = 10
}

variable "api_image_tag" {
  description = "Tag of the API image in ECR, set by scripts/push-api-image.sh"
  type        = string
  default     = "dev"
}
