import json
from random import random


def error_handler(event: dict) -> dict:
    """
    Error handling logic goes here.

    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function.

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        dict: Empty object

    """
    return {
        "error_type": event["Error"]
    }  ## Mildly useless input passing, for demo purposes


def lambda_handler(event: dict, context: dict) -> dict:
    """Placeholder Lambda function for handling errors

    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function.

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        dict: result of error_handler() invocation
    """
    return error_handler(event)
