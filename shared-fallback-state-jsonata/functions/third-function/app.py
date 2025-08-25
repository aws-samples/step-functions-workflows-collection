def lambda_handler(event, context):
    print("Executing Third Lambda Function")
    print(raising_error)
    return {
        'statusCode': 200,
        'body': 'Third Lambda Function executed successfully'
    }