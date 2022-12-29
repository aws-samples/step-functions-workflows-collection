output "TestStateMachine" {
  value       = module.StateMachineTestSemaphore.StateMachineArn
  description = "The Step Function ARN"
}