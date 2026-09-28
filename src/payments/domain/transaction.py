"""The transaction as it travels through the system.

A plain dataclass rather than a pydantic model on purpose: this module is imported by
the Lambda handlers, and their zips have to stay free of compiled dependencies.
The API keeps its own pydantic models at the HTTP edge and converts to this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

CURRENCIES = frozenset({"EUR", "USD", "GBP"})


class InvalidTransaction(ValueError):
    """The payload is not a transaction we can act on.

    Raised out of the handler on purpose so the message goes back to the queue and
    eventually to the dead letter queue, instead of being silently dropped.
    """


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: str
    customer_id: str
    amount: Decimal
    currency: str
    country: str
    created_at: datetime


def parse_transaction(body: str) -> Transaction:
    try:
        raw = json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidTransaction(f"body is not JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise InvalidTransaction(f"expected a JSON object, got {type(raw).__name__}")

    missing = sorted(
        {"transaction_id", "customer_id", "amount", "currency", "country", "created_at"}
        - raw.keys()
    )
    if missing:
        raise InvalidTransaction(f"missing fields: {', '.join(missing)}")

    try:
        amount = Decimal(str(raw["amount"]))
    except InvalidOperation as exc:
        raise InvalidTransaction(f"amount is not a number: {raw['amount']!r}") from exc
    if amount <= 0:
        raise InvalidTransaction(f"amount must be positive, got {amount}")

    currency = str(raw["currency"]).upper()
    if currency not in CURRENCIES:
        raise InvalidTransaction(f"unsupported currency: {currency}")

    country = str(raw["country"]).upper()
    if len(country) != 2:
        raise InvalidTransaction(f"country must be an ISO 3166-1 alpha-2 code, got {country!r}")

    try:
        created_at = datetime.fromisoformat(str(raw["created_at"]))
    except ValueError as exc:
        raise InvalidTransaction(f"created_at is not ISO 8601: {raw['created_at']!r}") from exc

    return Transaction(
        transaction_id=str(raw["transaction_id"]),
        customer_id=str(raw["customer_id"]),
        amount=amount,
        currency=currency,
        country=country,
        created_at=created_at,
    )
