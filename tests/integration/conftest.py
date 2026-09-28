from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import boto3
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

OUTPUTS = Path(__file__).resolve().parents[2] / "build" / "outputs.json"
ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
os.environ.setdefault("AWS_ENDPOINT_URL", ENDPOINT)

from payments.db.engine import database_url, load_credentials  # noqa: E402

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
def db_engine(outputs):
    # Floci advertises the database under a name only containers resolve, but the port
    # it gives out is published, so the host connects to the same port on localhost.
    credentials = load_credentials(outputs["db_secret_arn"])
    return create_engine(database_url(credentials, host="localhost"))


@pytest.fixture
def db(db_engine) -> Iterator[Session]:
    # No explicit transaction: the tests poll for rows another process writes, and
    # db.rollback() is how they drop a stale snapshot and look again.
    with Session(db_engine) as session:
        yield session
        session.rollback()


def clear_transactions(engine) -> None:
    # DELETE rather than TRUNCATE: TRUNCATE wants an exclusive lock on the table, and a
    # test's own session is often still holding a read transaction when this runs.
    with Session(engine) as session, session.begin():
        session.execute(text("delete from transactions"))


@pytest.fixture(scope="session", autouse=True)
def start_from_a_known_state(db_engine, sqs, outputs):
    # Whatever an interrupted run left behind is not this run's business.
    clear_transactions(db_engine)
    drain(sqs, outputs["queue_url"])
    drain(sqs, outputs["dlq_url"])


@pytest.fixture
def clean_transactions(db_engine):
    clear_transactions(db_engine)
    yield
    clear_transactions(db_engine)


@pytest.fixture(scope="session")
def queue_arn(outputs) -> str:
    # Floci hands out queue URLs, and IAM talks in ARNs.
    name = outputs["queue_url"].rsplit("/", 1)[-1]
    return f"arn:aws:sqs:{os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')}:000000000000:{name}"


def drain(sqs, queue_url: str) -> list[dict]:
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
    # A customer of its own by default. The velocity rule counts what the same customer
    # did recently, so sharing one across tests would let them reject each other.
    return {
        "transaction_id": transaction_id,
        "customer_id": f"cust-{transaction_id}",
        "amount": "100.00",
        "currency": "EUR",
        "country": "DE",
        "created_at": "2026-09-29T10:00:00+00:00",
    } | overrides


def wait_for(probe, timeout: float, interval: float = 1.0, description: str = "condition"):
    # Every effect here is asynchronous, so assertions need a deadline, not a sleep.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = probe()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError(f"timed out after {timeout:.0f}s waiting for {description}")
