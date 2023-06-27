import utils
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Migration:
    def __init__(self, table, pk):
        self.table = table
        self.pk = pk

    # Write to DDB (only if STAGE 1 AND 2 SUCCEED

    def start(self, items):
        with self.table.batch_writer(overwrite_by_pkeys=[self.pk]) as batch:
            [batch.put_item(Item=item) for item in items]
