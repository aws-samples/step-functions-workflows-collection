# emit-and-wait pattern

Implement a callback pattern within your workflow

A single workflow orchestrates a producitonline from start to completion, at various “milestones”, an event is emitted onto a serverless event bus (Event Bridge). The events are produced using the putEvents.waitForTaskToken. This allows the workflow to pause until receiving a resume command with the corresponding task token. Adding a `heartbeat` value to the putEvents task acts as a graceful timeout fallback.

![emit and wait](https://github.com/aws-samples/step-functions-workflows-collection/blob/main/emit-and-wait/images/emit-and-wait-sf.png?raw=true)