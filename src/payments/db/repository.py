from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from payments.db.models import TransactionRecord
from payments.domain.fraud import Decision, Status
from payments.domain.transaction import Transaction


def count_recent(session: Session, transaction: Transaction, window: timedelta) -> int:
    statement = (
        select(func.count())
        .select_from(TransactionRecord)
        .where(
            TransactionRecord.customer_id == transaction.customer_id,
            TransactionRecord.transaction_id != transaction.transaction_id,
            TransactionRecord.created_at > transaction.created_at - window,
            TransactionRecord.created_at <= transaction.created_at,
        )
    )
    return session.scalar(statement) or 0


def record_decision(session: Session, transaction: Transaction, decision: Decision) -> None:
    decided_at = datetime.now(UTC)
    statement = insert(TransactionRecord).values(
        transaction_id=transaction.transaction_id,
        customer_id=transaction.customer_id,
        amount=transaction.amount,
        currency=transaction.currency,
        country=transaction.country,
        status=decision.status.value,
        decision_reason=decision.reason,
        created_at=transaction.created_at,
        processed_at=decided_at,
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[TransactionRecord.transaction_id],
            set_={
                "status": decision.status.value,
                "decision_reason": decision.reason,
                "processed_at": decided_at,
            },
        )
    )


def insert_pending(
    session: Session,
    *,
    transaction_id: str,
    customer_id: str,
    amount: Decimal,
    currency: str,
    country: str,
    created_at: datetime,
) -> None:
    session.add(
        TransactionRecord(
            transaction_id=transaction_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            country=country,
            status=Status.PENDING.value,
            created_at=created_at,
        )
    )


def fetch(session: Session, transaction_id: str) -> TransactionRecord | None:
    return session.get(TransactionRecord, transaction_id)


def transactions_on(session: Session, day: date) -> list[TransactionRecord]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    statement = (
        select(TransactionRecord)
        .where(
            TransactionRecord.created_at >= start,
            TransactionRecord.created_at < start + timedelta(days=1),
        )
        .order_by(TransactionRecord.created_at, TransactionRecord.transaction_id)
    )
    return list(session.scalars(statement))
