# Nested Workflows

Combine Standard and Express Workflows by running a mock e-commerce workflow that does selective checkpointing (Nested workflows). Deploying this sample project creates a Standard workflows state machine, a nested Express Workflows state machine, an AWS Lambda function, an Amazon Simple Queue Service (Amazon SQS) queue, and an Amazon Simple Notification Service (Amazon SNS) topic.

Browse through this example state machine to see how Step Functions processes input from Amazon SQS and Amazon SNS, and then uses a nested Express Workflows state machine to update backend systems.

The child state machine in this sample project updates backend information when called by the parent state machine.

## Testing  


![image](./resources/childStateMachine.png)
![image](./resources/parentStatemachine.png)