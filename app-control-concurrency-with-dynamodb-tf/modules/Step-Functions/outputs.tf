output "StateMachineArn" {
  value       = aws_sfn_state_machine.sfn_state_machine.arn
  description = "The Step Function ARN"
}