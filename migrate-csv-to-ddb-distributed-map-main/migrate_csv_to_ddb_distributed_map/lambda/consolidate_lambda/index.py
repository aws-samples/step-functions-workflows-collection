import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import os

ddb_table_name = os.environ["DESTINATION_TABLE_NAME"]
s3_bucket = os.environ["S3_BUCKET"]


class ConsolidationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def handler(event, context):
    try:
        report = event["report"]
        execution_name = event["execution_name"]
        items_written = 0
        items_in_error = 0

        for item in report:
            if "NUMBER_OF_ITEMS_WRITTEN" in item and "NUMBER_OF_ITEMS_IN_ERROR" in item:
                items_written += item["NUMBER_OF_ITEMS_WRITTEN"]
                items_in_error += item["NUMBER_OF_ITEMS_IN_ERROR"]

        migration_result = {
            "TOTAL_NUMBER_OF_ITEMS_WRITTEN": items_written,
            "TOTAL_NUMBER_OF_ITEMS_IN_ERROR": items_in_error,
            "DESTINATION_TABLE_NAME": ddb_table_name,
        }
        if items_in_error > 0:
            migration_result[
                "ERROR_DATA_LOCATION"
            ] = f"s3://{s3_bucket}/migration_errors/execution_name={execution_name}"

        return migration_result
    except Exception as e:
        logger.error(e)
        raise ConsolidationError("Consolidation process failed.")
