import json
import math
import random


# Sample function with mocks the operation of checking the number of batch jobs needing fan out.
# For demo purposes, it will return a random number between 2 and 10.
def handler(event, context):
    num = random.randint(2, 10)

    result = {"input": str(num)}
    return result
