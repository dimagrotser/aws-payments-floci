from __future__ import annotations

import csv
import io
import logging
import os
from datetime import UTC, date, datetime, timedelta
from functools import cache

import boto3

from payments.db.engine import session_scope
from payments.db.repository import transactions_on

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLUMNS = (
    "transaction_id",
    "customer_id",
    "amount",
    "currency",
    "country",
    "status",
    "decision_reason",
    "created_at",
    "processed_at",
)


@cache
def get_s3():
    return boto3.client("s3")


def handler(event, context):
    day = reported_day(event)
    bucket = os.environ["REPORTS_BUCKET"]
    prefix = os.environ.get("REPORTS_PREFIX", "reports")

    with session_scope() as session:
        records = transactions_on(session, day)
        body = render(records)

    key = f"{prefix}/{day.isoformat()}.csv"
    get_s3().put_object(Bucket=bucket, Key=key, Body=body.encode(), ContentType="text/csv")

    logger.info("wrote %s with %d transactions", key, len(records))
    return {"key": key, "day": day.isoformat(), "transactions": len(records)}


def reported_day(event) -> date:
    requested = (event or {}).get("day")
    if requested:
        return date.fromisoformat(requested)
    return (datetime.now(UTC) - timedelta(days=1)).date()


def render(records) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)

    for record in records:
        writer.writerow(
            [
                record.transaction_id,
                record.customer_id,
                f"{record.amount:.2f}",
                record.currency,
                record.country,
                record.status,
                record.decision_reason or "",
                record.created_at.isoformat(),
                record.processed_at.isoformat() if record.processed_at else "",
            ]
        )

    return buffer.getvalue()
