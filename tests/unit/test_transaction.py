from datetime import datetime
from decimal import Decimal

import pytest

from payments.domain.transaction import InvalidTransaction, parse_transaction

VALID = (
    '{"transaction_id": "tx-1", "customer_id": "cust-1", "amount": "125.50",'
    ' "currency": "eur", "country": "de", "created_at": "2026-09-29T10:00:00+00:00"}'
)


def test_parses_a_well_formed_transaction():
    tx = parse_transaction(VALID)

    assert tx.transaction_id == "tx-1"
    assert tx.amount == Decimal("125.50")
    assert tx.currency == "EUR", "currency should be normalised to upper case"
    assert tx.country == "DE"
    assert tx.created_at == datetime.fromisoformat("2026-09-29T10:00:00+00:00")


def test_amount_keeps_its_precision():
    tx = parse_transaction(VALID)

    assert tx.amount == Decimal("125.50")
    assert tx.amount != 125.5000001, "a float would have swallowed the difference"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("this is not json", "not JSON"),
        ("[1, 2, 3]", "expected a JSON object"),
        ('{"transaction_id": "tx-1"}', "missing fields"),
        (VALID.replace('"125.50"', '"abc"'), "not a number"),
        (VALID.replace('"125.50"', '"-1"'), "must be positive"),
        (VALID.replace('"eur"', '"XXX"'), "unsupported currency"),
        (VALID.replace('"de"', '"Germany"'), "alpha-2"),
        (VALID.replace('"2026-09-29T10:00:00+00:00"', '"yesterday"'), "ISO 8601"),
    ],
)
def test_rejects_malformed_payloads(body, expected):
    with pytest.raises(InvalidTransaction, match=expected):
        parse_transaction(body)


def test_missing_fields_are_all_reported_at_once():
    with pytest.raises(InvalidTransaction) as exc:
        parse_transaction('{"transaction_id": "tx-1", "customer_id": "cust-1"}')

    assert "amount, country, created_at, currency" in str(exc.value)
