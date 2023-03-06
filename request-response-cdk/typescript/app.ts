import {
  App,
  Stack,
  aws_sns as sns,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
} from 'aws-cdk-lib';

import { Construct } from 'constructs';

export class requestResponseStack extends Stack {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    // Create Amazon SNS target topic
    const topic = new sns.Topic(this, "SNSTopic", {
      topicName: `${this.stackName}-topic`,
    })

    // Create a Wait state
    const wait_timestamp = new sfn.Wait(this, "Wait for timestamp", {
      time: sfn.WaitTime.secondsPath("$.timer_seconds"),
    })

    // Create a Task state which publishes a message to a SNS topic
    const sendMessageToSns = new tasks.SnsPublish(this, "Send message to SNS", {
      topic,
      integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
      message: sfn.TaskInput.fromObject({
        "input": sfn.JsonPath.stringAt("$.message")
      }),
    })

    // Create AWS Step Function state machine
    const requestResponseStateMachine = new sfn.StateMachine(this, "RequestResponse", {
      definition: sfn.Chain.start(
        wait_timestamp.next(
          sendMessageToSns
        ),
      ),
    })

    // Add permissions for state machine to publish to SNS topic
    topic.grantPublish(requestResponseStateMachine)
    
  }
}

const app = new App()
new requestResponseStack(app, "RequestResponseTypescript")
app.synth()