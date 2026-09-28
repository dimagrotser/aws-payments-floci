"""What happens to messages the processor cannot make sense of.

Waiting for a redrive is the slowest thing this suite does: the message has to be
received max_receive_count times, and after each failure it waits out the queue's
visibility timeout. So the scenario is set up once, in a module-scoped fixture, and the
tests below read the result of that single run.
"""

import json

import pytest

from tests.integration.conftest import drain, transaction, wait_for

pytestmark = pytest.mark.integration

NOT_JSON = "this is not a transaction"


@pytest.fixture(scope="module")
def redrive(sqs, s3, outputs):
    """Send two poison messages and one healthy one, then wait for the dust to settle."""
    drain(sqs, outputs["queue_url"])
    drain(sqs, outputs["dlq_url"])

    healthy_id = "tx-dlq-neighbour"
    missing_amount = transaction("tx-dlq-no-amount")
    del missing_amount["amount"]

    for body in (NOT_JSON, json.dumps(missing_amount), json.dumps(transaction(healthy_id))):
        sqs.send_message(QueueUrl=outputs["queue_url"], MessageBody=body)

    expected = 2

    def both_arrived():
        attributes = sqs.get_queue_attributes(
            QueueUrl=outputs["dlq_url"], AttributeNames=["ApproximateNumberOfMessages"]
        )["Attributes"]
        return int(attributes["ApproximateNumberOfMessages"]) >= expected

    wait_for(both_arrived, timeout=150, interval=2, description="the redrive to finish")

    yield {
        "dead_letters": drain(sqs, outputs["dlq_url"]),
        "healthy_id": healthy_id,
        "missing_amount_id": missing_amount["transaction_id"],
    }

    drain(sqs, outputs["queue_url"])
    drain(sqs, outputs["dlq_url"])


def test_a_message_that_is_not_json_is_moved_aside(redrive):
    assert NOT_JSON in [m["Body"] for m in redrive["dead_letters"]]


def test_a_transaction_missing_a_field_is_moved_aside(redrive):
    bodies = [m["Body"] for m in redrive["dead_letters"]]

    assert any(redrive["missing_amount_id"] in body for body in bodies)


def test_the_healthy_message_is_not_dragged_down_with_them(redrive, s3, outputs):
    # The event source mapping reports failures per message, so the good one is deleted
    # from the queue while only the poison ones go round again.
    key = f"{outputs['decisions_prefix']}/{redrive['healthy_id']}.json"
    decision = json.loads(s3.get_object(Bucket=outputs["bucket"], Key=key)["Body"].read())

    assert decision["status"] == "approved"


def test_nothing_else_ends_up_in_the_dead_letter_queue(redrive):
    assert len(redrive["dead_letters"]) == 2, "only the two poison messages should be there"
