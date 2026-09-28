import json
from decimal import Decimal

import pytest

from payments.domain.fraud import Rules
from payments.processor import handler as processor


class FakeS3:
    def __init__(self):
        self.objects = {}

    # Capitalised names because that is how boto3 spells these arguments.
    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = json.loads(Body)


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(processor, "s3", fake)
    return fake


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("DECISIONS_BUCKET", "bucket")
    monkeypatch.setenv("DECISIONS_PREFIX", "decisions")
    monkeypatch.setenv("MAX_AMOUNT", "1000")
    monkeypatch.setenv("BLOCKED_COUNTRIES", "KP")


def message(transaction_id, **overrides):
    body = {
        "transaction_id": transaction_id,
        "customer_id": "cust-1",
        "amount": "100",
        "currency": "EUR",
        "country": "DE",
        "created_at": "2026-09-29T10:00:00+00:00",
    } | overrides
    return {"messageId": f"msg-{transaction_id}", "body": json.dumps(body)}


def test_writes_the_decision_under_the_transaction_id(s3, env):
    processor.handler({"Records": [message("tx-1")]}, None)

    decision = s3.objects[("bucket", "decisions/tx-1.json")]
    assert decision["status"] == "approved"
    assert decision["transaction_id"] == "tx-1"
    assert decision["reason"] == "passed all rules"


def test_a_rejected_transaction_carries_its_reason(s3, env):
    processor.handler({"Records": [message("tx-2", amount="5000")]}, None)

    decision = s3.objects[("bucket", "decisions/tx-2.json")]
    assert decision["status"] == "rejected"
    assert "over limit" in decision["reason"]


def test_a_healthy_batch_reports_no_failures(s3, env):
    result = processor.handler({"Records": [message("tx-1"), message("tx-2")]}, None)

    assert result == {"batchItemFailures": []}
    assert len(s3.objects) == 2


def test_only_the_broken_message_is_reported_back(s3, env):
    poison = {"messageId": "msg-poison", "body": "not json"}

    result = processor.handler({"Records": [message("tx-1"), poison, message("tx-3")]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-poison"}]}
    assert len(s3.objects) == 2, "the healthy neighbours should still have been written"


def test_thresholds_come_from_the_environment(s3, env, monkeypatch):
    monkeypatch.setenv("MAX_AMOUNT", "50")

    processor.handler({"Records": [message("tx-1")]}, None)

    assert s3.objects[("bucket", "decisions/tx-1.json")]["status"] == "rejected"


def test_process_returns_the_key_it_wrote(s3, env):
    key = processor.process(message("tx-9")["body"], Rules(max_amount=Decimal("1000")), "b", "p")

    assert key == "p/tx-9.json"
