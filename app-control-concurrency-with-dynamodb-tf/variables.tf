variable "NamePrefix" {
  description = "Prefix to be used in names of the things created by this template."
  type        = string
  default     = "CC"
}

variable "LockName" {
  description = "The Semaphore name to be used"
  type        = string
  default     = "MySemaphore"
}

variable "region" {
  description = "The AWS Region to use"
  type        = string
  default     = "us-east-1"
}