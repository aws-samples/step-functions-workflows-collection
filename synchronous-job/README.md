# The Synchronous Job pattern

For integrated services such as AWS Batch and Amazon ECS, Step Functions can wait for a task to complete before progressing to the next state. This task orchestration pattern is called Run a Job (.sync)  in the documentation. To see a list of the integrated services that support synchronization, see Optimized integrations for Step Functions .

With this pattern you can run a synchronized task using Run a Job (.sync).


##Testing  
Execute the state machine, you will notice that the Submit Batch Job state will not advance until the job is completed.

![image](./resources/synchronous-job.png)

