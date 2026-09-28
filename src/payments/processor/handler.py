"""SQS consumer: applies the anti-fraud rules and records the decision.

Stage 1 writes decisions to S3 because there is no database yet. Stage 2 moves the
write to RDS and keeps S3 for the daily report.

Failures are reported per message (`ReportBatchItemFailures`) rather than by failing the
whole batch, so one malformed message cannot drag its healthy neighbours to the dead
letter queue with it.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

import boto3

from payments.domain.config import rules_from_env
from payments.domain.fraud import CustomerHistory, evaluate
from payments.domain.transaction import parse_transaction

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Created once per container, reused across warm invocations.
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


def process(body: str, rules, bucket: str, prefix: str) -> str:
    transaction = parse_transaction(body)

    # Nothing to count against yet: the transaction history arrives with the database
    # in stage 2, and CustomerHistory is the seam where it will plug in.
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
