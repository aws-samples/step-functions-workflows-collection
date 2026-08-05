# AWS Feature Relevance Notification System

## Executive Summary

AWS publishes more than 200 feature announcements every month. For enterprise customers operating across dozens of AWS accounts, multiple business units, and hundreds of services, identifying which announcements matter to which workload is a manual, time-consuming process that often falls through the cracks.

This system solves that problem. It automatically ingests AWS "What's New" announcements, scores their relevance against customer workload profiles using Amazon Bedrock (Claude Sonnet 4), and delivers enriched Slack notifications with benefit categorization, impact estimates, and adoption guidance — routed directly to the appropriate account team channel.

**The result:** 200+ monthly announcements are transformed into 8-15 curated, actionable recommendations per workload — with zero manual effort after initial setup.

### Key Capabilities

- **Automated daily ingestion** of AWS What's New RSS feed
- **Multi-category AI scoring** across 8 benefit dimensions (not just cost)
- **Workload-specific analysis** grounded in the customer's actual architecture and scale
- **Knowledge Base integration** for deep context from architecture documents
- **Metadata filtering** ensures workload isolation — each workload only sees its own docs
- **Threshold-based noise reduction** — only high-relevance announcements generate notifications
- **Tier-0 prioritization** — mission-critical workloads get lower thresholds

### Benefit Categories

| Category | Tag | What It Captures |
|----------|-----|-----------------|
| Cost Optimization | 💰 | Reduces spend, better pricing, savings plans |
| Performance | ⚡ | Lower latency, higher throughput, capacity |
| Security & Compliance | 🔒 | New controls, compliance, encryption |
| Operational Excellence | 🔧 | Simplifies management, observability |
| Reliability | 🛡️ | Higher availability, better DR |
| Technical Debt Reduction | 🧹 | Deprecation replacements, modernization |
| Simplification | ✨ | Replaces complex workarounds |
| New Capability | 🚀 | Unlocks previously impossible patterns |

---

## Architecture

![Architecture Diagram](architecture.png)

### Pipeline Flow

```
EventBridge (daily) → RSS Lambda → DynamoDB (dedup) → Step Functions
                                                            │
                                        ┌───────────────────┤
                                        ▼                   ▼
                                 Bedrock KB Retrieve   Free-text Profile
                                 (filtered by           (from DynamoDB)
                                  workload_id)
                                        │                   │
                                        └─────────┬─────────┘
                                                  ▼
                                        Claude Sonnet 4 Scoring
                                        (relevance + category + impact)
                                                  │
                                            Score ≥ 40?
                                            /        \
                                          Yes         No → Skip
                                           │
                                           ▼
                                  Slack Notification
                                  (enriched Block Kit message)
```

### Component Details

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| **EventBridge Scheduler** | Amazon EventBridge | Triggers the pipeline once per day on a cron schedule |
| **RSS Ingestion Lambda** | AWS Lambda | Fetches AWS What's New RSS feed, deduplicates against state table, matches announcements to workload profiles by service keywords, triggers Step Functions for matched pairs |
| **Announcement State Table** | Amazon DynamoDB | Stores announcement URLs already processed (deduplication). Uses TTL to auto-delete entries after 30 days |
| **Workload Profiles Table** | Amazon DynamoDB | Stores workload profiles including workload name, key services, free-text description, account IDs, tier, and pod channel |
| **Workload Manager Lambda** | AWS Lambda | API for creating, updating, listing, and deleting workload profiles |
| **Step Functions Pipeline** | AWS Step Functions | Orchestrates the scoring and notification flow with threshold gate, retries, and error handling |
| **Relevance Scorer Lambda** | AWS Lambda | Retrieves workload context (Knowledge Base + free-text), invokes Claude Sonnet 4 to score relevance across 8 categories |
| **Bedrock Knowledge Base** | Amazon Bedrock | Stores and retrieves architecture documents with metadata filtering by workload_id. Uses OpenSearch Serverless for vector storage |
| **Amazon Bedrock (Claude)** | Amazon Bedrock | Scores announcement relevance, categorizes benefits, estimates impact, generates workload-specific explanations |
| **Slack Notification Lambda** | AWS Lambda | Formats scoring results into rich Slack Block Kit messages and delivers via webhook |
| **Secrets Manager** | AWS Secrets Manager | Securely stores the Slack webhook URL |

