import boto3

vod = boto3.client('mediapackage-vod')
def on_event(event, context):
  physical_id = context.log_stream_name

  request_type = event['RequestType']
  if request_type == 'Create': return {'PhysicalResourceId': physical_id}
  if request_type == 'Update': return {'PhysicalResourceId': physical_id} 
  if request_type == 'Delete': 
    return on_delete(event,physical_id)
  
  raise Exception("Invalid request type: %s" % request_type)


def on_delete(event,physical_id):
  physical_id = event["PhysicalResourceId"]
  props = event["ResourceProperties"]
  packing_group_id = props['PackagingGroupId']
  remove_asset(packing_group_id)
  return {'PhysicalResourceId': physical_id}

  
def remove_asset(packaging_group_id: str):
  try: 
    response = vod.list_assets(PackagingGroupId=packaging_group_id)
    assets = response["Assets"]
    for asset in assets: 
      asset_id = asset["Id"]
      try: 
        vod.delete_asset(Id=asset_id)
        print("asset deleting:",asset_id )

      except Exception as error:
        print("failed to remove asset{0} with Exception: {1}".format(asset_id, error))

  except Exception as error:
    print("Failed to retrive asset", error)
    