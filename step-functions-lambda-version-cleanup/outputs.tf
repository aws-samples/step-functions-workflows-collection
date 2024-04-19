output "state_machine_arn" {
  value       = module.lambda_cleanup_sfn.state_machine_arn
  description = "The Step Functions State Machine ARN"
}

output "lambda_function_arn" {
  value       = module.sort_functions_fn.lambda_function_arn
  description = "The Lambda Function ARN"
}