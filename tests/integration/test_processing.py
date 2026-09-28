from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from payments.db.models import TransactionRecord
from tests.integration.conftest import transaction, wait_for

pytestmark = pytest.mark.integration


def settled(db, transaction_id: str, timeout: float = 45) -> TransactionRecord:
    def fetch():
        db.rollback()
        record = db.scalar(
            select(TransactionRecord).where(TransactionRecord.transaction_id == transaction_id)
        )
        return record if record is not None and record.processed_at is not None else None

    return wait_for(fetch, timeout, description=f"a decision on {transaction_id}")


def test_an_ordinary_transaction_is_approved(
    submit, db, transaction_id, clean_queues, clean_transactions
):
    submit(transaction(transaction_id))

    record = settled(db, transaction_id)

    assert record.status == "approved"
    assert record.decision_reason == "passed all rules"
    assert str(record.amount) == "100.00"
    assert record.customer_id == f"cust-{transaction_id}"


def test_a_large_transaction_is_rejected(
    submit, db, transaction_id, clean_queues, clean_transactions
):
    submit(transaction(transaction_id, amount="50000.00"))

    record = settled(db, transaction_id)

    assert record.status == "rejected"
    assert "over limit" in record.decision_reason


def test_a_blocked_country_is_rejected(
    submit, db, transaction_id, clean_queues, clean_transactions
):
    submit(transaction(transaction_id, country="KP"))

    record = settled(db, transaction_id)

    assert record.status == "rejected"
    assert "country KP is blocked" in record.decision_reason


def test_a_customer_moving_too_fast_is_rejected(
    submit, db, transaction_id, clean_queues, clean_transactions
):
    # The velocity rule is the one that needs the database: it counts what the same
    # customer did inside the window, which only exists once there is somewhere to look.
    now = datetime.now(UTC)
    for minute in range(5):
        db.add(
            TransactionRecord(
                transaction_id=f"{transaction_id}-history-{minute}",
                customer_id="cust-fast",
                amount="10.00",
                currency="EUR",
                country="DE",
                status="approved",
                created_at=now - timedelta(minutes=minute + 1),
            )
        )
    db.commit()

    submit(transaction(transaction_id, customer_id="cust-fast", created_at=now.isoformat()))

    record = settled(db, transaction_id)

    assert record.status == "rejected"
    assert "limit is 5" in record.decision_reason


def test_an_older_burst_does_not_count_against_the_customer(
    submit, db, transaction_id, clean_queues, clean_transactions
):
    now = datetime.now(UTC)
    for minute in range(5):
        db.add(
            TransactionRecord(
                transaction_id=f"{transaction_id}-old-{minute}",
                customer_id="cust-slow",
                amount="10.00",
                currency="EUR",
                country="DE",
                status="approved",
                created_at=now - timedelta(minutes=30 + minute),
            )
        )
    db.commit()

    submit(transaction(transaction_id, customer_id="cust-slow", created_at=now.isoformat()))

    assert settled(db, transaction_id).status == "approved"


def test_the_same_transaction_delivered_twice_leaves_one_row(
    submit, db, transaction_id, clean_queues, clean_transactions
):
    # SQS delivers at least once, so the processor has to be able to see a message twice
    # without producing a second row or a second decision.
    payload = transaction(transaction_id)
    submit(payload)
    settled(db, transaction_id)
    submit(payload)

    def both_handled():
        db.rollback()
        return db.scalar(
            select(TransactionRecord).where(TransactionRecord.transaction_id == transaction_id)
        )

    wait_for(both_handled, 30, description="the duplicate to be processed")
    db.rollback()
    rows = db.scalars(
        select(TransactionRecord).where(TransactionRecord.customer_id == f"cust-{transaction_id}")
    ).all()

    assert len(rows) == 1
    assert rows[0].status == "approved"


def test_the_queue_is_empty_once_the_work_is_done(
    submit, sqs, db, outputs, transaction_id, clean_queues, clean_transactions
):
    submit(transaction(transaction_id))
    settled(db, transaction_id)

    attributes = sqs.get_queue_attributes(
        QueueUrl=outputs["queue_url"],
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]

    assert attributes["ApproximateNumberOfMessages"] == "0"
    assert attributes["ApproximateNumberOfMessagesNotVisible"] == "0"


def test_the_decision_is_written_to_the_log(
    submit, db, logs, outputs, transaction_id, clean_queues, clean_transactions
):
    submit(transaction(transaction_id))
    settled(db, transaction_id)

    def find():
        # Floci matches filterPattern as a plain substring rather than AWS filter syntax.
        events = logs.filter_log_events(
            logGroupName=outputs["processor_log_group"], filterPattern=transaction_id
        )["events"]
        return events or None

    events = wait_for(find, 30, description="a log line mentioning the transaction")
    assert any(transaction_id in event["message"] for event in events)
