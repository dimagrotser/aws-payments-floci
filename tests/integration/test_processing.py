"""The happy path, end to end through the real emulator: SQS to Lambda to S3."""

import json

import pytest

from tests.integration.conftest import transaction, wait_for

pytestmark = pytest.mark.integration


def decision_for(s3, outputs, transaction_id: str, timeout: float = 45):
    key = f"{outputs['decisions_prefix']}/{transaction_id}.json"

    def fetch():
        try:
            return s3.get_object(Bucket=outputs["bucket"], Key=key)["Body"].read()
        except s3.exceptions.NoSuchKey:
            return None

    return json.loads(wait_for(fetch, timeout, description=f"decision for {transaction_id}"))


def test_an_ordinary_transaction_is_approved(submit, s3, outputs, transaction_id, clean_queues):
    submit(transaction(transaction_id))

    decision = decision_for(s3, outputs, transaction_id)

    assert decision["status"] == "approved"
    assert decision["reason"] == "passed all rules"
    assert decision["amount"] == "100.00"


def test_a_large_transaction_is_rejected(submit, s3, outputs, transaction_id, clean_queues):
    submit(transaction(transaction_id, amount="50000.00"))

    decision = decision_for(s3, outputs, transaction_id)

    assert decision["status"] == "rejected"
    assert "over limit" in decision["reason"]


def test_a_blocked_country_is_rejected(submit, s3, outputs, transaction_id, clean_queues):
    submit(transaction(transaction_id, country="KP"))

    decision = decision_for(s3, outputs, transaction_id)

    assert decision["status"] == "rejected"
    assert "country KP is blocked" in decision["reason"]


def test_the_queue_is_empty_once_the_work_is_done(
    submit, sqs, s3, outputs, transaction_id, clean_queues
):
    submit(transaction(transaction_id))
    decision_for(s3, outputs, transaction_id)

    attributes = sqs.get_queue_attributes(
        QueueUrl=outputs["queue_url"],
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]

    assert attributes["ApproximateNumberOfMessages"] == "0"
    assert attributes["ApproximateNumberOfMessagesNotVisible"] == "0"


def test_the_decision_is_written_to_the_log(
    submit, s3, logs, outputs, transaction_id, clean_queues
):
    submit(transaction(transaction_id))
    decision_for(s3, outputs, transaction_id)

    def find():
        # Floci matches filterPattern as a plain substring rather than AWS filter syntax,
        # so this stays a simple search for the key the handler logged.
        events = logs.filter_log_events(
            logGroupName=outputs["processor_log_group"], filterPattern=transaction_id
        )["events"]
        return events or None

    events = wait_for(find, 30, description="a log line mentioning the transaction")
    assert any(transaction_id in event["message"] for event in events)
