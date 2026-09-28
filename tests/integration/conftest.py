"""Fixtures for the tests that talk to a running Floci.

One shared emulator rather than one per test, see DECISIONS.md. Isolation comes from the
cleanup fixtures below plus a unique transaction id per test.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import boto3
import pytest

OUTPUTS = Path(__file__).resolve().parents[2] / "build" / "outputs.json"
ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def outputs() -> dict:
    if not OUTPUTS.exists():
        pytest.fail(f"{OUTPUTS} is missing; run `make up && make deploy` first")
    raw = json.loads(OUTPUTS.read_text())
    return {key: value["value"] for key, value in raw.items()}


def _client(service):
    return boto3.client(service, endpoint_url=ENDPOINT)


@pytest.fixture(scope="session")
def sqs():
    return _client("sqs")


@pytest.fixture(scope="session")
def s3():
    return _client("s3")


@pytest.fixture(scope="session")
def logs():
    return _client("logs")


@pytest.fixture(scope="session")
def iam():
    return _client("iam")


@pytest.fixture(scope="session")
def queue_arn(outputs) -> str:
    """Floci hands out queue URLs, and IAM talks in ARNs."""
    name = outputs["queue_url"].rsplit("/", 1)[-1]
    return f"arn:aws:sqs:{os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')}:000000000000:{name}"


def drain(sqs, queue_url: str) -> list[dict]:
    """Take everything off a queue and return it. Used both to clean up and to assert."""
    drained = []
    while True:
        batch = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=0
        ).get("Messages", [])
        if not batch:
            return drained
        drained.extend(batch)
        sqs.delete_message_batch(
            QueueUrl=queue_url,
            Entries=[{"Id": m["MessageId"], "ReceiptHandle": m["ReceiptHandle"]} for m in batch],
        )


@pytest.fixture
def clean_queues(sqs, outputs):
    """Both queues start and end empty, so one test cannot see another's leftovers."""
    drain(sqs, outputs["queue_url"])
    drain(sqs, outputs["dlq_url"])
    yield
    drain(sqs, outputs["queue_url"])
    drain(sqs, outputs["dlq_url"])


@pytest.fixture
def transaction_id() -> str:
    return f"tx-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def submit(sqs, outputs):
    def _submit(body) -> str:
        payload = body if isinstance(body, str) else json.dumps(body)
        return sqs.send_message(QueueUrl=outputs["queue_url"], MessageBody=payload)["MessageId"]

    return _submit


def transaction(transaction_id: str, **overrides) -> dict:
    return {
        "transaction_id": transaction_id,
        "customer_id": "cust-integration",
        "amount": "100.00",
        "currency": "EUR",
        "country": "DE",
        "created_at": "2026-09-29T10:00:00+00:00",
    } | overrides


def wait_for(probe, timeout: float, interval: float = 1.0, description: str = "condition"):
    """Poll until probe returns something truthy. Every effect here is asynchronous, so
    assertions need a deadline rather than a sleep."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = probe()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError(f"timed out after {timeout:.0f}s waiting for {description}")
