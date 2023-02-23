/*
@author : Swapnil Singh
@date : 01/22/2023
*/
import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import {
  HttpIntegration,
  MockIntegration,
  RequestValidator,
  RestApi,
} from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";

export class APIStack extends cdk.Stack {
  public readonly restApi: apigateway.RestApi;

  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create Pet Store Rest API

    this.restApi = new RestApi(this, "petStoreApi", {
      restApiName: "Pet Store CDK",
      description:
        "This is a sample API that integrates via HTTP with AWS demo Pet Store endpoints",
      cloudWatchRole: true,
      deploy: true,
      deployOptions: {
        stageName: "dev",
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
      },
    });

    //Create Model for Pet Object
    const petModel = this.restApi.addModel("Pet", {
      contentType: "application/json",
      modelName: "Pet",
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          id: { type: apigateway.JsonSchemaType.INTEGER },
          type: { type: apigateway.JsonSchemaType.STRING },
          price: { type: apigateway.JsonSchemaType.NUMBER },
        },
      },
    });

    const requestValidator = new apigateway.RequestValidator(this, 'PostRequestValidator', {
      restApi: this.restApi,
      requestValidatorName: 'postrequestValidator',
      validateRequestBody: true,
      validateRequestParameters: false,
    });

    
    const methodResponse: apigateway.MethodResponse = {
      statusCode: "200",
    };

    const integrationResponse: apigateway.IntegrationResponse = {
      statusCode: "200",
    };
    //Using AWS hosted pet store api as an HTTP Integration endpoint for our api. Add resource pets and method GET, POST and OPTIONS
    const pets = this.restApi.root.addResource("pets");
    pets.addMethod(
      "GET",
      new HttpIntegration(
        "http://petstore.execute-api.us-east-1.amazonaws.com/petstore/pets",
        {
          httpMethod: "GET",
          proxy: false,
          options: {
            integrationResponses: [integrationResponse],
          },
        }
      ),
    ).addMethodResponse(methodResponse);
  

    const postMethod = pets.addMethod(
      "POST",
      new HttpIntegration(
        "http://petstore.execute-api.us-east-1.amazonaws.com/petstore/pets",
        {
          httpMethod: "POST",
          proxy: false,
          options: {
            integrationResponses: [integrationResponse],
          },
        }
      ),
      { requestModels: { "application/json": petModel },
        requestValidator : requestValidator
       },

    ).addMethodResponse(methodResponse);

    pets.addMethod(
      "OPTIONS",
      new MockIntegration({
        requestTemplates: { "application/json": '{ "statusCode": 200 }' },
      })
    );

    //************ Add resource pet and method GET and OPTIONS

   const onepet =  pets.addResource("{id}");
     onepet.addMethod(
        "GET",
        new HttpIntegration(
          "http://petstore.execute-api.us-east-1.amazonaws.com/petstore/pets/{id}",
          {
            httpMethod: "GET",
            proxy: false,
            options: {
              integrationResponses: [integrationResponse],
            },
          }
        )
      )
      .addMethodResponse(methodResponse);

    onepet.addMethod(
      "OPTIONS",
      new MockIntegration({
        requestTemplates: { "application/json": '{ "statusCode": 200 }' },
      })
    );
  }
}
