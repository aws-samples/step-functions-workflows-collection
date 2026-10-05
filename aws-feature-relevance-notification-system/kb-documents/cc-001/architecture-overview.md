# Creative Cloud Asset Storage - Architecture Overview

## System Purpose
Global asset storage and rendering pipeline serving 30M+ Creative Cloud subscribers. Handles upload, storage, sync, and rendering of creative assets (PSD, AI, video files) across desktop and mobile clients.

## Compute Layer
- AWS Lambda for image processing: thumbnail generation, format conversion, metadata extraction
- 10K peak concurrent Lambda executions, ARM64 (Graviton) runtime
- AWS Step Functions for video transcoding orchestration (multi-step pipeline)
- AWS Elemental MediaConvert for video processing (4K, HDR support)

## Data Storage
- Amazon S3 primary object storage: 50PB+ total capacity across multiple regions
- S3 Intelligent-Tiering for automatic cost optimization on infrequently accessed assets
- S3 Cross-Region Replication to us-east-1 and eu-west-1 for disaster recovery
- Amazon Aurora PostgreSQL for metadata catalog (asset relationships, user permissions, version history)
- Aurora read replicas in 3 regions for low-latency metadata queries

## Content Delivery
- Amazon CloudFront with 100+ Points of Presence for global asset delivery
- Custom domain with dedicated IP (BYOIP) for enterprise clients
- CloudFront Functions for URL signing and access control at the edge
- Origin Shield enabled for cache efficiency

## Messaging & Queuing
- Amazon SQS for processing queue (decouples upload from processing)
- Dead Letter Queue for failed processing retries
- Amazon SNS for user notifications (processing complete, sharing events)

## Networking
- Multi-region deployment: us-west-2 (primary), us-east-1, eu-west-1
- AWS Global Accelerator for upload acceleration from global clients
- VPC endpoints for S3 and Lambda to avoid NAT Gateway costs

## Security
- Customer-managed AWS KMS keys for all asset encryption at rest
- Per-tenant encryption key isolation for enterprise customers
- S3 Object Lock for compliance retention (legal hold)
- VPC endpoints eliminate public internet exposure for data plane

## Performance Requirements
- Upload acknowledgment < 2 seconds for files up to 5GB
- Thumbnail generation < 10 seconds for images up to 100MB
- Video transcoding SLA: 2x realtime for 1080p, 1x realtime for 4K
- Global read latency p95 < 200ms via CloudFront

## Cost Profile
- Total monthly spend: ~$1.2M
- Largest cost drivers: S3 storage ($520K), CloudFront ($280K), Lambda ($145K)
- S3 costs growing 20% YoY with subscriber growth
- Intelligent-Tiering saves ~$80K/month vs. Standard tier

## Known Pain Points
- S3 costs growing 20% year-over-year as subscriber base expands
- Lambda cold starts (500ms+) affect thumbnail generation latency for first-request-after-idle
- Aurora writer instance hit max capacity during upload spikes (Monday mornings, product launches)
- Cross-region replication costs for DR are significant (~$40K/month in transfer fees)
- Video transcoding queue depth exceeds 10K during major product launches, causing SLA misses
