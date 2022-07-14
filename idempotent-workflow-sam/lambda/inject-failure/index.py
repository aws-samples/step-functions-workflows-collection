import random


def lambda_handler(event, context):
    if random.choice([True, False]):
        raise Exception("We got a failure")
    return "All good"
