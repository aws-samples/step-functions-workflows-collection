# Display the State Machine ARN
output "StateMachine" {
  value       = aws_sfn_state_machine.sfn_state_machine.id
  description = "The AWS Step Functions State Machine ARN"
}