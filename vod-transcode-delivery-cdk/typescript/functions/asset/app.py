import json
import boto3
import os

vod = boto3.client("mediapackage-vod")
sourcePaths = []
egress_endpoint = []
cdn_endpoints = []
asset_creation_status = "SUCCEED"
status_reason = "asset create success"
package_group_id = os.environ["GROUP_ID"]
source_arn = os.environ["SOURCE_ROLE_ARN"]
package_group_domain = os.environ["PACKAGE_GROUP_DOMAIN"] 
#https://d42fc57f657a3c587833a9425b507c62.egress.mediapackage-vod.us-east-1.amazonaws.com
distribution_domain = os.environ["DISTRIBUTION_DOMAIN"] 
#d111111abcdef8.cloudfront.net

def lambda_handler(event, context):
    for output_group in event["detail"]["outputGroupDetails"]:
        sourcePaths = output_group["playlistFilePaths"]
        for path in sourcePaths:
            try:
                media_package_asset = vod.create_asset(
                    Id=event["detail"]["jobId"],
                    PackagingGroupId=package_group_id,
                    SourceArn=path.replace("s3://", "arn:aws:s3:::"),
                    SourceRoleArn=source_arn,
                )

                print(media_package_asset)
                egress_endpoints = media_package_asset["EgressEndpoints"]
                egress = {
                    "egress_endpoints": egress_endpoints
                }
                endpoint_url = str()
                for endpoint in egress_endpoints: 
                    endpoint_url = endpoint["Url"].replace(package_group_domain.split("//")[1],distribution_domain)
                    cdn_endpoints.append(endpoint_url)

                asset_creation_status = "SUCCEED"
                status_reason = "asset create success"
                return {
                    "egress": egress, 
                    "asset_status": asset_creation_status,
                    "status_reason": status_reason, 
                    "endpoint": cdn_endpoints
                    }
            
            except Exception as error:
                asset_creation_status = "FAILED"
                status_reason = str(error)
                error_message = {
                    "asset_status": asset_creation_status,
                    "status_reason": status_reason, 
                    }
                return error_message
