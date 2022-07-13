import os
import hashlib
import json
import jmespath
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger

IDEMPOTENCY_RECORD_TTL_MINUTES = int(
    os.getenv("IDEMPOTENCY_RECORD_TTL_MINUTES", "1440")
)
IDEMPOTENCY_JMESPATH_ATTRIBUTE = os.getenv(
    "IDEMPOTENCY_JMESPATH_ATTRIBUTE", "idempotencyKeyJmespath"
)
logger = Logger()


class InvalidJMESPathException(Exception):
    ...


def calculate_hash(event):
    if idempotency_key_jmespath := event.get(IDEMPOTENCY_JMESPATH_ATTRIBUTE, None):
        idempotency_value = jmespath.search(idempotency_key_jmespath, event)
        if idempotency_value[0] is None:
            logger.error(
                f"JMESPath expression '{IDEMPOTENCY_JMESPATH_ATTRIBUTE}' did not find any matching values",
                extra={
                    "event": event,
                    "idempotency_jmespath": idempotency_key_jmespath,
                },
            )
            raise InvalidJMESPathException(
                f"JMESPath expression '{idempotency_key_jmespath}' did not yield any results"
            )
    else:
        logger.debug(
            f"{IDEMPOTENCY_JMESPATH_ATTRIBUTE} not found in event",
            extra={"event": event, "idempotency_jmespath": idempotency_key_jmespath},
        )
        idempotency_value = event

    idempotency_value = json.dumps(idempotency_value)
    return (
        idempotency_key_jmespath,
        idempotency_value,
        hashlib.sha256(idempotency_value.encode("utf-8")).hexdigest(),
    )


def lambda_handler(event, context):

    idempotency_key_jmespath, idempotency_value, hash = calculate_hash(event)

    logger.info(
        f"Event hashed to {hash}",
        extra={
            "event": event,
            "hash": hash,
            "idempotency_value": idempotency_value,
            "idempotency_jmespath": idempotency_key_jmespath,
        },
    )

    twentyfour_hours_from_now = datetime.now() + timedelta(hours=24)

    return {
        "payload": event,
        "idempotencyConfig": {
            "idempotencyKey": hash,
            "ttl": str(int(twentyfour_hours_from_now.timestamp())),
        },
    }
