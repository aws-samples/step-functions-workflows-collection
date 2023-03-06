using Amazon.CDK;
using Amazon.CDK.AWS.ECS;
using Amazon.CDK.AWS.IAM;
using Amazon.CDK.AWS.Lambda;
using Amazon.CDK.AWS.Logs;
using Amazon.CDK.AWS.StepFunctions;
using Amazon.CDK.AWS.StepFunctions.Tasks;
using Constructs;

namespace cdk
{
    /// <summary>
    /// The following code creates an AWS CloudFormation stack with the Amazon CDK that sets up an ECS Fargate Cluster, 
    /// Lambda functions and a Step Function State Machine.
    /// </summary>
    public class CdkStack : Stack
    {
        internal CdkStack(Construct scope, string id, IStackProps props = null) : base(scope, id, props)
        {
            // Create a Lambda function to list files.
            var listFilesFunction = new Amazon.CDK.AWS.Lambda.Function(this, "ListFilesFunction", new FunctionProps()
            {
                Runtime = Runtime.DOTNET_6,
                Code = Code.FromAsset("ListFilesFunction/bin/Release/net6.0/publish"),
                Handler = "ListFilesFunction::ListFilesFunction.Function::FunctionHandler",
                Timeout = Duration.Minutes(10)
            });

            // Create a VPC for the Fargate cluster.
            var vpc = new Amazon.CDK.AWS.EC2.Vpc(this, "VPC");

            // Create an IAM role for the Fargate container with permissions to access ECR and CloudWatch logs.
            var role = new Amazon.CDK.AWS.IAM.Role(this, "FargateContainerRole", new RoleProps
            {
                AssumedBy = new Amazon.CDK.AWS.IAM.ServicePrincipal("ecs-tasks.amazonaws.com")
            });

            // Add policy to the role
            role.AddToPolicy(new PolicyStatement(new PolicyStatementProps
            {
                Resources = new[] { "*" },
                Actions = new[] { "ecr:*", "logs:*" }
            }));

            // Create a Fargate cluster.
            var cluster = new Cluster(this, "WorkflowAppCLuster", new ClusterProps
            {
                Vpc = vpc
            });

            // Create Task definition
            var taskDef = new TaskDefinition(this, "WorkflowAppTaskDef", new TaskDefinitionProps
            {
                Compatibility = Compatibility.FARGATE,
                Cpu = "256",
                MemoryMiB = "512"
            });

            // Add container to Task definition
            taskDef.AddContainer("WorkflowAppContainer", new Amazon.CDK.AWS.ECS.ContainerDefinitionOptions
            {
                Image = Amazon.CDK.AWS.ECS.ContainerImage.FromAsset("../src"),
                MemoryLimitMiB = 256,
                Logging = new AwsLogDriver(new AwsLogDriverProps
                {
                    LogGroup = new LogGroup(this, "workflowapp-copy-files-logs", new LogGroupProps
                    {
                        Retention = RetentionDays.THREE_DAYS
                    }),
                    StreamPrefix = "CopyFiles"
                })
            });

            // Create State machine
            // Configure Step function listFilesTask for listFilesFunction
            var listFilesTask = new Amazon.CDK.AWS.StepFunctions.Tasks.LambdaInvoke(this, "ListFiles", new LambdaInvokeProps
            {
                LambdaFunction = listFilesFunction,
                OutputPath = "$.Payload"
            });

            // Configure Step function copyFilesTask and add Fargate container
            var copyFilesTask = new Amazon.CDK.AWS.StepFunctions.Tasks.EcsRunTask(this, "CopyFiles", new EcsRunTaskProps
            {
                IntegrationPattern = IntegrationPattern.RUN_JOB,
                Cluster = cluster,
                TaskDefinition = taskDef,

                // you can have multiple executables in same docker image and can override the required command, for example
                // here you have two, (check Dockerfile for reference), CopyFilesTask and CleanupTask and this container is executing only CopyFilesTask. 
                ContainerOverrides = new ContainerOverride[] { new ContainerOverride()
                {
                    Command = new [] { "dotnet", "CopyFilesTask.dll" },
                    ContainerDefinition=taskDef.DefaultContainer,
                    Environment =new []{ new TaskEnvironmentVariable {
                    Name="Input",
                    Value=JsonPath.JsonToString(JsonPath.EntirePayload)
                } }
                }
                },
                LaunchTarget = new EcsFargateLaunchTarget()
            });

            // Configure all the tasks in state machine
            var stateMachineDefinition = listFilesTask.Next(copyFilesTask);

            var stateMachineProps = new StateMachineProps
            {
                Definition = stateMachineDefinition
            };

            var stateMachine = new StateMachine(this, "WorkflowAppStateMachine", stateMachineProps);

        }
    }
}
