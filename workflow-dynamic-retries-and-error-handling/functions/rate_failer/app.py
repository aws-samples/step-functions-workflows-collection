from random import random


def lambda_handler(event: dict, context: dict) -> dict:
    """Sample Lambda function which fails if a randomly generated number is
    less than or equal to "failureRate" from the input event.

    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function.
        Contains one key - "failureRate" which has a floating point value between
        0 and 1 describing the chance of failure.

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        dict: Object containing the randomly generated number that was above failureRate
    """
    failure_rate = event["failureRate"]
    rand_number = random()

    if rand_number <= failure_rate:
        raise Exception(
            f"Oops! We failed very statistically because {rand_number} is less than {failure_rate}"
        )

    return {"randomDraw": rand_number}
