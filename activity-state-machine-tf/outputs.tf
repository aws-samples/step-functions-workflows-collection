output "TestStateMachine" {
  value       = aws_sfn_state_machine.sfn_state_machine.arn
  description = "The Step Functions State Machine ARN"
}

output "LambdaFunction" {
  value       = aws_lambda_function.LambdaDoWorkFunction.arn
  description = "The Lambda Function ARN"
}