import math
import random

""" 
Sample Lambda function which mocks checking the price of a stock.
For demonstration purposes, this function simply generates a random integer and
returns this number as the stock price.

 """


def handler(event, context):

    # simulate a stock price with a random number
    price = getRandomInt(0, 100)
    print(f"Stock price is: {str(price)}")
    return {"stock_price": str(price)}


# generate a random int between 2 values
def getRandomInt(min, max):
    min = math.ceil(min)
    max = math.floor(max)
    return math.floor(random.random() * (max - min) + min)