### How Service Matching Works

The system uses a two-stage filtering approach:

1. **Stage 1 — Cheap keyword matching (RSS Lambda):** Checks if an announcement mentions any service in a workload's `key_services` list. Eliminates ~80% of announcements with zero AI cost.

2. **Stage 2 — Expensive AI scoring (Scorer Lambda):** For matched announcements, Claude evaluates relevance using the workload's full context. Only announcements scoring ≥40 (or ≥25 for tier-0) generate notifications.

### Knowledge Base & Metadata Filtering

Documents in the Knowledge Base are tagged with `workload_id` metadata. When scoring an announcement for a specific workload, the Relevance Scorer filters retrieval to only return documents belonging to that workload — preventing cross-contamination between workloads.

```
S3 Bucket Structure:
├── dxp-001/
│   ├── architecture-overview.md
│   └── architecture-overview.md.metadata.json  ← {"metadataAttributes":{"workload_id":"dxp-001"}}
├── cc-001/
│   ├── architecture-overview.md
│   └── architecture-overview.md.metadata.json  ← {"metadataAttributes":{"workload_id":"cc-001"}}
```

---

## Project Structure

```
feature-relevance-poc/
├── README.md                          # This file
├── infrastructure.yaml                # CloudFormation template
├── architecture.png                   # Architecture diagram
├── generate-diagram.py                # Script to regenerate diagram
├── generate-doc.py                    # Script to regenerate Word doc
├── AWS_Feature_Relevance_System_Overview.docx  # Overview document
├── lambdas/
│   ├── rss-ingestion/index.py         # RSS feed polling and matching
│   ├── relevance-scorer/index.py      # Claude scoring with KB retrieval
│   ├── slack-notification/index.py    # Slack Block Kit formatting
│   └── workload-manager/index.py      # Workload profile CRUD
├── step-functions/
│   └── state-machine.json             # Step Functions ASL definition
├── sam-app/
│   └── template.yaml                 # AWS SAM template (alternative deployment)
├── sample-data/
│   ├── workload-dxp.json              # Sample workload profile
│   └── workload-creative-cloud.json   # Sample workload profile
└── kb-documents/
    ├── dxp-001/
    │   ├── architecture-overview.md
    │   └── architecture-overview.md.metadata.json
    └── cc-001/
        ├── architecture-overview.md
        └── architecture-overview.md.metadata.json
```

---

## Deployment Guide

There are two deployment options:
- **Option A: SAM (recommended)** — Automatic Lambda packaging, dependency management, simpler workflow
- **Option B: CloudFormation** — Manual Lambda code deployment, more control

### Prerequisites

- AWS CLI configured with appropriate credentials
- An AWS account with Bedrock model access enabled (Claude Sonnet 4)
- A Slack workspace with an Incoming Webhook configured
- Python 3.12 (for diagram/doc generation scripts)
- AWS SAM CLI (for Option A — [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))

### Option A: SAM Deployment (Recommended)

SAM automatically packages Lambda code with dependencies — no manual zip/upload needed.

#### Step 1: Build

```bash
cd sam-app
sam build --template template.yaml
```

#### Step 2: Deploy

```bash
sam deploy \
  --stack-name feature-relevance-poc \
  --region <YOUR_REGION> \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    "SlackWebhookUrl=https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
    "BedrockModelId=us.anthropic.claude-sonnet-4-6" \
    "KnowledgeBaseId=<YOUR_KB_ID_OR_EMPTY>" \
  --no-confirm-changeset
```

#### Step 3: Create Workload Profiles

