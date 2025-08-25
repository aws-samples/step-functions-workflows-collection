def lambda_handler(event, context):
    print("Executing Second Lambda Function")
    return {
        'statusCode': 200,
        'body': 'Second Lambda Function executed successfully'
    }