import json


# This function removes the "$LATEST" version from the list of versions, sorts the remaining
# versions in descending order and determines the total number of versions.
def lambda_handler(event, context):
    versions = event.get("data", []).get("version", [])
    lambda_function_name = event.get("lambda_function_name", "Unknown")

    versions = [version for version in versions if version != "$LATEST"]
    versions_int = list(map(int, versions))

    sorted_versions = sorted(versions_int)
    count_versions = len(sorted_versions)

    response_data = {
        "lambda_function_name": lambda_function_name,
        "sorted_versions": sorted_versions,
        "count": count_versions,
    }

    return {
        "statusCode": 200,
        "body": json.dumps(response_data),
        "headers": {"Content-Type": "application/json"},
    }
