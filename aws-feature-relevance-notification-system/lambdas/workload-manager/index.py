"""
Workload Manager Lambda
API for creating, updating, and listing workload profiles.
Supports both structured (key_services) and free-text descriptions.
"""
import boto3
import json
import os
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
PROFILES_TABLE = os.environ.get('PROFILES_TABLE', 'WorkloadProfiles')


def lambda_handler(event, context):
    """Handle workload profile CRUD operations."""
    table = dynamodb.Table(PROFILES_TABLE)
    action = event.get('action', 'list')

    if action == 'create':
        return create_profile(table, event.get('profile', {}))
    elif action == 'update':
        return update_profile(table, event.get('profile', {}))
    elif action == 'get':
        return get_profile(table, event.get('workload_id', ''))
    elif action == 'list':
        return list_profiles(table)
    elif action == 'delete':
        return delete_profile(table, event.get('workload_id', ''))
    else:
        return {'statusCode': 400, 'error': f'Unknown action: {action}'}


def create_profile(table, profile):
    """Create a new workload profile."""
    required_fields = ['workload_id', 'workload_name']
    for field in required_fields:
        if field not in profile:
            return {'statusCode': 400, 'error': f'Missing required field: {field}'}

    # Ensure key_services is a list stored as JSON string for DynamoDB
    if 'key_services' in profile and isinstance(profile['key_services'], list):
        profile['key_services'] = profile['key_services']  # DynamoDB handles lists natively

    profile['created_at'] = datetime.now(timezone.utc).isoformat()
    profile['updated_at'] = datetime.now(timezone.utc).isoformat()

    table.put_item(Item=profile)
    print(f"Created profile: {profile['workload_id']} - {profile['workload_name']}")

    return {
        'statusCode': 201,
        'message': f"Profile created: {profile['workload_name']}",
        'workload_id': profile['workload_id']
    }


def update_profile(table, profile):
    """Update an existing workload profile."""
    if 'workload_id' not in profile:
        return {'statusCode': 400, 'error': 'Missing workload_id'}

    profile['updated_at'] = datetime.now(timezone.utc).isoformat()
    table.put_item(Item=profile)

    return {
        'statusCode': 200,
        'message': f"Profile updated: {profile.get('workload_name', profile['workload_id'])}"
    }


def get_profile(table, workload_id):
    """Get a single workload profile."""
    if not workload_id:
        return {'statusCode': 400, 'error': 'Missing workload_id'}

    response = table.get_item(Key={'workload_id': workload_id})
    if 'Item' not in response:
        return {'statusCode': 404, 'error': f'Profile not found: {workload_id}'}

    return {'statusCode': 200, 'profile': response['Item']}


def list_profiles(table):
    """List all workload profiles."""
    response = table.scan()
    profiles = response.get('Items', [])

    # Return summary view
    summaries = []
    for p in profiles:
        summaries.append({
            'workload_id': p['workload_id'],
            'workload_name': p.get('workload_name', ''),
            'customer': p.get('customer', ''),
            'workload_tier': p.get('workload_tier', 'standard'),
            'key_services_count': len(p.get('key_services', [])),
            'pod_slack_channel': p.get('pod_slack_channel', '')
        })

    return {'statusCode': 200, 'profiles': summaries, 'count': len(summaries)}


def delete_profile(table, workload_id):
    """Delete a workload profile."""
    if not workload_id:
        return {'statusCode': 400, 'error': 'Missing workload_id'}

    table.delete_item(Key={'workload_id': workload_id})
    return {'statusCode': 200, 'message': f'Profile deleted: {workload_id}'}
