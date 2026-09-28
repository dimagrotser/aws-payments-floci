variable "name" {
  description = "Queue name; the dead letter queue gets a -dlq suffix"
  type        = string
}

variable "visibility_timeout_seconds" {
  description = "How long a message stays invisible after being received"
  type        = number
  default     = 30
}

variable "max_receive_count" {
  description = "Attempts before the message is moved to the dead letter queue"
  type        = number
  default     = 3
}

variable "dlq_retention_seconds" {
  description = "How long failed messages are kept for inspection"
  type        = number
  default     = 1209600 # 14 days, the SQS maximum
}
