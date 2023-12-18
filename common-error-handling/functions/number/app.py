

def lambda_handler(event, context):
    print(event)
    #if we don't have a number this will throw an exception
    number = int(event["Number"])
    return number
