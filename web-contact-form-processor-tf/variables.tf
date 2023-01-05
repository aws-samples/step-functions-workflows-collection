variable "region" {
  description = "The AWS Region to use"
  type        = string
  default     = "us-east-1"
}

variable "email" {
  description = "The email address that will receive review notifications."
  type        = string
}