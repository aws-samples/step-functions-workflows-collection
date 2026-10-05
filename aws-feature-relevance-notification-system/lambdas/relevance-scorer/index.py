"""
Relevance Scorer Lambda
Called by Step Functions. Retrieves workload context and invokes
Claude to score announcement relevance across 8 benefit categories.
"""
import boto3
import json
import os

bedrock = boto3.client('bedrock-runtime', region_name='<YOUR_REGION>')
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='<YOUR_REGION>')

MODEL_ID = os.environ.get('MODEL_ID', 'us.anthropic.claude-sonnet-4-6')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')

SCORING_PROMPT = """You are an AWS Solutions Architect analyzing AWS feature announcements for enterprise customers. Your job is to score the relevance of a new AWS announcement against a specific customer workload.

<announcement>
Title: {title}
Description: {description}
Service Category: {categories}
Link: {link}
</announcement>

<workload_profile>
Workload: {workload_name}
Description: {free_text_description}
Key Services: {key_services}
Workload Tier: {workload_tier}
</workload_profile>

{kb_context}

Score the relevance of this announcement to the customer's workload. Consider ALL dimensions of value, not just cost.

Respond ONLY with valid JSON (no markdown fencing):
{{
  "relevance_score": <0-100 integer>,
  "primary_category": "<one of: cost_optimization, performance, security_compliance, operational_excellence, reliability, technical_debt_reduction, simplification, new_capability>",
  "secondary_categories": ["<optional additional categories>"],
  "impact_summary": {{
    "what_changes": "<one sentence: what specifically improves for this workload>",
    "magnitude": "<high|medium|low>",
    "effort_to_adopt": "<drop-in|configuration-change|migration-required|redesign-needed>",
    "urgency": "<immediate|next-quarter|when-convenient|monitor-only>"
  }},
  "benefit_explanation": "<2-3 sentences explaining why this feature matters for THIS specific workload, referencing their architecture and pain points>",
  "adoption_recommendation": "<immediate|evaluate|monitor|skip>",
  "risk_of_not_adopting": "<one sentence: what happens if they ignore this, or null if no risk>",
  "estimated_impact": {{
    "direction": "<positive|neutral|negative>",
    "description": "<quantified impact if possible, e.g. '~$12K/month savings' or '30% latency reduction' or 'eliminates 2K lines of custom code'>"
  }}
}}"""


def lambda_handler(event, context):
    """Score an announcement against a workload profile."""
    announcement = event['announcement']
    workload = event['workload']

    print(f"Scoring: '{announcement['title'][:60]}...' against '{workload['workload_name']}'")

    # Retrieve additional context from Knowledge Base (if configured)
    kb_context = ""
    if KNOWLEDGE_BASE_ID:
        kb_context = retrieve_kb_context(
            announcement['title'] + " " + announcement.get('description', ''),
            workload.get('workload_id', '')
        )

    # Build the scoring prompt
    prompt = SCORING_PROMPT.format(
        title=announcement['title'],
        description=announcement.get('description', 'No description available'),
        categories=', '.join(announcement.get('categories', [])),
        link=announcement.get('link', ''),
        workload_name=workload.get('workload_name', 'Unknown'),
        free_text_description=workload.get('free_text_description', 'No description provided'),
        key_services=', '.join(workload.get('key_services', [])),
        workload_tier=workload.get('workload_tier', 'standard'),
        kb_context=f"<additional_context>\n{kb_context}\n</additional_context>" if kb_context else ""
    )

    # Invoke Claude
    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 2048,
                'temperature': 0.3,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        result_text = response_body['content'][0]['text']

        # Parse the JSON response
        scoring_result = json.loads(result_text)
        scoring_result['model_used'] = MODEL_ID
        scoring_result['workload_id'] = workload.get('workload_id', '')
        scoring_result['workload_name'] = workload.get('workload_name', '')
        scoring_result['pod_slack_channel'] = workload.get('pod_slack_channel', '#aws-notifications')
        scoring_result['workload_tier'] = workload.get('workload_tier', 'standard')
        scoring_result['account_ids'] = workload.get('account_ids', [])

        print(f"Score: {scoring_result['relevance_score']}, Category: {scoring_result['primary_category']}")
        return scoring_result

    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Claude response as JSON: {e}")
        print(f"Raw response: {result_text[:500]}")
        return {
            'relevance_score': 0,
            'primary_category': 'unknown',
            'error': f'JSON parse error: {str(e)}',
            'raw_response': result_text[:200]
        }
    except Exception as e:
        print(f"ERROR invoking Bedrock: {e}")
        return {
            'relevance_score': 0,
            'primary_category': 'unknown',
            'error': str(e)
        }


def retrieve_kb_context(query, workload_id):
    """Retrieve relevant context from Bedrock Knowledge Base, filtered by workload_id."""
    if not KNOWLEDGE_BASE_ID:
        return ""

    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3,
                    'filter': {
                        'equals': {
                            'key': 'workload_id',
                            'value': workload_id
                        }
                    }
                }
            }
        )

        chunks = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            if content:
                chunks.append(content)

        return '\n---\n'.join(chunks) if chunks else ""

    except Exception as e:
        print(f"WARNING: KB retrieval failed: {e}")
        return ""
