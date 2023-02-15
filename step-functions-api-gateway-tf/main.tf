terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>4.0"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile_name
}

data "aws_caller_identity" "caller" {}
data "aws_partition" "partition" {}


locals {
  project_name = "step-functions-api-gateway"
  account_id = data.aws_caller_identity.caller.account_id
}


resource "aws_api_gateway_rest_api" "petstore" {
  body = jsonencode({
  "swagger" : "2.0",
  "info" : {
    "description" : "Your first API with Amazon API Gateway. This is a sample API that integrates via HTTP with our demo Pet Store endpoints",
    "version" : "2022-12-20T17:56:02Z",
    "title" : "PetStore"
  },
  "basePath" : "/dev",
  "schemes" : [ "https" ],
  "paths" : {
    "/" : {
      "get" : {
        "consumes" : [ "application/json" ],
        "produces" : [ "text/html" ],
        "responses" : {
          "200" : {
            "description" : "200 response",
            "headers" : {
              "Content-Type" : {
                "type" : "string"
              }
            }
          }
        },
        "x-amazon-apigateway-integration" : {
          "responses" : {
            "default" : {
              "statusCode" : "200",
              "responseParameters" : {
                "method.response.header.Content-Type" : "'text/html'"
              },
              "responseTemplates" : {
                "text/html" : "<html>\n    <head>\n        <style>\n        body {\n            color: #333;\n            font-family: Sans-serif;\n            max-width: 800px;\n            margin: auto;\n        }\n        </style>\n    </head>\n    <body>\n        <h1>Welcome to your Pet Store API</h1>\n        <p>\n            You have successfully deployed your first API. You are seeing this HTML page because the <code>GET</code> method to the root resource of your API returns this content as a Mock integration.\n        </p>\n        <p>\n            The Pet Store API contains the <code>/pets</code> and <code>/pets/{petId}</code> resources. By making a <a href=\"/$context.stage/pets/\" target=\"_blank\"><code>GET</code> request</a> to <code>/pets</code> you can retrieve a list of Pets in your API. If you are looking for a specific pet, for example the pet with ID 1, you can make a <a href=\"/$context.stage/pets/1\" target=\"_blank\"><code>GET</code> request</a> to <code>/pets/1</code>.\n        </p>\n        <p>\n            You can use a REST client such as <a href=\"https://www.getpostman.com/\" target=\"_blank\">Postman</a> to test the <code>POST</code> methods in your API to create a new pet. Use the sample body below to send the <code>POST</code> request:\n        </p>\n        <pre>\n{\n    \"type\" : \"cat\",\n    \"price\" : 123.11\n}\n        </pre>\n    </body>\n</html>"
              }
            }
          },
          "requestTemplates" : {
            "application/json" : "{\"statusCode\": 200}"
          },
          "passthroughBehavior" : "when_no_match",
          "type" : "mock"
        }
      }
    },
    "/pets" : {
      "get" : {
        "produces" : [ "application/json" ],
        "parameters" : [ {
          "name" : "type",
          "in" : "query",
          "required" : false,
          "type" : "string"
        }, {
          "name" : "page",
          "in" : "query",
          "required" : false,
          "type" : "string"
        } ],
        "responses" : {
          "200" : {
            "description" : "200 response",
            "schema" : {
              "$ref" : "#/definitions/Pets"
            },
            "headers" : {
              "Access-Control-Allow-Origin" : {
                "type" : "string"
              }
            }
          }
        },
        "x-amazon-apigateway-integration" : {
          "httpMethod" : "GET",
          "uri" : "http://petstore.execute-api.${var.region}.amazonaws.com/petstore/pets",
          "responses" : {
            "default" : {
              "statusCode" : "200",
              "responseParameters" : {
                "method.response.header.Access-Control-Allow-Origin" : "'*'"
              }
            }
          },
          "requestParameters" : {
            "integration.request.querystring.page" : "method.request.querystring.page",
            "integration.request.querystring.type" : "method.request.querystring.type"
          },
          "passthroughBehavior" : "when_no_match",
          "type" : "http"
        }
      },
      "post" : {
        "operationId" : "CreatePet",
        "consumes" : [ "application/json" ],
        "produces" : [ "application/json" ],
        "parameters" : [ {
          "in" : "body",
          "name" : "NewPet",
          "required" : true,
          "schema" : {
            "$ref" : "#/definitions/NewPet"
          }
        } ],
        "responses" : {
          "200" : {
            "description" : "200 response",
            "schema" : {
              "$ref" : "#/definitions/NewPetResponse"
            },
            "headers" : {
              "Access-Control-Allow-Origin" : {
                "type" : "string"
              }
            }
          }
        },
        "x-amazon-apigateway-integration" : {
          "httpMethod" : "POST",
          "uri" : "http://petstore.execute-api.${var.region}.amazonaws.com/petstore/pets",
          "responses" : {
            "default" : {
              "statusCode" : "200",
              "responseParameters" : {
                "method.response.header.Access-Control-Allow-Origin" : "'*'"
              }
            }
          },
          "passthroughBehavior" : "when_no_match",
          "type" : "http"
        }
      },
      "options" : {
        "consumes" : [ "application/json" ],
        "produces" : [ "application/json" ],
        "responses" : {
          "200" : {
            "description" : "200 response",
            "schema" : {
              "$ref" : "#/definitions/Empty"
            },
            "headers" : {
              "Access-Control-Allow-Origin" : {
                "type" : "string"
              },
              "Access-Control-Allow-Methods" : {
                "type" : "string"
              },
              "Access-Control-Allow-Headers" : {
                "type" : "string"
              }
            }
          }
        },
        "x-amazon-apigateway-integration" : {
          "responses" : {
            "default" : {
              "statusCode" : "200",
              "responseParameters" : {
                "method.response.header.Access-Control-Allow-Methods" : "'POST,GET,OPTIONS'",
                "method.response.header.Access-Control-Allow-Headers" : "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'",
                "method.response.header.Access-Control-Allow-Origin" : "'*'"
              }
            }
          },
          "requestTemplates" : {
            "application/json" : "{\"statusCode\": 200}"
          },
          "passthroughBehavior" : "when_no_match",
          "type" : "mock"
        }
      }
    },
    "/pets/{petId}" : {
      "get" : {
        "operationId" : "GetPet",
        "produces" : [ "application/json" ],
        "parameters" : [ {
          "name" : "petId",
          "in" : "path",
          "required" : true,
          "type" : "string"
        } ],
        "responses" : {
          "200" : {
            "description" : "200 response",
            "schema" : {
              "$ref" : "#/definitions/Pet"
            },
            "headers" : {
              "Access-Control-Allow-Origin" : {
                "type" : "string"
              }
            }
          }
        },
        "x-amazon-apigateway-integration" : {
          "httpMethod" : "GET",
          "uri" : "http://petstore.execute-api.${var.region}.amazonaws.com/petstore/pets/{petId}",
          "responses" : {
            "default" : {
              "statusCode" : "200",
              "responseParameters" : {
                "method.response.header.Access-Control-Allow-Origin" : "'*'"
              }
            }
          },
          "requestParameters" : {
            "integration.request.path.petId" : "method.request.path.petId"
          },
          "passthroughBehavior" : "when_no_match",
          "type" : "http"
        }
      },
      "options" : {
        "consumes" : [ "application/json" ],
        "produces" : [ "application/json" ],
        "parameters" : [ {
          "name" : "petId",
          "in" : "path",
          "required" : true,
          "type" : "string"
        } ],
        "responses" : {
          "200" : {
            "description" : "200 response",
            "schema" : {
              "$ref" : "#/definitions/Empty"
            },
            "headers" : {
              "Access-Control-Allow-Origin" : {
                "type" : "string"
              },
              "Access-Control-Allow-Methods" : {
                "type" : "string"
              },
              "Access-Control-Allow-Headers" : {
                "type" : "string"
              }
            }
          }
        },
        "x-amazon-apigateway-integration" : {
          "responses" : {
            "default" : {
              "statusCode" : "200",
              "responseParameters" : {
                "method.response.header.Access-Control-Allow-Methods" : "'GET,OPTIONS'",
                "method.response.header.Access-Control-Allow-Headers" : "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'",
                "method.response.header.Access-Control-Allow-Origin" : "'*'"
              }
            }
          },
          "requestTemplates" : {
            "application/json" : "{\"statusCode\": 200}"
          },
          "passthroughBehavior" : "when_no_match",
          "type" : "mock"
        }
      }
    }
  },
  "definitions" : {
    "Pets" : {
      "type" : "array",
      "items" : {
        "$ref" : "#/definitions/Pet"
      }
    },
    "Empty" : {
      "type" : "object"
    },
    "NewPetResponse" : {
      "type" : "object",
      "properties" : {
        "pet" : {
          "$ref" : "#/definitions/Pet"
        },
        "message" : {
          "type" : "string"
        }
      }
    },
    "Pet" : {
      "type" : "object",
      "properties" : {
        "id" : {
          "type" : "integer"
        },
        "type" : {
          "type" : "string"
        },
        "price" : {
          "type" : "number"
        }
      }
    },
    "NewPet" : {
      "type" : "object",
      "properties" : {
        "type" : {
          "$ref" : "#/definitions/PetType"
        },
        "price" : {
          "type" : "number"
        }
      }
    },
    "PetType" : {
      "type" : "string",
      "enum" : [ "dog", "cat", "fish", "bird", "gecko" ]
    }
  }
})

  name = "${local.project_name}-pet-api"
}


