import logging
import os
import utils
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

destination_table_name = os.environ["DESTINATION_TABLE_NAME"]
DDB_RETRIES = os.environ["DDB_RETRIES"]

from botocore.client import Config

config = Config(retries=dict(max_attempts=int(DDB_RETRIES)))
dynamodb = boto3.resource("dynamodb", config=config)

table = dynamodb.Table(destination_table_name)

from migration import Migration

DDB_BATCH_SIZE = 100
TABLE_PK_NAME = "dol_vehicle_id"
KEY_VALIDATION_NAME = "DOL Vehicle ID"

import handle_error_data


class MigrationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def handler(event, context):
    """
    :param event:
    {
      "Items": [
        {
          "Vehicle Location": "POINT (-122.20563 47.76144)",
          "Postal Code": "98011",
          "Make": "TESLA",
          "City": "Bothell",
          "County": "King",
          "Electric Vehicle Type": "Battery Electric Vehicle (BEV)",
          "Base MSRP": "0",
          "Model Year": "2021",
          "State": "WA",
          "VIN (1-10)": "5YJYGDEE7M",
          "Electric Utility": "PUGET SOUND ENERGY INC||CITY OF TACOMA - (WA)",
          "Model": "MODEL Y",
          "Legislative District": "1",
          "Electric Range": "0",
          "DOL Vehicle ID": "138583672",
          "2020 Census Tract": "53033021804",
          "Clean Alternative Fuel Vehicle (CAFV) Eligibility": "Eligibility unknown as battery range has not been researched"
        },
    ]
    :param context:
    :return:
    """
    try:
        execution_name = event["BatchInput"]["execution_name"]
        items = event["Items"]
        clean_list, bad_items_list = utils.validate_and_transform_items(
            items=items, validation_key_name=KEY_VALIDATION_NAME
        )
        if len(clean_list) > 0:
            migration = Migration(table=table, pk=TABLE_PK_NAME)
            migration.start(clean_list)

        handle_error_data.send(items=bad_items_list, execution_name=execution_name)

        return {
            "NUMBER_OF_ITEMS_WRITTEN": len(clean_list),
            "NUMBER_OF_ITEMS_IN_ERROR": len(bad_items_list),
        }

    except Exception as e:
        logger.error(e)
        raise MigrationError("Process failed.")
