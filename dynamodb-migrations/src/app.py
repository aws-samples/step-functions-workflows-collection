import time

def lambda_handler(event, context):
    # Your migration code goes here
    # The record is passed in as the event. Change the data/structure as needed
    # return the modified event
    try:
        # Example convert clf time to unix time
        event["timestamp"]["S"] = str(time.mktime(time.strptime(event["timestamp"]["S"], "%d/%b/%Y:%H:%M:%S %z")))
        return event
    except ValueError as e:
        print('ValueError:', e)
        return