# State Machine's execution role
resource "aws_iam_role" "state_machine_exec_role" {
  name = "${local.project_name}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action : "sts:AssumeRole"
        Effect : "Allow"
        Sid : ""
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
  inline_policy {
    name = "${local.project_name}-api-invoke"
    policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "apigateway:*",
            "Resource": "arn:aws:apigateway:${var.region}:${local.account_id}:/restapis/${aws_api_gateway_rest_api.petstore.id}"
        }
    ]
})
  }
}

resource "aws_sfn_state_machine" "StepFunctionsStateMachine" {
    name = "${local.project_name}-statemachine"
    role_arn = aws_iam_role.state_machine_exec_role.arn
    definition = templatefile("${path.module}/statemachine/statemachine.asl.json",  {
    APIID = aws_api_gateway_rest_api.petstore.id,
    APIRoleArn    = aws_iam_role.state_machine_exec_role.arn,
    REGION = var.region,
    ACCOUNTID = local.account_id,
    STAGE = aws_api_gateway_stage.devstage.stage_name
    })
    }


# Output the State Machine ARN
output "state_machine_arn" {
  description = "ARN of sample state machine"
  value = aws_sfn_state_machine.StepFunctionsStateMachine.arn 
  
}

resource "aws_api_gateway_deployment" "petstoredep" {
  rest_api_id = aws_api_gateway_rest_api.petstore.id
}

resource "aws_api_gateway_stage" "devstage" {
  deployment_id = aws_api_gateway_deployment.petstoredep.id
  rest_api_id   = aws_api_gateway_rest_api.petstore.id
  stage_name    = "dev"
}

output "state_machine_name" {
  description = "Name of the sample state machine"
  value = aws_sfn_state_machine.StepFunctionsStateMachine.name
}

output "api_id" {
  description = "Name of SNS topic where result is published"
  value = aws_api_gateway_rest_api.petstore.id
  
}

output "api_arn" {
  description = "Name of SNS topic where result is published"
  value = aws_api_gateway_rest_api.petstore.execution_arn
  
}