```bash
aws lambda invoke --function-name WorkloadManager-feature-relevance-poc \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "action": "create",
    "profile": {
      "workload_id": "my-workload-001",
      "workload_name": "My Production Workload",
      "customer": "My Customer",
      "account_ids": ["123456789012"],
      "business_unit": "Engineering",
      "pod_owner": "Pod Alpha",
      "pod_slack_channel": "#my-channel",
      "workload_tier": "tier-0",
      "free_text_description": "Describe your workload architecture here — what services, what scale, what matters, what the pain points are. The richer this description, the better Claude scores relevance.",
      "key_services": ["Amazon EKS", "Amazon DynamoDB", "Amazon S3"]
    }
  }' \
  --region <YOUR_REGION> /tmp/output.json
```

**Key fields:**

| Field | Purpose |
|-------|---------|
| `workload_id` | Unique identifier (also used for KB metadata filtering) |
| `key_services` | List of AWS services — used for keyword matching against announcements |
| `free_text_description` | Rich architecture context — this is what Claude reads for deep scoring |
| `workload_tier` | `tier-0` (threshold ≥25) or `standard` (threshold ≥40) |
| `account_ids` | AWS account IDs shown in notifications |
| `pod_slack_channel` | Slack channel for notification routing |

#### Step 4: Test

```bash
aws lambda invoke --function-name RSSIngestion-feature-relevance-poc \
  --cli-binary-format raw-in-base64-out \
  --payload '{"test_mode": true}' \
  --region <YOUR_REGION> /tmp/test.json && cat /tmp/test.json
```

#### Step 5: Verify

- Check Step Functions console for execution status
- Check Slack channel for the notification
- Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/RelevanceScorer-feature-relevance-poc --follow --region <YOUR_REGION>
```

#### SAM Cleanup

```bash
sam delete --stack-name feature-relevance-poc --region <YOUR_REGION>
```

---

### Option B: CloudFormation Deployment

#### Step 1: Deploy Infrastructure

```bash
aws cloudformation deploy \
  --template-file infrastructure.yaml \
  --stack-name feature-relevance-poc \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <YOUR_REGION> \
  --parameter-overrides \
    SlackWebhookUrl="https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
    BedrockModelId="us.anthropic.claude-sonnet-4-6" \
    KnowledgeBaseId=""
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `SlackWebhookUrl` | Yes | Slack Incoming Webhook URL for notifications |
| `BedrockModelId` | No | Bedrock model ID (default: `us.anthropic.claude-sonnet-4-6`) |
| `KnowledgeBaseId` | No | Bedrock Knowledge Base ID. Leave empty to use free-text only mode |

#### Step 2: Deploy Lambda Code

The CloudFormation template creates placeholder Lambdas. Deploy the actual code:

```bash
# RSS Ingestion
cd lambdas/rss-ingestion
zip -j /tmp/rss-ingestion.zip index.py
aws lambda update-function-code \
  --function-name RSSIngestion-feature-relevance-poc \
  --zip-file fileb:///tmp/rss-ingestion.zip \
  --region <YOUR_REGION>

# Relevance Scorer
cd ../relevance-scorer
zip -j /tmp/relevance-scorer.zip index.py
aws lambda update-function-code \
  --function-name RelevanceScorer-feature-relevance-poc \
  --zip-file fileb:///tmp/relevance-scorer.zip \
  --region <YOUR_REGION>

# Slack Notification
cd ../slack-notification
zip -j /tmp/slack-notification.zip index.py
aws lambda update-function-code \
  --function-name SlackNotification-feature-relevance-poc \
  --zip-file fileb:///tmp/slack-notification.zip \
  --region <YOUR_REGION>

# Workload Manager
cd ../workload-manager
zip -j /tmp/workload-manager.zip index.py
aws lambda update-function-code \
  --function-name WorkloadManager-feature-relevance-poc \
  --zip-file fileb:///tmp/workload-manager.zip \
  --region <YOUR_REGION>
```

#### Step 3: Set Up Knowledge Base (Optional)

