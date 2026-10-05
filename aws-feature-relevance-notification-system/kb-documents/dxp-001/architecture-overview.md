# Digital Experience Platform - Architecture Overview

## System Purpose
Real-time customer data platform processing 2M events/sec for personalization and analytics across 50+ global properties.

## Compute Layer
- Amazon EKS cluster with 340 Graviton3 (m7g.4xlarge) nodes across 3 Availability Zones
- Currently running Kubernetes 1.29
- Custom Horizontal Pod Autoscaler based on Kinesis shard iterator age
- Considering migration to Fargate for batch processing workloads
- 12 custom ARM64 container images built and stored in Amazon ECR

## Data Storage
- Amazon DynamoDB for hot customer profile storage: 500K RCU peak, single-digit millisecond reads
- DynamoDB Global Tables for multi-region replication (us-west-2 primary, eu-west-1 secondary)
- Amazon S3 data lake: 2PB total, Apache Iceberg table format, Parquet files
- S3 Intelligent-Tiering for cold data cost optimization

## Event Streaming
- Amazon Kinesis Data Streams: 200 shards for event ingestion
- Peak throughput: 2M events/sec during Black Friday / holiday events
- Consumer applications use Enhanced Fan-Out for dedicated throughput
- Kinesis Data Firehose for S3 data lake loading

## Content Delivery
- Amazon CloudFront with 50+ Points of Presence
- Custom domain with ACM certificates
- Origin failover configured for high availability
- Lambda@Edge for A/B testing and personalization at the edge

## Networking
- AWS Transit Gateway connecting 12 VPCs across the workload
- AWS PrivateLink for all cross-VPC service communication
- VPC endpoints for all AWS service data plane traffic (S3, DynamoDB, ECR, KMS)
- No public internet egress for data plane — all traffic stays on AWS backbone

## Security
- AWS KMS customer-managed keys for encryption at rest (all services)
- TLS 1.3 enforced for all data in transit
- IAM roles with least-privilege policies, no long-lived credentials
- AWS PrivateLink eliminates exposure to public internet
- Compliance: SOC2, GDPR, HIPAA-eligible

## Performance Requirements
- p99 latency < 50ms for customer profile lookups
- p99 latency < 100ms for event ingestion acknowledgment
- 99.99% availability target (tier-0 workload)

## Cost Profile
- Total monthly spend: ~$750K
- Largest cost drivers: EKS compute ($320K), DynamoDB ($180K), S3 ($95K)
- Reserved Instances and Savings Plans cover ~60% of compute
- Cost-sensitive: leadership reviews spend monthly

## Known Pain Points
- EKS version upgrades require 2-week planning cycle due to custom admission controllers
- DynamoDB costs spike 3x during seasonal events (Black Friday, holiday season)
- Cross-region replication latency to eu-west-1 occasionally exceeds 500ms, affecting APAC users routed through Europe
- Graviton migration from x86 is 70% complete — remaining 30% blocked by third-party container dependencies
