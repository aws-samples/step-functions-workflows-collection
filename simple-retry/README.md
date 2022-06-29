# The “simple retry” pattern

Use AWS Step Function native retry configuration to catch errors and retry tasks
Enable error handling and retry logic into your Step Function State Machine

Task states (and others) have the capability to retry their work after they encounter an error. We just need to add a Retry parameter to the Task state definitions, telling them which types of errors they should retry for, and optionally specify additional configuration to control the rate of retries and the maximum number of retry attempts.


![Simple retry pattern](http://serverlessland.com/assets/images/workflows/simple-retry.png)