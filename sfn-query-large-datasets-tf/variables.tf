variable "region" {
    type=string
    description = "AWS Region where deploying resources"
    default = "us-east-1"
}

variable "aws_profile_name" {
    type=string
    description = "AWS CLI credentials profile name"
    default="default"
}