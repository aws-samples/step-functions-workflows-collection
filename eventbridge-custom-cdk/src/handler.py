import json


def handler(event, context):
    print("Hello from Lambda")

    responseBody = {"Status": 200}

    return json.dumps(responseBody)
