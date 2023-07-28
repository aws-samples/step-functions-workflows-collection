import boto3

session = boto3.Session()


def list_eks_clusters(credentials):
    # Retrieve the list of enabled regions
    ec2_client = session.client(
        "ec2",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    enabled_regions = [
        region["RegionName"] for region in ec2_client.describe_regions()["Regions"]
    ]
    eks_clusters = []

    for region in enabled_regions:
        try:
            eks_client = session.client(
                "eks",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=region,
            )

            response = eks_client.list_clusters()
            clusters = response["clusters"]
            for cluster in clusters:
                response = eks_client.describe_cluster(name=cluster)
                data = {
                    "name": response["cluster"]["name"],
                    "arn": response["cluster"]["arn"],
                    "platformVersion": response["cluster"]["platformVersion"],
                    "version": response["cluster"]["version"],
                }
                eks_clusters.append(data)
        except Exception as error:
            print("An error occurred:", error)
    return eks_clusters


# assume role function
def assume_role(role_arn, session_name):
    sts_client = session.client("sts")
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
    return response["Credentials"]


def handler(event, context):
    account_id = event.get("Id")
    credentials = assume_role(
        f"arn:aws:iam::{account_id}:role/OrgInventoryReader", "OrgInventory"
    )
    data = list_eks_clusters(credentials)
    return data
