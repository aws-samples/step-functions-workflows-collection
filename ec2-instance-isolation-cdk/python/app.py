from aws_cdk import (
    App,
    Fn,
    CfnOutput,
    Duration,
    Environment,
    Stack,
    aws_ec2 as ec2,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
import os

from constructs import Construct

class Ec2IsolationStack(Stack):
    def __init__(self, scope: Construct, id: str, vpc_id: str, **kwargs) -> sfn.JsonPath.DISCARD:
        super().__init__(scope, id, **kwargs)

        # Security group for isolating instance. 
        self.vpc = ec2.Vpc.from_lookup(self,"VPC",vpc_id=vpc_id)
        self.isolation_security_group = ec2.SecurityGroup(
            self, "EC2IsolationSecurityGroup",vpc=self.vpc)

        self.isolation_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(22))

        # Get EC2 instance info
        describe_ec2_task = tasks.CallAwsService(self, "Get EC2 Instance Info",
            service="ec2",
            action="describeInstances",
            parameters={
                "InstanceIds": sfn.JsonPath.string_at("States.Array($.IsolatedInstanceId)")
            },
            result_path=sfn.JsonPath.string_at("$.InstanceDescription"),
            iam_resources=["*"])

        # Enable EC2 termination portection
        disable_ec2_termination_task = tasks.CallAwsService(self, "Disable EC2 Termination",
            service="ec2",
            action="modifyInstanceAttribute",
            parameters={
                "InstanceId": sfn.JsonPath.string_at("$.IsolatedInstanceId"),
                "DisableApiTermination": {
                    "Value": "true"
                }
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.DISCARD
        )

        # Get the EC2 Instance autoscaling group info
        get_autoscaling_info_task = tasks.CallAwsService(self, "Get Autosacling Group Info",
            service="autoscaling",
            action="describeAutoScalingInstances",
            parameters={
                "InstanceIds": sfn.JsonPath.string_at("States.Array($.IsolatedInstanceId)")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.string_at("$.AutoScalingResult")
        )

        # Detach instance from autosacing group if it has one
        detach_instance_from_asg_task = tasks.CallAwsService(self, 
            "Detach Instance from ASG",
            service="autoscaling",
            action="detachInstances",
            parameters={
                "AutoScalingGroupName": sfn.JsonPath.string_at("$.AutoScalingResult.AutoScalingInstances[0].AutoScalingGroupName"),
                "ShouldDecrementDesiredCapacity": "false",
                "InstanceIds": sfn.JsonPath.string_at("States.Array($.IsolatedInstanceId)")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.DISCARD
        )

        # Create the Snapshot from the Isolated Instance
        create_snapshot_from_isolated_instance_task = tasks.CallAwsService(self, "Create Snapshot from Isolated Instance",
            service="ec2",
            action="createSnapshot",
            parameters={
                "VolumeId": sfn.JsonPath.string_at("$.InstanceDescription.Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.string_at("$.SnapshotId")
        )
        
        # Create the Forensic Instance
        create_forensic_instance_task = tasks.CallAwsService(self, "Create Forensic Instance",
            service="ec2",
            action="runInstances",
            parameters={
                "MaxCount": 1,
                "MinCount": 1,
                "InstanceType": sfn.JsonPath.string_at("$.InstanceDescription.Reservations[0].Instances[0].InstanceType"),
                "ImageId": sfn.JsonPath.string_at("$.InstanceDescription.Reservations[0].Instances[0].ImageId"),
                "SubnetId": sfn.JsonPath.string_at("$.InstanceDescription.Reservations[0].Instances[0].NetworkInterfaces[0].SubnetId"),
                "SecurityGroupIds": [
                    self.isolation_security_group.security_group_id
                ]
            },
            iam_resources=["*"],
            result_selector={
                "ForensicInstanceId": sfn.JsonPath.string_at("$.Instances[0].InstanceId")
            }
        )

        # Describe snapshot creating status
        get_snapshot_status_task = tasks.CallAwsService(self, "Get Snapshot Status",
            service="ec2",
            action="describeSnapshots",
            parameters={
                "SnapshotIds": sfn.JsonPath.string_at("States.Array($.SnapshotId.SnapshotId)")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.string_at("$.SnapshotStatus"),
            result_selector={"SnapshotState": sfn.JsonPath.string_at("$.Snapshots.[0].State")}
        )
        
        # Create EBS volume from the snapshot
        create_ebs_volume_from_ss_task = tasks.CallAwsService(self, "Create EBS Volume from Snapshot",
            service="ec2",
            action="createVolume",
            parameters={
                "AvailabilityZone": sfn.JsonPath.string_at("$.InstanceDescription.Reservations[0].Instances[0].Placement.AvailabilityZone"),
                "SnapshotId": sfn.JsonPath.string_at("$.SnapshotId.SnapshotId")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.string_at("$.Volumes")
        )

        # Describe EBS volume to get the creating status
        get_ebs_volume_status_task = tasks.CallAwsService(self, "Get EBS Volume Status",
            service="ec2",
            action="describeVolumes",
            parameters={
                "VolumeIds": sfn.JsonPath.string_at("States.Array($.Volumes.VolumeId)")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.string_at("$.VolumeDescription")
        )
    
        # Attach the volume to the forensic instance
        attach_volume_task = tasks.CallAwsService(self, "Attach Volume",
            service="ec2",
            action="attachVolume",
            parameters={
                "Device": "/dev/sdf",
                "InstanceId": sfn.JsonPath.string_at("$[0].ForensicInstanceId"),
                "VolumeId": sfn.JsonPath.string_at("$[1].Volumes.VolumeId")
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.DISCARD

        )

        # Attach isolation security group to forensic instance
        allow_forensic_instace_ingress_task = tasks.CallAwsService(self, "Allow Forensic Instance Ingress",
            service="ec2",
            action="authorizeSecurityGroupIngress",
            parameters={
                "GroupId": sfn.JsonPath.string_at("$[1].InstanceDescription.Reservations[0].Instances[0].SecurityGroups[0].GroupId"),
                "IpPermissions": [
                    {
                        "IpProtocol": "-1",
                        "FromPort": -1,
                        "UserIdGroupPairs": [
                            {
                                "GroupId": self.isolation_security_group.security_group_id
                            }
                        ]
                    }
                ]
            },
            iam_resources=["*"],
            result_path=sfn.JsonPath.DISCARD

        )

        # Tag the Forensic instance with tag Quarantie
        tag_instance_as_quarantie_task = tasks.CallAwsService(self, "Tag Instance as Quarntie",
            service="ec2",
            action="createTags",
            parameters={
                "Resources":  sfn.JsonPath.string_at("States.Array($[1].IsolatedInstanceId)"),
                "Tags": [
                    {
                        "Key": "Environment",
                        "Value": "Quarantine"
                    }
                ]
            },
            iam_resources=["*"]
        )

        # Build the state machine state: Choice, Condition, Pass, Wait
        has_asg_choice = sfn.Choice(self, "Has ASG?")

        yes_asg_con = sfn.Condition.is_present(variable="$.AutoScalingResult.AutoScalingInstances[0].AutoScalingGroupName")

        is_snapshot_complete_choice = sfn.Choice(
            self, "Is snapshot complete?")
        
        yes_snapshot_complete_con = sfn.Condition.string_equals(variable="$.SnapshotStatus.SnapshotState",value="completed")

        is_ebs_volume_available_choice = sfn.Choice(
            self, "Is EBS Volume Available?")
        
        no_ebs_volume_available_con = sfn.Condition.not_(sfn.Condition.string_equals(variable="$.VolumeDescription.Volumes[0].State",value="available"))

        volume_creation_complete_wait = sfn.Wait(
            self, "Wait for Volume Creation", time=sfn.WaitTime.duration(Duration.seconds(15)))

        snapshot_creation_complete_wait = sfn.Wait(
            self, "Wait for Snapshot Creation", time=sfn.WaitTime.duration(Duration.seconds(15)))

        volume_create_complete_pass = sfn.Pass(
            self, "Volume Creation Complete")
        
        # parallel create Forensic instance, snapshots and volume        
        parallel_create = sfn.Parallel(self, "Create Forensic Instance, Snapshots, Volume")

        parallel_create.branch(create_forensic_instance_task)
        
        parallel_create.branch(create_snapshot_from_isolated_instance_task.next(get_snapshot_status_task).next(is_snapshot_complete_choice.when(
                yes_snapshot_complete_con, create_ebs_volume_from_ss_task.next(get_ebs_volume_status_task).next(is_ebs_volume_available_choice.when(
                        no_ebs_volume_available_con, volume_creation_complete_wait.next(get_ebs_volume_status_task)
                    ).otherwise(volume_create_complete_pass))
            ).otherwise(snapshot_creation_complete_wait.next(get_snapshot_status_task))))
        
        # Build the state machine definition 
        chain = sfn.Chain.start(describe_ec2_task).next(disable_ec2_termination_task).next(get_autoscaling_info_task).next(has_asg_choice.when
                    (
                        yes_asg_con, detach_instance_from_asg_task
                    ).afterwards(include_otherwise=True)
                ).next(parallel_create).next(attach_volume_task).next(allow_forensic_instace_ingress_task).next(tag_instance_as_quarantie_task)

        # State machine      
        sm = sfn.StateMachine(self, "StateMachine",
            definition=chain
        )

        CfnOutput(self, "StepFunctionArn", description="Step function ARN",
            value=sm.state_machine_arn       
        )

        CfnOutput(self, "StpFunctionURL", description="Step Function URL",
            value=Fn.sub("https://${AWS::Region}.console.aws.amazon.com/states/home?region=${AWS::Region}#/statemachines/view/${EC2IsolationStateMachine}",
               {"EC2IsolationStateMachine": sm.state_machine_arn}
            )       
        )

# lunch the stack.
app = App()
Ec2IsolationStack(
    app,
    "Ec2IsolationPython",
    env=Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    vpc_id="<your VPC ID>"
)
app.synth()
