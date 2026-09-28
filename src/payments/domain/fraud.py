"""Anti-fraud rules.

Three rules, deliberately boring, because the interesting part of this project is the
plumbing around them. They are pure functions over a transaction plus a snapshot of what
we know about the customer, so the same code runs in a unit test and in Lambda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from payments.domain.transaction import Transaction


class Status(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class Rules:
    max_amount: Decimal = Decimal("10000")
    blocked_countries: frozenset[str] = frozenset({"KP", "IR", "SY"})
    velocity_limit: int = 5
    velocity_window_minutes: int = 10


@dataclass(frozen=True, slots=True)
class CustomerHistory:
    """What the caller managed to find out about this customer.

    `recent_transactions` counts transactions inside the velocity window. Stage 1 has
    nowhere to count them yet and passes 0; stage 2 fills it in from the database.
    """

    recent_transactions: int = 0


@dataclass(frozen=True, slots=True)
class Decision:
    status: Status
    reasons: tuple[str, ...] = field(default=())

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "passed all rules"


def evaluate(transaction: Transaction, history: CustomerHistory, rules: Rules) -> Decision:
    reasons = []

    if transaction.amount > rules.max_amount:
        reasons.append(f"amount {transaction.amount} over limit {rules.max_amount}")

    if transaction.country in rules.blocked_countries:
        reasons.append(f"country {transaction.country} is blocked")

    if history.recent_transactions >= rules.velocity_limit:
        reasons.append(
            f"{history.recent_transactions} transactions in the last "
            f"{rules.velocity_window_minutes} minutes, limit is {rules.velocity_limit}"
        )

    if reasons:
        return Decision(Status.REJECTED, tuple(reasons))
    return Decision(Status.APPROVED)
