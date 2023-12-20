

def lambda_handler(event, context):
    number = int(event['Number'])
    if number % 2 == 0:
        return "woohoo even number"
    else:
        raise Exception("odd number")
