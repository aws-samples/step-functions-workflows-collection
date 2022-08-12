import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (aws_apigateway as apigateway,
                     aws_stepfunctions as stepfunctions,
                     aws_stepfunctions_tasks as tasks,
                     aws_dynamodb as dynamodb,
                     aws_logs as logs)

class DynamicRestApi(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Define a cloudwatch log group for Step Function logs
        step_function_log_group = logs.LogGroup(self, "StepFunctionLogGroup", log_group_name="RestApiExpressStepFunction" )

        # Create a DynamoDB table for Books
        books_table = dynamodb.Table(self, "BooksTable", table_name="Books",
            partition_key=dynamodb.Attribute(name="book_id",
            type=dynamodb.AttributeType.STRING))


        # Define a Stepfunction task for calling DynamoDB PutItem API
        dynamo_put_item_task = tasks.DynamoPutItem(self, "DynamoDB Put Item Task",
            item={"book_id": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.body.book_id")),
                    "Author" : tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.body.author"))},
            table=books_table
        )

        # Define a Stepfunction task for calling DynamoDB GetItem API
        dynamo_get_item_task = tasks.DynamoGetItem(self, "DynamoDB Get Item Task",
            key={"book_id": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.querystring.book_id"))},
            table=books_table
        )

        # Define a Stepfunction task for calling DynamoDB DeleteItem API
        dynamo_delete_item_task = tasks.DynamoDeleteItem(self, "DynamoDB Delete Item Tasktem",
            key={"book_id": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.path.book_id"))},
            condition_expression="attribute_exists(book_id)",
            table=books_table
        )


        # A state machine definition that has a Choice state inside to make a desision base of input "httpMethod" and call DynamoDB PutItem, GetItem, DeleteItem APIs accordingly
        state_machine_definition = stepfunctions.Choice(self, "Choice based on API Call Method").when(stepfunctions.Condition.string_equals("$.httpMethod", "GET"), dynamo_get_item_task).when(stepfunctions.Condition.string_equals("$.httpMethod", "POST"), dynamo_put_item_task).when(stepfunctions.Condition.string_equals("$.httpMethod", "DELETE"), dynamo_delete_item_task)

        # Define Express Step function that is exceuted when Rest api endpoint are called
        state_machine = stepfunctions.StateMachine(self, "StateMachine",
            state_machine_name="book_api_start_execution_state_machine",
            definition=state_machine_definition,
            state_machine_type=stepfunctions.StateMachineType.EXPRESS,
            tracing_enabled=True,
            logs=stepfunctions.LogOptions(
                destination=step_function_log_group,
                level=stepfunctions.LogLevel.ALL,
                include_execution_data=True)
            )


        stateMachineARN = state_machine.state_machine_arn

        # Request template mapping to add HTTP method to the input that Step function receives
        RequestTemplateJson = "#set($inputString = '')\r\n#set($includeHeaders = true)\r\n#set($includeQueryString = true)\r\n#set($includePath = true)\r\n#set($includeAuthorizer = false)\r\n#set($allParams = $input.params())\r\n#set($inputRoot='\"httpMethod\" :\"'+ $context.httpMethod+'\"')\r\n{\r\n    \"stateMachineArn\": \""+ stateMachineARN +"\",\r\n\r\n    #set($inputString = \"$inputString,@@body@@: $input.body\")\r\n\r\n    #if ($includeHeaders)\r\n        #set($inputString = \"$inputString, @@header@@:{\")\r\n        #foreach($paramName in $allParams.header.keySet())\r\n            #set($inputString = \"$inputString @@$paramName@@: @@$util.escapeJavaScript($allParams.header.get($paramName))@@\")\r\n            #if($foreach.hasNext)\r\n                #set($inputString = \"$inputString,\")\r\n            #end\r\n        #end\r\n        #set($inputString = \"$inputString },$inputRoot\")\r\n\r\n        \r\n    #end\r\n\r\n    #if ($includeQueryString)\r\n        #set($inputString = \"$inputString, @@querystring@@:{\")\r\n        #foreach($paramName in $allParams.querystring.keySet())\r\n            #set($inputString = \"$inputString @@$paramName@@: @@$util.escapeJavaScript($allParams.querystring.get($paramName))@@\")\r\n            #if($foreach.hasNext)\r\n                #set($inputString = \"$inputString,\")\r\n            #end\r\n        #end\r\n        #set($inputString = \"$inputString }\")\r\n    #end\r\n\r\n    #if ($includePath)\r\n        #set($inputString = \"$inputString, @@path@@:{\")\r\n        #foreach($paramName in $allParams.path.keySet())\r\n            #set($inputString = \"$inputString @@$paramName@@: @@$util.escapeJavaScript($allParams.path.get($paramName))@@\")\r\n            #if($foreach.hasNext)\r\n                #set($inputString = \"$inputString,\")\r\n            #end\r\n        #end\r\n        #set($inputString = \"$inputString }\")\r\n    #end\r\n    \r\n    #if ($includeAuthorizer)\r\n        #set($inputString = \"$inputString, @@authorizer@@:{\")\r\n        #foreach($paramName in $context.authorizer.keySet())\r\n            #set($inputString = \"$inputString @@$paramName@@: @@$util.escapeJavaScript($context.authorizer.get($paramName))@@\")\r\n            #if($foreach.hasNext)\r\n                #set($inputString = \"$inputString,\")\r\n            #end\r\n        #end\r\n        #set($inputString = \"$inputString }\")\r\n    #end\r\n\r\n    #set($requestContext = \"\")\r\n    ## Check if the request context should be included as part of the execution input\r\n    #if($requestContext && !$requestContext.empty)\r\n        #set($inputString = \"$inputString,\")\r\n        #set($inputString = \"$inputString @@requestContext@@: $requestContext\")\r\n    #end\r\n\r\n    #set($inputString = \"$inputString}\")\r\n    #set($inputString = $inputString.replaceAll(\"@@\",'\"'))\r\n    #set($len = $inputString.length() - 1)\r\n    \"input\": \"{$util.escapeJavaScript($inputString.substring(1,$len)).replaceAll(\"\\\\'\",\"'\")}\"\r\n}"
        
        # Response template mapping to send 404 HTTP response code instead of 200 in response to a get request when the item does not exist in "Books" database, DynamoDB does not return error when the item does not exists in table
        GetRequestTemplateJson = "#set($inputRoot = $input.path('$'))\r\n#set($inputBookId = $input.params('book_id'))\r\n#set($integration_output = $input.path('$.output'))\r\n#if($input.path('$.status').toString().equals(\"FAILED\"))\r\n#set($context.responseOverride.status = 500)\r\n{\r\n\"error\": \"$input.path('$.error')\",\r\n\"cause\": \"$input.path('$.cause')\"\r\n}\r\n#elseif(!$integration_output.contains(\"Item\"))\r\n#set($context.responseOverride.status = 404)\r\n{ \"Book ID \"$inputBookId\" not found in Books database\" }\r\n#else\r\n$input.path('$.output')\r\n#end"

        # Response template mapping to map 500 error to 404 in case item "book_id" doesn't exist in database
        DeleteRequestTemplateJson = "#set($inputRoot = $input.path('$'))\r\n#set($inputBookId = $input.params('book_id'))\r\n#if($input.path('$.error').toString().equals(\"DynamoDB.ConditionalCheckFailedException\"))\r\n#set($context.responseOverride.status = 404)\r\n{\r\n\"error\": \"$input.path('$.error')\",\r\n\"cause\": \"The item \"$inputBookId\" does not exist in database to delete\"\r\n}\r\n#elseif($input.path('$.status').toString().equals(\"FAILED\"))\r\n#set($context.responseOverride.status = 500)\r\n{\r\n\"error\": \"$input.path('$.error')\",\r\n\"cause\": \"$input.path('$.cause')\"\r\n}\r\n#else\r\n$input.path('$.output')\r\n#end"


        
        
        # Define "books-api" rest api
        rest_api = apigateway.RestApi(self, "books-api",
            deploy_options=apigateway.StageOptions(
                stage_name="dev",
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            )
        )

        rest_api.root.add_method("ANY")

        books = rest_api.root.add_resource("books")

        # Adding Post method to /books resource
        books.add_method("POST", apigateway.StepFunctionsIntegration.start_execution(state_machine,
            passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={
            "application/json": RequestTemplateJson
            }
        ))

        # Adding path parameter {book_id} to /books resource
        book_id = books.add_resource("{book_id}")


        # Adding Delete method to /books/{book_id} path with Step function integration
        book_id.add_method("DELETE", apigateway.StepFunctionsIntegration.start_execution(state_machine,
            passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={
                "application/json": RequestTemplateJson
            },
            integration_responses=[apigateway.IntegrationResponse(status_code="200",
                response_templates={
                    "application/json": DeleteRequestTemplateJson
                }
            )]    
        ))

        # Adding Get method to /books/{book_id} path with Step function integration
        book_id.add_method("GET", apigateway.StepFunctionsIntegration.start_execution(state_machine,
            passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={
                "application/json": RequestTemplateJson
            },
            integration_responses=[apigateway.IntegrationResponse(status_code="200",
                response_templates={
                    "application/json": GetRequestTemplateJson
                }
            )]
        ))