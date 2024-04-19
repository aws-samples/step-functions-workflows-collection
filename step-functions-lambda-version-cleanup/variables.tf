variable "region" {
  description = "The AWS Region to use"
  type        = string
  default     = "eu-central-1"
}

variable "lambda_function_filter_prefix" {
  type = string
  description = "Specify a prefix which is used to classify Lambda functions to be processed. All functions whose name starts with this prefix will taken into account"
}