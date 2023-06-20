""" 
Sample Lambda function that is supposed to perform some user dependent action which is simulated by adding a sleep statement.
"""
import time

def lambda_handler(event, context):
    print(event)
    time.sleep(100)
    return {"message":"task completed"}