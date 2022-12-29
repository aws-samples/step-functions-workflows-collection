# Display the S3 bucket and the SQS queue URL
output "S3-Bucket" {
  value       = aws_s3_bucket.MyS3Bucket.id
  description = "The S3 Bucket"
}

# Display the State Machine ARN
output "StateMachine" {
  value       = aws_sfn_state_machine.sfn_state_machine.id
  description = "The AWS Step Functions State Machine ARN"
}

# Display the DynamoDB table name
output "DynamoDBTable" {
  value       = aws_dynamodb_table.imagesTable.id
  description = "The DynamoDB Table Name"
}

# Display the Input for the Step Functions
output "StepFunctionInput" {
  # value       = "{ \"Objects\": [ {\"Key\": \"building.jpg\",\"Bucket\": \"${aws_s3_bucket.MyS3Bucket.id}\"},{\"Key\": \"desk.jpg\",\"Bucket\": \"${aws_s3_bucket.MyS3Bucket.id}\"},{\"Key\": \"dinos.jpg\",\"Bucket\": \"${aws_s3_bucket.MyS3Bucket.id}\"},{\"Key\": \"office.jpg\",\"Bucket\": \"${aws_s3_bucket.MyS3Bucket.id}\"},{\"Key\": \"stage.jpg\",\"Bucket\": \"${aws_s3_bucket.MyS3Bucket.id}\"}]}"
  value       = <<EOF
{
  "Objects": [
      {
          "Key": "building.jpg",
          "Bucket": "${aws_s3_bucket.MyS3Bucket.id}"
      },
      {
          "Key": "desk.jpg",
          "Bucket": "${aws_s3_bucket.MyS3Bucket.id}"
      },
      {
          "Key": "dinos.jpg",
          "Bucket": "${aws_s3_bucket.MyS3Bucket.id}"
      },
      {
          "Key": "office.jpg",
          "Bucket": "${aws_s3_bucket.MyS3Bucket.id}"
      },
      {
          "Key": "stage.jpg",
          "Bucket": "${aws_s3_bucket.MyS3Bucket.id}"
      }
  ]
}
  EOF
  description = "Use this JSON as input to the Step Function"
}