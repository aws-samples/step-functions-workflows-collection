def lambda_handler(event, context):
    print("Executing First Lambda Function")
    return {
        'statusCode': 200,
        'body': 'First Lambda Function executed successfully'
    }