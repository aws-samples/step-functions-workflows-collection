import boto3
import logging

client = boto3.client("iam")
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger()


def handler(event, context):
    logger.setLevel(logging.INFO)
    logger.info(
        f"Policy changes approved by admin for policy: {event['policyMeta']['policyName']}"
    )
    client.create_policy_version(
        PolicyArn=event["policyMeta"]["arn"],
        PolicyDocument=event["policy"],
        SetAsDefault=True,
    )
    return {
        "message": f"Policy {event['policyMeta']['policyName']} has been approved by admin.\n Policy:\n{event['policy']} ",
        "action": "remedy",
    }
