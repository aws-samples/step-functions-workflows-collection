import boto3
import urllib.parse

sfn = boto3.client("stepfunctions")


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    token = urllib.parse.unquote(params.get("token", ""))
    action = params.get("action", "")

    if not token or action not in ("approve", "reject"):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "text/html"},
            "body": "<h2>Invalid request.</h2>",
        }

    try:
        if action == "approve":
            sfn.send_task_success(taskToken=token, output="{}")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": "<h1>&#9989; Report Approved</h1><p>The report has been approved and recorded.</p>",
            }
        else:
            sfn.send_task_failure(
                taskToken=token,
                error="Rejected",
                cause="Report not approved by reviewer",
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": "<h1>&#10060; Report Rejected</h1><p>The report has been rejected.</p>",
            }
    except Exception as e:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": f"<h2>Action already completed or token expired.</h2><p>{str(e)}</p>",
        }
