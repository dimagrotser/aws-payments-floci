from datetime import UTC, datetime
from decimal import Decimal

import pytest

from payments.domain.fraud import CustomerHistory, Rules, Status, evaluate
from payments.domain.transaction import Transaction


def transaction(**overrides) -> Transaction:
    defaults = {
        "transaction_id": "tx-1",
        "customer_id": "cust-1",
        "amount": Decimal("100"),
        "currency": "EUR",
        "country": "DE",
        "created_at": datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
    }
    return Transaction(**(defaults | overrides))


RULES = Rules(
    max_amount=Decimal("10000"),
    blocked_countries=frozenset({"KP", "IR"}),
    velocity_limit=5,
)


def test_an_ordinary_transaction_is_approved():
    decision = evaluate(transaction(), CustomerHistory(), RULES)

    assert decision.status is Status.APPROVED
    assert decision.reason == "passed all rules"


@pytest.mark.parametrize("amount", [Decimal("10000.01"), Decimal("999999")])
def test_amounts_over_the_limit_are_rejected(amount):
    decision = evaluate(transaction(amount=amount), CustomerHistory(), RULES)

    assert decision.status is Status.REJECTED
    assert "over limit" in decision.reason


def test_the_limit_itself_is_still_allowed():
    decision = evaluate(transaction(amount=Decimal("10000")), CustomerHistory(), RULES)

    assert decision.status is Status.APPROVED


def test_blocked_countries_are_rejected():
    decision = evaluate(transaction(country="KP"), CustomerHistory(), RULES)

    assert decision.status is Status.REJECTED
    assert "country KP is blocked" in decision.reason


def test_too_many_recent_transactions_are_rejected():
    decision = evaluate(transaction(), CustomerHistory(recent_transactions=5), RULES)

    assert decision.status is Status.REJECTED
    assert "limit is 5" in decision.reason


def test_one_below_the_velocity_limit_still_passes():
    decision = evaluate(transaction(), CustomerHistory(recent_transactions=4), RULES)

    assert decision.status is Status.APPROVED


def test_every_broken_rule_ends_up_in_the_reason():
    decision = evaluate(
        transaction(amount=Decimal("50000"), country="IR"),
        CustomerHistory(recent_transactions=9),
        RULES,
    )

    assert decision.status is Status.REJECTED
    assert len(decision.reasons) == 3
    assert "over limit" in decision.reason
    assert "country IR is blocked" in decision.reason
    assert "limit is 5" in decision.reason
