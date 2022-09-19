# The “Serverless Round-robin” pattern

Selects the next array item in round robin fashion using the Step Functions execution count modulo of the array length.

The Step Functions `SDK:ListExecutions` task retrieves the total number of successful executions, and passes this onto a Lambda function that finds the remainder when divided by an array length (the modulo). 

This workflow pattern Is used in production to assign new serverlessLand pattern pull requests to the DA team via Asana. 

![Stateless roundrobin](https://github.com/aws-samples/step-functions-workflows-collection/blob/main/stateless-roundrobin/images/stateless-roundrobin-image.png?raw=true)