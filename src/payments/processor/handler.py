from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

import boto3

from payments.domain.config import rules_from_env
from payments.domain.fraud import CustomerHistory, Rules, evaluate
from payments.domain.transaction import parse_transaction

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def handler(event, context):
    rules = rules_from_env()
    bucket = os.environ["DECISIONS_BUCKET"]
    prefix = os.environ.get("DECISIONS_PREFIX", "decisions")

    failures = []
    for record in event.get("Records", []):
        try:
            key = process(record["body"], rules, bucket, prefix)
            logger.info("decided %s", key)
        except Exception:
            logger.exception("message %s failed", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def process(body: str, rules: Rules, bucket: str, prefix: str) -> str:
    transaction = parse_transaction(body)
    decision = evaluate(transaction, CustomerHistory(), rules)

    key = f"{prefix}/{transaction.transaction_id}.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(
            {
                "transaction_id": transaction.transaction_id,
                "customer_id": transaction.customer_id,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "country": transaction.country,
                "status": decision.status.value,
                "reason": decision.reason,
                "decided_at": datetime.now(UTC).isoformat(),
            }
        ).encode(),
        ContentType="application/json",
    )
    return key
