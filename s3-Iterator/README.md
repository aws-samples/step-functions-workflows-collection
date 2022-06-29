# The “S3 Iterator” pattern

This pattern forms the basis of serverlesspresso’s event driven architecture.
A single workflow orchestrates each order from start to completion, at various “milestones”, an event is emitted onto a serverless event bus (Event Bridge). The events are produced using the putEvents.waitForTaskToken. This allows the workflow to pause until receiving a resume command with the corresponding task token. Adding a `heartbeat` value to the putEvents task acts as a graceful timeout fallback.

 This is an effective way to signal state transitions to interested consumers. The process is event-driven, promoting the concepts of loose coupling, isolation, and autonomy. It uses a low code integration approach via the EventBridge service integration.

This pattern has been explained to over 10 thousand users across multiple serverlesspresso booths. It is the primary focus of the new serverlesspresso EDA workshop I have built. The workshop has been very popular with users at multiple AWS summits and customer immersion days ran by DA and the serverless TFC.
