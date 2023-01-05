variable "SF_Name" {}

variable "SF_Role" {}

variable "SF_LogGroup" {}

variable "SF_definitionFile" {}

variable "region" {}

variable "SF_LambdaARN" {
  default = null
}

variable "SF_TableSemaphore" {
  default = null
}

variable "SF_LockName" {
  default = null
}

variable "SF_ConcurrentAccessLimit" {
  default = null
}

variable "SF_StateMachineSemaphore" {
  default = null
}

