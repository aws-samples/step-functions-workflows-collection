# Display the S3 bucket and the SQS queue URL
output "expenses_bucket" {
  value       = aws_s3_bucket.expenses_bucket.id
  description = "The S3 Bucket"
}

# Display the State Machine ARN
output "sfn_state_machine" {
  value       = aws_sfn_state_machine.sfn_state_machine.id
  description = "The AWS Step Functions State Machine ARN"
}

# Display the DynamoDB table name
output "expenses_table" {
  value       = aws_dynamodb_table.expenses_table.id
  description = "The DynamoDB Table Name"
}
