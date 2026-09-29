from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from payments.db.models import TransactionRecord
from payments.reporter.handler import COLUMNS, render, reported_day


def record(**overrides) -> TransactionRecord:
    defaults = {
        "transaction_id": "tx-1",
        "customer_id": "cust-1",
        "amount": Decimal("100.5"),
        "currency": "EUR",
        "country": "DE",
        "status": "approved",
        "decision_reason": "passed all rules",
        "created_at": datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
        "processed_at": datetime(2026, 9, 29, 10, 0, 2, tzinfo=UTC),
    }
    return TransactionRecord(**(defaults | overrides))


def test_an_empty_day_still_produces_a_header():
    report = render([])

    assert report == ",".join(COLUMNS) + "\n"


def test_every_column_is_filled_in():
    lines = render([record()]).splitlines()

    assert lines[1].split(",") == [
        "tx-1",
        "cust-1",
        "100.50",
        "EUR",
        "DE",
        "approved",
        "passed all rules",
        "2026-09-29T10:00:00+00:00",
        "2026-09-29T10:00:02+00:00",
    ]


def test_amounts_keep_two_decimal_places():
    assert ",100.00," in render([record(amount=Decimal("100"))])


def test_a_transaction_nobody_has_settled_yet_leaves_the_last_columns_empty():
    lines = render([record(status="pending", decision_reason=None, processed_at=None)]).splitlines()

    assert lines[1].endswith(",")
    assert lines[1].split(",")[5] == "pending"


def test_a_reason_with_a_comma_is_quoted():
    # The reasons are joined with a semicolon, but a rule could still contain a comma.
    report = render([record(decision_reason="one, two")])

    assert '"one, two"' in report


def test_the_day_can_be_asked_for():
    assert reported_day({"day": "2026-01-31"}) == date(2026, 1, 31)


@pytest.mark.parametrize("event", [None, {}, {"day": None}])
def test_without_a_day_it_reports_on_yesterday(event):
    today = datetime.now(UTC).date()

    assert (today - reported_day(event)).days == 1
