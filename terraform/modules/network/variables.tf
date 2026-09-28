variable "name" {
  description = "Prefix for the VPC and everything in it"
  type        = string
}

variable "cidr_block" {
  description = "Address range of the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zones to spread the subnets across"
  type        = set(string)
  default     = ["us-east-1a", "us-east-1b"]
}
