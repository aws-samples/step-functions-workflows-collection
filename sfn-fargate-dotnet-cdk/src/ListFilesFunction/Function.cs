using Amazon.Lambda.Core;
using WorkflowApp.Models;

// Assembly attribute to enable the Lambda function's JSON input to be converted into a .NET class.
[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.SystemTextJson.DefaultLambdaJsonSerializer))]

namespace ListFilesFunction;

public class Function
{    
    public CopyRequest FunctionHandler(CopyRequest copyRequest, ILambdaContext context)
    {
        LambdaLogger.Log($"Listing files for copy request from {copyRequest.SourceLocation} to {copyRequest.TargetLocation} started...");
        Thread.Sleep(500);

        LambdaLogger.Log($"Listing files for copy request from {copyRequest.SourceLocation} to {copyRequest.TargetLocation} finished...");
        return copyRequest;
    }
}
