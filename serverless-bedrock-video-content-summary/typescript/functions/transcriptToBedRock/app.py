import json
import boto3
import os
# Get list of available foundational models using the 'bedrock' client.
# This allows the application to interact with the service configuratoin.
bedrock = boto3.client('bedrock')
models = str(bedrock.list_foundation_models())
table_name = os.environ["TABLE_NAME"]
dynamodb = boto3.client('dynamodb')
ddb = boto3.resource("dynamodb")
table = ddb.Table(table_name)# 'bedrock_runtime' is the client to consume the Bedrock service
bedrock_runtime = boto3.client('bedrock-runtime')
ssm = boto3.client('ssm')

# Create an S3 client to interact with S3
s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Log the incoming events from the state machine
    print('event from state-machine', event)

    # Extract information about the transcription job from the event
    transcriptionResultBucketObject = event['TranscriptionJob']['TranscriptionJob']['Transcript']['TranscriptFileUri']
    transcriptionBucketName = transcriptionResultBucketObject.split("/")[-2]
    transcriptionKeyName = transcriptionResultBucketObject.split("/")[-1]

    # Get ddb PK from file name (video_id)
    video_id = (event['detail']['object']['key'].split('/')[-1]).split('.')[0]

    # Get the transcription result from S3
    transcriptionResponseObjectfromS3 = s3.get_object(
        Bucket = transcriptionBucketName,
        Key = transcriptionKeyName
    )

    # Read the content of the transcription result in bytes format
    transcriptionResponseBodyfromS3 = transcriptionResponseObjectfromS3.get('Body')
    transcriptionResponseBodyContentfromS3 = transcriptionResponseBodyfromS3.read()
    
    # Convert the transcription result from JSOn bytes to a Python Dictionary
    transcriptionResponseJsonContentfromS3 = json.loads(transcriptionResponseBodyContentfromS3)
    
    # Extract the transcript message from the transcription result
    transcriptMessage = str(transcriptionResponseJsonContentfromS3['results']['transcripts'][0]['transcript'])
    
    # Create a prompt for the Bedrock model by combining a text summary prompt and the transcript message
    textSummaryPrompt = "Summarize this meeting transcript: "
    bedrockPrompt = textSummaryPrompt+transcriptMessage
    
    # Log the text summary prompt
    print('text summary promt:', transcriptMessage)

    #Specify the Besdrock model Id from parameter store
    # model_id = "ai21.j2-ultra-v1"
    try:
        # Get the parameter value
        response = ssm.get_parameter(
            Name='/vod/shared/bedrock-llm-name',
            WithDecryption=True  # Set to False if the parameter is not encrypted
        )
        model_id = response['Parameter']['Value']


    except Exception as e:
        raise e

    # Prepare the request body with the prompt and model parameters   
    body = json.dumps(
      {
          "prompt": bedrockPrompt, 
          "maxTokens": 200,
          "temperature": 0.7,
          "topP": 1,
       }
     )
     
     # Invoke the Bedrock model to get a response
    response = bedrock_runtime.invoke_model(
       body=body, 
       modelId=model_id,
       accept='application/json', 
       contentType='application/json'
     )
    
    # Convert the response body from JSON bytes to a python dictionary
    response_body_bedrock = json.loads(response.get('body').read())
    
     # The response from the model now mapped to the answer
    summary_answer_bedrock = response_body_bedrock.get('completions')[0].get('data').get('text')
    

    update_item_dynamodb(video_id, summary_answer_bedrock)
    # Log the final answer
    print('final answer', summary_answer_bedrock)
    return {
        'statusCode': 200,
        'body': summary_answer_bedrock
    }

def update_item_dynamodb(video_id, summary):

    response = dynamodb.update_item(
        TableName=table_name,
        Key={
            'video_id': {'S': video_id}
        },
        UpdateExpression='SET summary = :val',
        ExpressionAttributeValues={
            ':val': {'S': summary}
        },
        ReturnValues="UPDATED_NEW"
    )

    return response
