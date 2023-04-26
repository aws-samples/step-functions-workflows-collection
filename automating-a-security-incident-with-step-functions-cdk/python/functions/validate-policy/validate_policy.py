import json
import os
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger()


def handler(event, context):
    logger.setLevel(logging.INFO)
    restricted_actions = os.environ["RESTRICTED_ACTIONS"].split(",")
    policy = json.loads(event["policy"])
    policy_actions = policy["Statement"][0]["Action"]

    found = False
    found = any(x in restricted_actions for x in policy_actions)

    if found:
        message = f"Policy found to have one or more of the following restricted actions: \n{restricted_actions}\n Admin needs to manually aprove to proceed."
        action = "remedy"
    else:
        message = f"No restricted actions found in the policy.  \nPolicy:\n \n{event['policy']}"
        action = "alert"

    logger.info(message)
    logger.info(f"Action taken: {action}")
    return {"message": message, "action": action}
