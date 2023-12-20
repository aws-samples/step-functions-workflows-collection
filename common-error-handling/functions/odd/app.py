from random import randint


def lambda_handler(event, context):
    number = int(event['Number'])
    if number % 2 == 0:
        raise Exception("even number") 
    else:
        return "woohoo odd number"

