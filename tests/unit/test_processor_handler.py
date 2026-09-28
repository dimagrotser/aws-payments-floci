import json

import pytest

from payments.domain.fraud import CustomerHistory, Decision, Rules, Status
from payments.processor import handler as processor


class FakeSession:
    pass


@pytest.fixture
def recorded(monkeypatch):
    # The database layer is replaced so these tests are about the handler, not about
    # SQL. The repository functions are exercised for real in tests/integration/.
    calls = {"decisions": [], "history": 0}

    class Scope:
        def __enter__(self):
            return FakeSession()

        def __exit__(self, *exception):
            return False

    monkeypatch.setattr(processor, "session_scope", Scope)
    monkeypatch.setattr(processor, "count_recent", lambda session, tx, window: calls["history"])
    monkeypatch.setattr(
        processor,
        "record_decision",
        lambda session, tx, decision: calls["decisions"].append((tx, decision)),
    )
    return calls


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MAX_AMOUNT", "1000")
    monkeypatch.setenv("BLOCKED_COUNTRIES", "KP")
    monkeypatch.setenv("VELOCITY_LIMIT", "5")
    monkeypatch.setenv("VELOCITY_WINDOW_MINUTES", "10")


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


def test_an_ordinary_transaction_is_recorded_as_approved(recorded, env):
    processor.handler({"Records": [message("tx-1")]}, None)

    transaction, decision = recorded["decisions"][0]
    assert transaction.transaction_id == "tx-1"
    assert decision.status is Status.APPROVED


def test_a_rejected_transaction_carries_its_reason(recorded, env):
    processor.handler({"Records": [message("tx-2", amount="5000")]}, None)

    _, decision = recorded["decisions"][0]
    assert decision.status is Status.REJECTED
    assert "over limit" in decision.reason


def test_the_customer_history_reaches_the_rules(recorded, env):
    recorded["history"] = 9

    processor.handler({"Records": [message("tx-3")]}, None)

    _, decision = recorded["decisions"][0]
    assert decision.status is Status.REJECTED
    assert "9 transactions in the last 10 minutes" in decision.reason


def test_a_healthy_batch_reports_no_failures(recorded, env):
    result = processor.handler({"Records": [message("tx-1"), message("tx-2")]}, None)

    assert result == {"batchItemFailures": []}
    assert len(recorded["decisions"]) == 2


def test_only_the_broken_message_is_reported_back(recorded, env):
    poison = {"messageId": "msg-poison", "body": "not json"}

    result = processor.handler({"Records": [message("tx-1"), poison, message("tx-3")]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-poison"}]}
    assert len(recorded["decisions"]) == 2, "the healthy neighbours should still be recorded"


def test_a_message_that_fails_to_record_is_reported_back(recorded, env, monkeypatch):
    def explode(session, transaction, decision):
        raise RuntimeError("the database said no")

    monkeypatch.setattr(processor, "record_decision", explode)

    result = processor.handler({"Records": [message("tx-1")]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-tx-1"}]}


def test_thresholds_come_from_the_environment(recorded, env, monkeypatch):
    monkeypatch.setenv("MAX_AMOUNT", "50")

    processor.handler({"Records": [message("tx-1")]}, None)

    assert recorded["decisions"][0][1].status is Status.REJECTED


def test_process_summarises_what_it_did(recorded, env):
    summary = processor.process(message("tx-9")["body"], Rules(), FakeSession())

    assert summary.startswith("tx-9 approved")


def test_the_history_is_passed_as_a_snapshot(recorded, env, monkeypatch):
    seen = {}

    def spy(transaction, history, rules):
        seen["history"] = history
        return Decision(Status.APPROVED)

    monkeypatch.setattr(processor, "evaluate", spy)
    recorded["history"] = 3

    processor.handler({"Records": [message("tx-1")]}, None)

    assert seen["history"] == CustomerHistory(recent_transactions=3)
