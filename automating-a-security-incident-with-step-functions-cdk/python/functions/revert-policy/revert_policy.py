import boto3
import logging

client = boto3.client("iam")
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger()


def handler(event, context):
    logger.setLevel(logging.INFO)
    logger.info(
        f"Going to temporarily revert the policy until we get approval from the admin. Policy ARN: {event['policyMeta']['arn']}"
    )

    client.create_policy_version(
        PolicyArn=event["policyMeta"]["arn"],
        PolicyDocument='{"Version": "2012-10-17","Statement": [{ "Sid": "VisualEditor0","Effect": "Allow","Action": "logs:GetLogGroupFields", "Resource": "*"}] }',
        SetAsDefault=True,
    )

    client.delete_policy_version(
        PolicyArn=event["policyMeta"]["arn"],
        VersionId=event["policyMeta"]["defaultVersionId"],
    )

    return {
        "message": f"Policy {event['policyMeta']['policyName']} has been temporarily altered as it contains one or more of the following restricted Actions: \n{event['policy']}. \n Admin needs to approve or deny",
        "action": "remedy",
    }
