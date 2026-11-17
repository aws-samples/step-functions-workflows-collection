# PowerShell deployment script for AWS Feature Relevance Notification System
param(
    [string]$SlackWebhookUrl = "",
    [string]$BedrockModelId = "us.anthropic.claude-sonnet-4-6",
    [string]$KnowledgeBaseId = "",
    [string]$StackName = "feature-relevance-poc",
    [switch]$DestroyInfra
)

$ErrorActionPreference = "Stop"

Write-Host "=== AWS Feature Relevance Notification System Deployment ===" -ForegroundColor Green

# Use shared prerequisites check
Write-Host "Checking prerequisites..." -ForegroundColor Yellow
& "..\..\shared\scripts\check-prerequisites.ps1" -MinPythonVersion "3.9"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Prerequisites check failed" -ForegroundColor Red
    exit 1
}

# Get region
$Region = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION }
          elseif ($env:AWS_REGION) { $env:AWS_REGION }
          else { (aws configure get region 2>$null) }
if (-not $Region) { $Region = "us-east-1" }
Write-Host "Using region: $Region" -ForegroundColor Cyan

# Check SAM CLI is installed
Write-Host "Checking AWS SAM CLI..." -ForegroundColor Yellow
$samVersion = sam --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: AWS SAM CLI not found." -ForegroundColor Red
    Write-Host "Install from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html" -ForegroundColor Cyan
    exit 1
}
Write-Host "  OK: $samVersion" -ForegroundColor Green

# Destroy mode
if ($DestroyInfra) {
    Write-Host "Destroying infrastructure..." -ForegroundColor Red
    sam delete --stack-name $StackName --region $Region --no-prompts
    Write-Host "Infrastructure destruction completed" -ForegroundColor Green
    exit 0
}

# Build SAM application
Write-Host "`nBuilding SAM application..." -ForegroundColor Yellow
Push-Location sam-app
try {
    sam build --template template.yaml
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: SAM build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  SAM build succeeded" -ForegroundColor Green

    # Deploy SAM application
    Write-Host "`nDeploying SAM application..." -ForegroundColor Yellow

    $deployArgs = @(
        "deploy",
        "--stack-name", $StackName,
        "--region", $Region,
        "--resolve-s3",
        "--capabilities", "CAPABILITY_IAM", "CAPABILITY_NAMED_IAM",
        "--no-confirm-changeset",
        "--parameter-overrides",
        "BedrockModelId=$BedrockModelId",
        "KnowledgeBaseId=$KnowledgeBaseId"
    )

    if (-not [string]::IsNullOrEmpty($SlackWebhookUrl)) {
        $deployArgs += "SlackWebhookUrl=$SlackWebhookUrl"
    }

    sam @deployArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: SAM deploy failed" -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

# Get stack outputs
Write-Host "`nGetting stack outputs..." -ForegroundColor Yellow
$outputs = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs" --output json --region $Region --no-cli-pager 2>&1

if ($LASTEXITCODE -eq 0) {
    $outputsJson = $outputs | ConvertFrom-Json

    $stateMachineArn = ""
    $rssFunction = ""
    $scorerFunction = ""
    $workloadManager = ""
    $profilesTable = ""

    foreach ($output in $outputsJson) {
        switch ($output.OutputKey) {
            "StateMachineArn" { $stateMachineArn = $output.OutputValue }
            "RSSIngestionFunctionName" { $rssFunction = $output.OutputValue }
            "RelevanceScorerFunctionName" { $scorerFunction = $output.OutputValue }
            "WorkloadManagerFunctionName" { $workloadManager = $output.OutputValue }
            "WorkloadProfilesTableName" { $profilesTable = $output.OutputValue }
        }
    }
}

# Print deployment summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Region:              $Region" -ForegroundColor Cyan
Write-Host "  Stack Name:          $StackName" -ForegroundColor Cyan
Write-Host "  State Machine:       $stateMachineArn" -ForegroundColor Cyan
Write-Host "  RSS Ingestion:       $rssFunction" -ForegroundColor Cyan
Write-Host "  Relevance Scorer:    $scorerFunction" -ForegroundColor Cyan
Write-Host "  Workload Manager:    $workloadManager" -ForegroundColor Cyan
Write-Host "  Profiles Table:      $profilesTable" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Create a workload profile:" -ForegroundColor White
Write-Host "     aws lambda invoke --function-name $workloadManager \" -ForegroundColor Gray
Write-Host "       --cli-binary-format raw-in-base64-out \" -ForegroundColor Gray
Write-Host "       --payload '{""action"":""create"",""profile"":{...}}' /tmp/out.json" -ForegroundColor Gray
Write-Host "  2. Test the pipeline:" -ForegroundColor White
Write-Host "     aws lambda invoke --function-name $rssFunction \" -ForegroundColor Gray
Write-Host "       --cli-binary-format raw-in-base64-out \" -ForegroundColor Gray
Write-Host "       --payload '{""test_mode"":true}' /tmp/test.json" -ForegroundColor Gray
Write-Host "  3. Monitor in Step Functions console" -ForegroundColor White
Write-Host ""
Write-Host "To destroy the infrastructure later, run:" -ForegroundColor Yellow
Write-Host "  .\deploy-all.ps1 -DestroyInfra" -ForegroundColor White
