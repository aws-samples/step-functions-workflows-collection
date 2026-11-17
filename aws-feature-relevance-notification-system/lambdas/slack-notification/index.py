"""
Slack Notification Lambda
Formats scoring results into rich Slack Block Kit messages and
delivers them to the appropriate pod channel via webhook.
"""
import boto3
import json
import os
import urllib.request
import urllib.parse

secrets_client = boto3.client('secretsmanager')

SECRET_ARN = os.environ.get('SLACK_SECRET_ARN', '')

CATEGORY_TAGS = {
    'cost_optimization': '💰 Cost Optimization',
    'performance': '⚡ Performance',
    'security_compliance': '🔒 Security & Compliance',
    'operational_excellence': '🔧 Operational Excellence',
    'reliability': '🛡️ Reliability',
    'technical_debt_reduction': '🧹 Technical Debt Reduction',
    'simplification': '✨ Simplification',
    'new_capability': '🚀 New Capability'
}

URGENCY_EMOJI = {
    'immediate': '🚨',
    'next-quarter': '📅',
    'when-convenient': '📋',
    'monitor-only': '👀'
}

RECOMMENDATION_TEXT = {
    'immediate': 'Adopt immediately — high-impact, low-effort',
    'evaluate': 'Evaluate — schedule POC within 2 weeks',
    'monitor': 'Monitor — track for future adoption window',
    'skip': 'Skip — low relevance for current architecture'
}


def lambda_handler(event, context):
    """Format and send Slack notification."""
    scoring = event.get('scoring', {})
    announcement = event.get('announcement', {})

    # Get webhook URL from Secrets Manager
    webhook_url = get_webhook_url()
    if not webhook_url:
        return {'statusCode': 500, 'error': 'No Slack webhook URL configured'}

    # Build the Slack message
    slack_payload = build_slack_message(scoring, announcement)

    # Send to Slack
    try:
        # Validate webhook URL scheme
        parsed_url = urllib.parse.urlparse(webhook_url)
        if parsed_url.scheme != 'https':
            print(f"ERROR: Invalid webhook URL scheme: {parsed_url.scheme}")
            return {'statusCode': 400, 'error': 'Webhook URL must use HTTPS'}
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(slack_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(req, timeout=10)  # nosec B310
        print(f"Slack notification sent: {response.status}")
        return {'statusCode': 200, 'message': 'Notification sent'}
    except Exception as e:
        print(f"ERROR sending Slack notification: {e}")
        return {'statusCode': 500, 'error': str(e)}


def build_slack_message(scoring, announcement):
    """Build a rich Slack Block Kit message from scoring results."""
    category = scoring.get('primary_category', 'unknown')
    tag = CATEGORY_TAGS.get(category, '📢 AWS Update')
    workload_name = scoring.get('workload_name', 'Unknown Workload')
    workload_tier = scoring.get('workload_tier', 'standard')

    # Header line (category + tier badge, no score)
    tier_badge = ' 🔴 TIER-0' if workload_tier == 'tier-0' else ''
    header = f"{tag}{tier_badge}"

    # Impact section
    impact = scoring.get('estimated_impact', {})
    impact_text = impact.get('description', 'Impact assessment pending')

    # Effort
    effort = scoring.get('impact_summary', {}).get('effort_to_adopt', 'TBD')

    # Account IDs (support multiple)
    account_ids = scoring.get('account_ids', [])
    if not account_ids:
        # Try to get from workload profile
        account_id = scoring.get('account_id', '')
        if account_id:
            account_ids = [account_id] if isinstance(account_id, str) else account_id
    account_ids_str = ', '.join(account_ids) if account_ids else 'N/A'

    # Format announcement date
    pub_date_raw = announcement.get('pub_date', '')
    release_date = format_date(pub_date_raw)

    # Build workload line
    workload_line = f"*Workload:* {workload_name} | *Account ID:* {account_ids_str}"

    # Build blocks
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header[:150], "emoji": True}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{announcement.get('link', '#')}|{announcement.get('title', 'AWS Announcement')}>*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Release Date:* {release_date}\n"
                    f"{workload_line}\n\n"
                    f"*Why this matters:*\n{scoring.get('benefit_explanation', 'No explanation available')}"
                )
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Impact:*\n{impact_text}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Effort:*\n{effort}"
            }
        }
    ]

    # Add risk warning if present
    risk = scoring.get('risk_of_not_adopting')
    if risk and risk != 'null' and risk.lower() != 'none':
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"⚠️ *Risk of inaction:* {risk}"}
        })

    # Secondary categories
    secondary = scoring.get('secondary_categories', [])
    if secondary:
        secondary_tags = ', '.join([CATEGORY_TAGS.get(c, c) for c in secondary])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Also relevant to: {secondary_tags}"}]
        })

    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn",
            "text": f"📊 AWS Feature Relevance System | Model: Claude Sonnet 4"}]
    })

    return {
        "blocks": blocks,
        "text": f"{tag} | {announcement.get('title', 'AWS Announcement')}"
    }


def get_webhook_url():
    """Retrieve Slack webhook URL from Secrets Manager."""
    if not SECRET_ARN:
        return os.environ.get('SLACK_WEBHOOK_URL', '')

    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        secret = json.loads(response['SecretString'])
        return secret.get('webhook_url', '')
    except Exception as e:
        print(f"ERROR retrieving webhook URL: {e}")
        return ''


def format_date(date_str):
    """Parse RSS date string and return dd/mm/yyyy format."""
    from datetime import datetime
    if not date_str:
        return 'N/A'
    try:
        # RSS dates are like: "Mon, 21 Jul 2026 08:00:00 GMT"
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        return dt.strftime('%d/%m/%Y')
    except Exception:
        try:
            # Try ISO format fallback
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return date_str[:10] if len(date_str) >= 10 else date_str
