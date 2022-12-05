import json
import datetime
import math
import random
import uuid

"""
Sample Lambda function simulates buying a random number of shares of a stock.
For demonstration purposes, this function does not actually perform any transactions but simulates returning transaction details.

"""


def handler(event, context):
    _price = event["stock_price"]

    print(f"Buying for ${_price}")
    _now = datetime.datetime.now()

    transaction_result = {
        "price": _price,
        "transaction_id": str(uuid.uuid1),
        "type": "buy",
        "qty": getRandomInt(1, 100),
        "timestamp": str(_now),
    }

    return transaction_result


# generate a random int between 2 values
def getRandomInt(min, max):
    min = math.ceil(min)
    max = math.floor(max)
    return math.floor(random.random() * (max - min) + min)
