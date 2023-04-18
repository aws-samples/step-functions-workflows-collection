import re

def lambda_handler(event, context):
    input = event['input']
    cleaned_string = re.sub('\W+',' ', input)
    return {
        'statusCode': 200,
        'input': input,
        'output': cleaned_string
    }
