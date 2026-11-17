# Architecture — AWS Feature Relevance Notification System

## Overview

This system transforms the high-volume AWS "What's New" feed (200+ announcements/month) into curated, workload-specific recommendations delivered via Slack. It uses a two-stage filtering approach — cheap keyword matching followed by expensive AI scoring — to minimize Bedrock costs while maximizing signal quality.

---

## Architecture Diagram

![Architecture Diagram](architecture.png)

---

## High-Level Flow

```
┌──────────────────┐       ┌───────────────────────┐       ┌──────────────────────┐
│  EventBridge     │──────▶│  RSS Ingestion Lambda │──────▶│  DynamoDB            │
│  (every 10 min)  │       │  - Fetch RSS feed     │       │  - Deduplication     │
└──────────────────┘       │  - Keyword matching   │       │  - Workload profiles │
                           └───────────┬───────────┘       └──────────────────────┘
                                       │
                         (per matched workload)
                                       ▼
                           ┌───────────────────────┐
                           │  Step Functions        │
                           │  Scoring Pipeline      │
                           └───────────┬───────────┘
                                       │
                                       ▼
                           ┌───────────────────────┐       ┌──────────────────────┐
                           │  Relevance Scorer     │──────▶│  Amazon Bedrock      │
                           │  Lambda               │       │  - KB Retrieve       │
                           │                       │◀──────│  - Claude Sonnet 4   │
                           └───────────┬───────────┘       └──────────────────────┘
                                       │
                                 Score ≥ threshold?
                                  /            \
                                Yes             No → End
                                 │
                                 ▼
                           ┌───────────────────────┐       ┌──────────────────────┐
                           │  Slack Notification   │──────▶│  Slack Webhook       │
                           │  Lambda               │       │  (Block Kit message) │
                           └───────────────────────┘       └──────────────────────┘
```

---

## Component Architecture

### 1. Event Trigger — Amazon EventBridge

- **Schedule**: `rate(10 minutes)` (configurable)
- **Target**: RSS Ingestion Lambda
- **Purpose**: Provides serverless cron-style triggering without infrastructure

### 2. RSS Ingestion Lambda

**Responsibility**: Fetch, deduplicate, match, and fan out announcements.

| Step | Action |
|------|--------|
| 1 | Fetch `https://aws.amazon.com/about-aws/whats-new/recent/feed/` |
| 2 | Parse XML items (title, link, description, categories, pub_date) |
| 3 | Check DynamoDB state table for deduplication |
| 4 | Match announcement text against each workload profile's `key_services` using keyword lookup |
| 5 | Start a Step Functions execution for each (announcement, workload) pair |

**Key design decisions**:
- Uses `defusedxml` for safe XML parsing
- Keyword matching is case-insensitive and checks title + description + categories
- One Step Functions execution per (announcement × workload) match enables parallel scoring
- Test mode supports injecting a synthetic announcement for demos

### 3. DynamoDB Tables

| Table | Key | Purpose | Features |
|-------|-----|---------|----------|
| **AnnouncementState** | `announcement_url` (S) | Deduplication — tracks processed URLs | TTL (30 days), KMS encryption, PITR |
| **WorkloadProfiles** | `workload_id` (S) | Stores workload definitions | KMS encryption, PITR, PAY_PER_REQUEST |

### 4. Step Functions State Machine

Orchestrates the scoring and notification pipeline with built-in error handling.

```
ScoreRelevance → CheckRelevanceThreshold → PrepareNotification → SendSlackNotification
                        │                                                   
                        └─── BelowThreshold (skip)
                        
ScoreRelevance ──(error)──▶ ScoringFailed
```

**Threshold logic**:
- Tier-0 workloads: score ≥ 25 (lower bar for mission-critical systems)
- Standard workloads: score ≥ 40

**Retry configuration**:
- Scoring: 3 retries, 5s interval, 2x backoff
- Notification: 2 retries, 2s interval, 2x backoff

### 5. Relevance Scorer Lambda

**Responsibility**: Build context, invoke Claude, return structured scoring.

**Scoring flow**:
1. Retrieve architecture context from Bedrock Knowledge Base (filtered by `workload_id` metadata)
2. Combine KB context with the workload's `free_text_description` from DynamoDB
3. Invoke Claude Sonnet 4 with a structured prompt
4. Parse JSON response into scoring result

**Scoring dimensions** (8 categories):
- Cost Optimization
- Performance
- Security & Compliance
- Operational Excellence
- Reliability
- Technical Debt Reduction
- Simplification
- New Capability

**Output structure**:
```json
{
  "relevance_score": 0-100,
  "primary_category": "...",
  "secondary_categories": [],
  "impact_summary": { "what_changes", "magnitude", "effort_to_adopt", "urgency" },
  "benefit_explanation": "...",
  "adoption_recommendation": "immediate|evaluate|monitor|skip",
  "risk_of_not_adopting": "...",
  "estimated_impact": { "direction", "description" }
}
```