If you want deeper scoring using architecture documents:

1. **Create an S3 bucket** for documents:
```bash
aws s3 mb s3://your-kb-bucket-name --region <YOUR_REGION>
```

2. **Upload documents** with metadata files:
```bash
aws s3 sync kb-documents/ s3://your-kb-bucket-name/
```

Each document needs a companion `.metadata.json` file:
```json
{
  "metadataAttributes": {
    "workload_id": "your-workload-id",
    "workload_name": "Your Workload Name",
    "document_type": "architecture"
  }
}
```

3. **Create the Knowledge Base** via Bedrock console or CLI (requires OpenSearch Serverless collection for vector storage)

4. **Update the Scorer Lambda** with the Knowledge Base ID:
```bash
aws lambda update-function-configuration \
  --function-name RelevanceScorer-feature-relevance-poc \
  --environment '{"Variables":{"MODEL_ID":"us.anthropic.claude-sonnet-4-6","KNOWLEDGE_BASE_ID":"YOUR_KB_ID"}}' \
  --region <YOUR_REGION>
```

#### Step 4: Create Workload Profiles

Same as Option A Step 3.

#### Step 5: Test the Pipeline

```bash
aws lambda invoke --function-name RSSIngestion-feature-relevance-poc \
  --cli-binary-format raw-in-base64-out \
  --payload '{"test_mode": true}' \
  --region <YOUR_REGION> /tmp/test.json && cat /tmp/test.json
```

#### Step 6: Verify

- Check Step Functions console for execution status
- Check Slack channel for the notification
- Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/RelevanceScorer-feature-relevance-poc --follow --region <YOUR_REGION>
```

---

## Configuration

### Changing the Polling Frequency

The EventBridge schedule is set to `rate(1 day)`. To change:

```bash
aws events put-rule \
  --name RSSPolling-feature-relevance-poc \
  --schedule-expression 'rate(12 hours)' \
  --region <YOUR_REGION>
```

### Adjusting the Relevance Threshold

Edit the Step Functions state machine `CheckRelevanceThreshold` Choice state. Default: ≥40 for standard workloads, ≥25 for tier-0.

### Adding New Service Keywords

Edit the `SERVICE_KEYWORDS` dictionary in `lambdas/rss-ingestion/index.py` to add new service name → keyword mappings.

### Updating the Slack Webhook

```bash
aws secretsmanager put-secret-value \
  --secret-id slack-webhook-feature-relevance-poc \
  --secret-string '{"webhook_url":"https://hooks.slack.com/services/NEW/WEBHOOK/URL"}' \
  --region <YOUR_REGION>
```

---

## Slack Notification Examples
![Slack Notification Example 1](slack-notification-example-1.png)

![Slack Notification Example 2](slack-notification-example-2.png)

---
## Cost Estimate

| Scenario | Bedrock Calls/Day | Monthly Cost |
|----------|-------------------|--------------|
| 1 workload profile | ~5-8 | ~$10-$20 |
| 5 workload profiles | ~15-30 | ~$30-$60 |
| 20 workload profiles | ~50-100 | ~$100-$200 |

Bedrock (Claude) accounts for 90-95% of total cost. All other services (Lambda, DynamoDB, Step Functions, EventBridge) are under $1/month combined.

---

## Cleanup

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name feature-relevance-poc --region <YOUR_REGION>

# Delete Knowledge Base (if created)
aws bedrock-agent delete-knowledge-base --knowledge-base-id YOUR_KB_ID --region <YOUR_REGION>

# Delete S3 bucket
aws s3 rb s3://your-kb-bucket-name --force

# Delete OpenSearch Serverless collection
aws opensearchserverless delete-collection --id YOUR_COLLECTION_ID --region <YOUR_REGION>
```

---

## Model

**us.anthropic.claude-sonnet-4-6** (Amazon Bedrock inference profile).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review AWS Bedrock documentation
- Open an issue in the repository

We welcome community contributions! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## Contributing

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
