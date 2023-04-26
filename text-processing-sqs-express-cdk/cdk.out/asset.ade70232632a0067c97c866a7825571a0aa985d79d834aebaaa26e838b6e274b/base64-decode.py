import base64

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'input': event['input'],
        'output': base64.b64decode(event['input']).decode('utf-8')
    }