### 6. Bedrock Knowledge Base (Optional)

- **Vector store**: Amazon OpenSearch Serverless
- **Documents**: Architecture overviews per workload, stored in S3
- **Metadata filtering**: Each document tagged with `workload_id` to ensure isolation
- **Retrieval**: Top 3 chunks per query, filtered to requesting workload only

### 7. Slack Notification Lambda

- Formats scoring results into rich **Slack Block Kit** messages
- Retrieves webhook URL from **AWS Secrets Manager**
- Includes: category tag, tier badge, benefit explanation, impact, effort, risk warning
- Validates HTTPS scheme on webhook URL before sending

### 8. Workload Manager Lambda

CRUD API for workload profiles. Supports:
- `create` — Register a new workload
- `update` — Modify profile fields
- `list` — Return all profiles
- `delete` — Remove a workload

---

## Security Architecture

| Concern | Implementation |
|---------|---------------|
| **Encryption at rest** | KMS Customer Managed Key (CMK) shared across DynamoDB, SQS, and Secrets Manager |
| **Key rotation** | Automatic annual rotation enabled |
| **Secrets** | Slack webhook stored in Secrets Manager, never in environment variables |
| **Least privilege** | Lambda role scoped to specific table ARNs, model ARNs, and secret ARNs |
| **Dead letter queue** | SQS DLQ captures failed Lambda invocations (14-day retention) |
| **XML parsing** | `defusedxml` library prevents XXE attacks |
| **URL validation** | HTTPS scheme enforced before outbound HTTP calls |
| **Concurrency limits** | Reserved concurrency on all Lambdas prevents runaway scaling |

---

## Data Flow

```
AWS What's New RSS ──▶ RSS Lambda ──▶ DynamoDB (state)
                                │
                                ├──▶ DynamoDB (profiles) ◀── Workload Manager Lambda
                                │
                                ▼
                         Step Functions
                                │
                                ▼
               Bedrock KB ──▶ Scorer Lambda ──▶ Bedrock Claude
                                │
                                ▼
               Secrets Mgr ──▶ Slack Lambda ──▶ Slack Webhook
```

---

## Cost Architecture

The system is designed for minimal cost at low-to-moderate volume:

| Component | Pricing Model | Expected Cost |
|-----------|---------------|---------------|
| EventBridge | Free tier (14M invocations/month) | $0 |
| Lambda (4 functions) | Pay-per-invocation, ~5-100 calls/day | < $1/month |
| DynamoDB (2 tables) | PAY_PER_REQUEST, minimal reads/writes | < $1/month |
| Step Functions | Standard workflow, ~5-100 executions/day | < $1/month |
| Bedrock (Claude Sonnet 4) | Per-token pricing, ~5-100 calls/day | $10-$200/month |
| Knowledge Base + OpenSearch | Serverless OCU hours | ~$5-$20/month |
| Secrets Manager | 1 secret, occasional reads | < $1/month |
| KMS | 1 key + API calls | < $5/month |

**Bedrock accounts for 90-95% of total cost.** The two-stage filtering (keyword → AI) ensures only matched announcements consume Bedrock tokens.

---

## Scalability Considerations

- **Fan-out pattern**: One Step Functions execution per (announcement × workload) allows parallel processing
- **Reserved concurrency**: Prevents excessive parallel Bedrock calls (scorer limited to 10 concurrent)
- **DynamoDB on-demand**: Auto-scales with no capacity planning
- **TTL on state table**: Self-cleaning deduplication (30-day retention)
- **Stateless Lambdas**: Horizontally scalable by default

---

## Deployment Options

| Option | Tool | Packaging | Best For |
|--------|------|-----------|----------|
| **A (recommended)** | AWS SAM | Automatic Lambda packaging with dependencies | Quick setup, dependency management |
| **B** | CloudFormation | Manual zip/upload of Lambda code | Full control, existing CF workflows |

Both options deploy identical infrastructure. SAM adds automatic `defusedxml` dependency packaging for the RSS Lambda.

---

## Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI model | Claude Sonnet 4 (Bedrock) | Best balance of quality/cost for structured JSON scoring |
| Orchestration | Step Functions | Built-in retries, error handling, threshold gating |
| Notification | Slack Block Kit | Rich formatting, enterprise adoption |
| Secret storage | Secrets Manager | Rotation support, KMS integration |
| XML parsing | defusedxml | Prevents XXE and entity expansion attacks |
| Infrastructure | CloudFormation/SAM | Native AWS, no external dependencies |
| DynamoDB billing | PAY_PER_REQUEST | Unpredictable low-volume traffic pattern |
