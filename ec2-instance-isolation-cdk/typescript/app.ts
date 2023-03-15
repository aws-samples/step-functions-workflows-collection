import {
    App,
    CfnOutput,
    Duration,
    Fn,
    Stack,
    StackProps,
    aws_ec2 as ec2,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
} from "aws-cdk-lib";
import { Construct } from "constructs";


interface ec2IsolationStackProps extends StackProps {
    vpcId: string;
}

export class ec2IsolationStack extends Stack {
    constructor(
        scope: Construct,
        id: string,
        props: ec2IsolationStackProps
    ) {
        super(scope, id, props);
        // Security group for isolating instance. 
        const vpc = ec2.Vpc.fromLookup(this, "VPC", {
            vpcId: props.vpcId
        });

        const isolationSecurityGroup = new ec2.SecurityGroup(this, "IsolationSecurityGroup", {
            vpc: vpc
        });

        isolationSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(22))

        // Get EC2 instance info
        const describeEc2InstanceTask = new tasks.CallAwsService(this, "Get EC2 Instance Info", {
            service: "ec2",
            action: "describeInstances",
            parameters: {
                "InstanceIds": sfn.JsonPath.stringAt("States.Array($.IsolatedInstanceId)")
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.stringAt("$.InstanceDescription")
        });

        // Enable EC2 termination protection
        const disableEc2TerminationTask = new tasks.CallAwsService(this, "Disable EC2 Termination", {
            service: "ec2",
            action: "modifyInstanceAttribute",
            parameters: {
                "InstanceId": sfn.JsonPath.stringAt("$.IsolatedInstanceId"),
                "DisableApiTermination": {
                    "Value": "true"
                }
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.DISCARD
        });

        // Get the EC2 instance autoscaling info
        const getAutoscalingInfoTask = new tasks.CallAwsService(this, "Get Autoscaling Group info", {
            service: "autoscaling",
            action: "describeAutoScalingInstances",
            parameters: {
                "InstanceIds": sfn.JsonPath.stringAt("States.Array($.IsolatedInstanceId)")
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.stringAt("$.AutoScalingResult")
        });

        // Detach instance from autoscaling group if it has one.
        const detachInstanceFromAsgTask = new tasks.CallAwsService(this, "Detach Instance from ASG", {
            service: "autoscaling",
            action: "detachInstances",
            parameters: {
                "AutoScalingGroupName": sfn.JsonPath.stringAt("$.AutoScalingResult.AutoScalingInstances[0].AutoScalingGroupName"),
                "ShouldDecrementDesiredCapacity": "false",
                "InstanceIds": sfn.JsonPath.stringAt("States.Array($.IsolatedInstanceId)")
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.DISCARD
        });


        // Create the snapshot from the isolated instance
        const createSnapshotFromIsolatedInstanceTask = new tasks.CallAwsService(this, "Create Sanpshot from Isonlated Instance", {
            service: "ec2",
            action: "createSnapshot",
            parameters: {
                "VolumeId": sfn.JsonPath.stringAt("$.InstanceDescription.Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId")
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.stringAt("$.SnapshotId")
        });

        // Create the forensic instance
        const createForensicInstanceTask = new tasks.CallAwsService(this, "Create Forensic Instance", {
            service: "ec2",
            action: "runInstances",
            parameters: {
                "MaxCount": 1,
                "MinCount": 1,
                "InstanceType": sfn.JsonPath.stringAt("$.InstanceDescription.Reservations[0].Instances[0].InstanceType"),
                "ImageId": sfn.JsonPath.stringAt("$.InstanceDescription.Reservations[0].Instances[0].ImageId"),
                "SubnetId": sfn.JsonPath.stringAt("$.InstanceDescription.Reservations[0].Instances[0].NetworkInterfaces[0].SubnetId"),
                "SecurityGroupIds": [
                    isolationSecurityGroup.securityGroupId
                ]
            },
            iamResources: ["*"],
            resultSelector: {
                "ForensicInstanceId": sfn.JsonPath.stringAt("$.Instances[0].InstanceId")
            }
        });

        // Describe snapshot creating status
        const getSnapshotStatusTask = new tasks.CallAwsService(this, "Get Snapshot Status",{
            service: "ec2",
            action: "describeSnapshots",
            parameters: {
                "SnapshotIds": sfn.JsonPath.stringAt("States.Array($.SnapshotId.SnapshotId)")
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.stringAt("$.SnapshotStatus"),
            resultSelector: {
                "SnapshotState": sfn.JsonPath.stringAt("$.Snapshots.[0].State")
            }
        });

        // Create EBS volume from the snapshot
        const createEbsVolumeFromSnapshotTask = new tasks.CallAwsService(this, "Create EBS Volume from Snapshot", {
            service: "ec2",
            action: "createVolume",
            parameters: {
                "AvailabilityZone": sfn.JsonPath.stringAt("$.InstanceDescription.Reservations[0].Instances[0].Placement.AvailabilityZone"),
                "SnapshotId": sfn.JsonPath.stringAt("$.SnapshotId.SnapshotId")
            },
            iamResources: ["*"],
            resultPath: sfn.JsonPath.stringAt("$.Volumes")
        });

        // Describe EBS volume to get the creating status
        const getEbsVolumeStatusTask = new tasks.CallAwsService(this, "Get EBS Volume Status",{
            service: "ec2",
            action: "describeVolumes",
            parameters: {
                "VolumeIds": sfn.JsonPath.stringAt("States.Array($.Volumes.VolumeId)")
            },
            iamResources:["*"],
            resultPath: sfn.JsonPath.stringAt("$.VolumeDescription")
        });

        // Attach the volume to the forensic instance 
        const attachVolumeTask = new tasks.CallAwsService(this, "Attach Volume", {
            service: "ec2",
            action: "attachVolume",
            parameters: {
                "Device": "/dev/sdf",
                "InstanceId": sfn.JsonPath.stringAt("$[0].ForensicInstanceId"),
                "VolumeId": sfn.JsonPath.stringAt("$[1].Volumes.VolumeId")
            },
            iamResources:["*"],
            resultPath: sfn.JsonPath.DISCARD
        });

        // Attach isolation security group to forensic instance 
        const allowForensicInstanceIngressTask = new tasks.CallAwsService(this, "Allow Forensic Instance Ingress",{
            service: "ec2",
            action: "authorizeSecurityGroupIngress",
            parameters: {
                "GroupId": sfn.JsonPath.stringAt("$[1].InstanceDescription.Reservations[0].Instances[0].SecurityGroups[0].GroupId"),
                "IpPermissions": [
                    {
                        "IpProtocol": "-1",
                        "FromPort": -1,
                        "UserIdGroupPairs": [
                            {
                                "GroupId": isolationSecurityGroup.securityGroupId
                            }
                        ]
                    }
                ]
            },
            iamResources:["*"],
            resultPath: sfn.JsonPath.DISCARD
        });

        // Tag the forensic instance with tag {"Environment": "Quarantie"}
        const tagInstanceAsQuarantieTask = new tasks.CallAwsService(this, "Tag Instance as Quarntie",{
            service: "ec2",
            action: "createTags",
            parameters: {
                "Resources":  sfn.JsonPath.stringAt("States.Array($[1].IsolatedInstanceId)"),
                "Tags": [
                    {
                        "Key": "Environment",
                        "Value": "Quarantine"
                    }
                ]
            },
            iamResources:["*"]
        });

        // Build the state machine states: Choice, Condition, Pass, Wait
        const hasAsgChoice = new sfn.Choice(this, "Has ASG?");
        const yesAsgCon = sfn.Condition.isPresent("$.AutoScalingResult.AutoScalingInstances[0].AutoScalingGroupName");

        const isSnapshotCompleteChoice = new sfn.Choice(this, "Is Snapshot Complete?");
        const yesSnapshotCompleteCon = sfn.Condition.stringEquals("$.SnapshotStatus.SnapshotState", "completed");

        const isEbsVolumeAvailableChoice = new sfn.Choice(this, "is EBS Volume Available?");
        const noEbsVolumeavailableCon = sfn.Condition.not(sfn.Condition.stringEquals(
            "$.VolumeDescription.Volumes[0].State", "available"
        ));

        const snapshotCreationCompleteWait = new sfn.Wait(this, "Wait for Snapshot Creation",{
            time: sfn.WaitTime.duration(Duration.seconds(15))
        });

        const volumeCreationCompleteWait = new sfn.Wait(this, "Wati for Volume Createion", {
            time: sfn.WaitTime.duration(Duration.seconds(15))
        });

        const volumeCreationCompletePass = new sfn.Pass(this, "Volume Creation Complete")

        // Parallel create forensic instance, snapshot and volume

        const parallelCreate = new sfn.Parallel(this, "Create Forensic Instance, Snapshot, Volume");

        parallelCreate.branch(createForensicInstanceTask);

        parallelCreate.branch(
            createSnapshotFromIsolatedInstanceTask.next(getSnapshotStatusTask).next(isSnapshotCompleteChoice.when(
                yesSnapshotCompleteCon, createEbsVolumeFromSnapshotTask.next(getEbsVolumeStatusTask).next(isEbsVolumeAvailableChoice.when(
                    noEbsVolumeavailableCon, volumeCreationCompleteWait.next(getEbsVolumeStatusTask)
                ).otherwise(volumeCreationCompletePass)
                )).otherwise(snapshotCreationCompleteWait.next(getSnapshotStatusTask))
            )
        );

        // Build the state machine chain 
        const chain = sfn.Chain.start(describeEc2InstanceTask).next(disableEc2TerminationTask).next(getAutoscalingInfoTask).next(hasAsgChoice.when(
                        yesAsgCon, detachInstanceFromAsgTask
                    ).afterwards({includeOtherwise: true})
                    ).next(parallelCreate).next(attachVolumeTask).next(allowForensicInstanceIngressTask).next(tagInstanceAsQuarantieTask)

        // State machine
        const sm = new sfn.StateMachine(this, "StateMachin", {
            definition: chain
        });

        // Outputs for accessing resources
        new CfnOutput(this, "StepFunctionArn", {
            description: "Step function ARN",
            value: sm.stateMachineType
        });

        new CfnOutput(this, "StepFunctionUrl", {
            description: "Step function Console URL",
            value: Fn.sub("https://${AWS::Region}.console.aws.amazon.com/states/home?region=${AWS::Region}#/statemachines/view/${EC2IsolationStateMachine}",{
                EC2IsolationStateMachine: sm.stateMachineArn
            })
        })
    }
}

const app = new App();
new ec2IsolationStack(app, "ec2IsolationTypescript", {
    vpcId: "<your vpc ID >",
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT,
        region: process.env.CDK_DEFAULT_REGION
    }
});
app.synth();
