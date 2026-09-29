import csv
import io
from datetime import UTC, datetime, timedelta

import pytest

from payments.db.models import TransactionRecord

pytestmark = pytest.mark.integration


def invoke_reporter(lambda_client, outputs, day: str) -> dict:
    import json

    response = lambda_client.invoke(
        FunctionName=outputs["reporter_function"],
        Payload=json.dumps({"day": day}).encode(),
    )
    assert "FunctionError" not in response, response.get("FunctionError")
    return json.loads(response["Payload"].read())


def read_report(s3, outputs, key: str) -> list[dict]:
    body = s3.get_object(Bucket=outputs["bucket"], Key=key)["Body"].read().decode()
    return list(csv.DictReader(io.StringIO(body)))


def settled(transaction_id: str, created_at: datetime, **overrides) -> TransactionRecord:
    defaults = {
        "transaction_id": transaction_id,
        "customer_id": f"cust-{transaction_id}",
        "amount": "42.00",
        "currency": "EUR",
        "country": "DE",
        "status": "approved",
        "decision_reason": "passed all rules",
        "created_at": created_at,
        "processed_at": created_at + timedelta(seconds=2),
    }
    return TransactionRecord(**(defaults | overrides))


def test_the_report_holds_the_transactions_of_that_day(
    lambda_client, s3, db, outputs, clean_transactions
):
    day = datetime(2026, 3, 14, tzinfo=UTC)
    db.add(settled("tx-report-morning", day.replace(hour=9)))
    db.add(settled("tx-report-evening", day.replace(hour=21), status="rejected"))
    db.commit()

    result = invoke_reporter(lambda_client, outputs, "2026-03-14")

    assert result["transactions"] == 2
    assert result["key"] == f"{outputs['reports_prefix']}/2026-03-14.csv"

    rows = read_report(s3, outputs, result["key"])
    assert [row["transaction_id"] for row in rows] == ["tx-report-morning", "tx-report-evening"]
    assert [row["status"] for row in rows] == ["approved", "rejected"]
    assert rows[0]["amount"] == "42.00"


def test_the_report_ignores_the_days_around_it(lambda_client, s3, db, outputs, clean_transactions):
    day = datetime(2026, 3, 14, tzinfo=UTC)
    db.add(settled("tx-report-yesterday", day - timedelta(minutes=1)))
    db.add(settled("tx-report-today", day.replace(hour=12)))
    db.add(settled("tx-report-tomorrow", day + timedelta(days=1)))
    db.commit()

    result = invoke_reporter(lambda_client, outputs, "2026-03-14")

    rows = read_report(s3, outputs, result["key"])
    assert [row["transaction_id"] for row in rows] == ["tx-report-today"]


def test_a_quiet_day_still_produces_a_report(lambda_client, s3, db, outputs, clean_transactions):
    result = invoke_reporter(lambda_client, outputs, "2026-03-15")

    assert result["transactions"] == 0
    rows = read_report(s3, outputs, result["key"])
    assert rows == []


def test_the_rule_fires_daily_at_the_hour_it_says(events, outputs):
    rule = events.describe_rule(Name="payments-daily-report")

    assert rule["ScheduleExpression"] == outputs["report_schedule"]
    assert rule["State"] == "ENABLED"


def test_the_rule_points_at_the_reporter(events, outputs):
    targets = events.list_targets_by_rule(Rule="payments-daily-report")["Targets"]

    assert len(targets) == 1
    assert targets[0]["Arn"].endswith(f":function:{outputs['reporter_function']}")
